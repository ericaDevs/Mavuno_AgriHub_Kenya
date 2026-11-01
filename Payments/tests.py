import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from Orders.models import Order, OrderItem
from Products.models import Product
from .models import Delivery_infor, MpesaPayment
from .views import _apply_result


class CheckoutTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="customer",
            email="customer@example.com",
            password="StrongPass!123",
        )
        self.client.force_login(self.user)
        self.product = Product.objects.create(
            name="Hybrid maize seed",
            description="High-yield seed.",
            product_category=Product.Category.SEEDS,
            price_per_unit=Decimal("12.50"),
            stock_quantity=4,
        )
        self.client.post(
            reverse("products:cart_add", args=[self.product.pk]),
            {"quantity": 2},
        )

    def delivery_data(self, **overrides):
        data = {
            "full_name": "Jane Customer",
            "phone": "+254712345678",
            "email": "jane@example.com",
            "delivery_address": "Nairobi, Kenya",
            "delivery_notes": "Call on arrival",
        }
        data.update(overrides)
        return data

    def save_delivery_details(self):
        return self.client.post(
            reverse("payments:checkout"),
            self.delivery_data(),
        )

    def test_checkout_requires_authentication_and_preserves_return_url(self):
        self.client.logout()

        response = self.client.get(reverse("payments:checkout"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            f"{reverse('authentication:login')}?next=",
            response["Location"],
        )
        self.assertIn(reverse("payments:checkout"), response["Location"])

    def test_checkout_shows_cart_and_total_for_authenticated_customer(self):
        response = self.client.get(reverse("payments:checkout"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["subtotal"], Decimal("25.00"))
        self.assertEqual(response.context["total"], Decimal("25.00"))
        self.assertContains(response, "Hybrid maize seed")

    def test_delivery_form_validation_shows_errors_without_saving_order(self):
        response = self.client.post(
            reverse("payments:checkout"),
            self.delivery_data(phone=""),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(Delivery_infor.objects.count(), 0)

    def test_valid_delivery_data_is_staged_and_payment_section_is_rendered(self):
        response = self.save_delivery_details()

        self.assertRedirects(
            response,
            f"{reverse('payments:checkout')}#order-review",
            fetch_redirect_response=False,
        )
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(Delivery_infor.objects.count(), 0)

        review_response = self.client.get(reverse("payments:checkout"))

        self.assertContains(review_response, "Jane Customer")
        self.assertContains(review_response, "Proceed to Payment")
        self.assertContains(review_response, "Payment with M-Pesa")
        self.assertEqual(review_response.context["delivery_data"]["phone"], "+254712345678")

    @patch("Payments.views.stk_push")
    def test_mpesa_initiation_does_not_save_order(self, stk_push):
        self.save_delivery_details()
        stk_push.return_value = {
            "ResponseCode": "0",
            "MerchantRequestID": "merchant-1",
            "CheckoutRequestID": "checkout-1",
            "CustomerMessage": "Prompt sent",
        }

        response = self.client.post(
            reverse("payments:mpesa"),
            data=json.dumps({"phone": "0712345678"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

        # Crucial requirement: Order is NOT saved before payment is done!
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)
        self.assertEqual(Delivery_infor.objects.count(), 0)

        # Mpesa payment is staged in PENDING status
        payment = MpesaPayment.objects.get()
        self.assertEqual(payment.status, MpesaPayment.Status.PENDING)
        self.assertIsNone(payment.order)
        self.assertEqual(payment.amount, 25)

    @patch("Payments.views.stk_query")
    @patch("Payments.views.stk_push")
    def test_successful_payment_saves_order_and_renders_confirmation(self, stk_push, stk_query):
        self.save_delivery_details()
        stk_push.return_value = {
            "ResponseCode": "0",
            "MerchantRequestID": "merchant-1",
            "CheckoutRequestID": "checkout-1",
            "CustomerMessage": "Prompt sent",
        }

        init_resp = self.client.post(
            reverse("payments:mpesa"),
            data=json.dumps({"phone": "0712345678"}),
            content_type="application/json",
        )
        payment_id = init_resp.json()["payment_id"]

        # Mock Daraja query returning SUCCESS
        stk_query.return_value = {
            "ResponseCode": "0",
            "ResultCode": "0",
            "ResultDesc": "The service request is processed successfully.",
        }

        # Poll status
        status_resp = self.client.get(reverse("payments:payment_status", args=[payment_id]))
        self.assertEqual(status_resp.status_code, 200)
        status_data = status_resp.json()
        self.assertEqual(status_data["status"], "SUCCESS")

        # Now Order, OrderItems, Delivery_infor MUST be saved!
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get()
        self.assertEqual(order.customer, self.user)
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.total_amount, Decimal("25.00"))
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.delivery.full_name, "Jane Customer")

        # Session cart and delivery must be cleared
        self.assertEqual(self.client.session.get("cart"), None)
        self.assertEqual(self.client.session.get("checkout_delivery"), None)

        # Order confirmation page renders after payment is done
        confirmation_url = status_data["success_url"]
        confirmation_resp = self.client.get(confirmation_url)
        self.assertEqual(confirmation_resp.status_code, 200)
        self.assertContains(confirmation_resp, order.order_reff)
        self.assertContains(confirmation_resp, "Payment Confirmed")
        self.assertContains(confirmation_resp, "Thank you for your order!")

    @patch("Payments.views.stk_query")
    @patch("Payments.views.stk_push")
    def test_cancelled_payment_does_not_save_order(self, stk_push, stk_query):
        self.save_delivery_details()
        stk_push.return_value = {
            "ResponseCode": "0",
            "MerchantRequestID": "merchant-2",
            "CheckoutRequestID": "checkout-2",
            "CustomerMessage": "Prompt sent",
        }

        init_resp = self.client.post(
            reverse("payments:mpesa"),
            data=json.dumps({"phone": "0712345678"}),
            content_type="application/json",
        )
        payment_id = init_resp.json()["payment_id"]

        # Mock Daraja query returning CANCELLED (1032)
        stk_query.return_value = {
            "ResponseCode": "0",
            "ResultCode": "1032",
            "ResultDesc": "Request cancelled by user",
        }

        status_resp = self.client.get(reverse("payments:payment_status", args=[payment_id]))
        self.assertEqual(status_resp.status_code, 200)
        status_data = status_resp.json()
        self.assertEqual(status_data["status"], "CANCELLED")
        self.assertIn("cancelled", status_data["message"].lower())

        # No order should have been saved
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)
        self.assertEqual(Delivery_infor.objects.count(), 0)

    def test_mpesa_initiation_rejects_get_requests(self):
        response = self.client.get(reverse("payments:mpesa"))
        self.assertEqual(response.status_code, 405)
