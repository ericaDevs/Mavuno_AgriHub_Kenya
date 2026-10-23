from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from Orders.models import Order, OrderItem
from Products.models import Product
from .models import Delivery_infor


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

    def test_valid_delivery_data_is_staged_until_customer_confirms_order(self):
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
        self.assertContains(review_response, "Confirm order (payment not requested)")
        self.assertEqual(review_response.context["delivery_data"]["phone"], "+254712345678")

    def test_confirm_order_creates_order_items_and_delivery_atomically(self):
        self.save_delivery_details()

        response = self.client.post(reverse("payments:confirm_order"))

        order = Order.objects.get()
        self.assertRedirects(
            response,
            reverse(
                "payments:order_confirmation",
                kwargs={"order_reference": order.order_reff},
            ),
            fetch_redirect_response=False,
        )
        self.assertEqual(order.customer, self.user)
        self.assertEqual(order.status, Order.Status.AWAITING_PAYMENT)
        self.assertEqual(order.item_subtotal, Decimal("25.00"))
        self.assertEqual(order.delivery_fee, Decimal("0.00"))
        self.assertEqual(order.total_amount, Decimal("25.00"))
        self.assertEqual(order.items.count(), 1)
        item = order.items.get()
        self.assertEqual(item.product, self.product)
        self.assertEqual(item.product_name, self.product.name)
        self.assertEqual(item.unit_price, Decimal("12.50"))
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.total_price, Decimal("25.00"))
        self.assertEqual(order.delivery.full_name, "Jane Customer")
        self.assertEqual(order.delivery.phone_number, "+254712345678")
        self.assertEqual(self.client.session.get("cart"), None)
        self.assertEqual(self.client.session.get("checkout_delivery"), None)

        confirmation = self.client.get(
            reverse(
                "payments:order_confirmation",
                kwargs={"order_reference": order.order_reff},
            )
        )
        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, order.order_reff)
        self.assertContains(confirmation, "Awaiting payment")
        self.assertContains(confirmation, "Payment has not been requested or processed.")

    def test_confirmation_requires_delivery_data_and_post(self):
        response = self.client.post(reverse("payments:confirm_order"))

        self.assertRedirects(
            response,
            reverse("payments:checkout"),
            fetch_redirect_response=False,
        )
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(
            self.client.get(reverse("payments:confirm_order")).status_code,
            405,
        )

    def test_order_confirmation_is_only_visible_to_its_customer(self):
        self.save_delivery_details()
        self.client.post(reverse("payments:confirm_order"))
        order = Order.objects.get()
        other_user = get_user_model().objects.create_user(
            username="other",
            password="StrongPass!123",
        )
        self.client.force_login(other_user)

        response = self.client.get(
            reverse(
                "payments:order_confirmation",
                kwargs={"order_reference": order.order_reff},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_confirmation_rechecks_stock_before_creating_any_records(self):
        self.save_delivery_details()
        self.product.stock_quantity = 1
        self.product.save(update_fields=["stock_quantity"])

        response = self.client.post(reverse("payments:confirm_order"))

        self.assertRedirects(
            response,
            reverse("payments:checkout"),
            fetch_redirect_response=False,
        )
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)
        self.assertEqual(Delivery_infor.objects.count(), 0)
