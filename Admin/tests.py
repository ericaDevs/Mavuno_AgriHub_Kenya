from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from Orders.models import Order
from Payments.models import MpesaPayment
from Products.models import Product

from .models import Admins


class AdminLoginTests(TestCase):
    def setUp(self):
        self.admin = Admins.objects.create(
            username="storeadmin",
            email="admin@example.com",
            password=make_password("CorrectHorseBatteryStaple"),
        )
        self.login_url = reverse("admin:login")

    def test_admin_login_form_posts_to_admin_login(self):
        response = self.client.get(self.login_url)

        self.assertContains(response, f'action="{self.login_url}"')

    def test_admin_can_log_in_with_admin_account(self):
        response = self.client.post(
            self.login_url,
            {
                "username": "storeadmin",
                "email": "admin@example.com",
                "password": "CorrectHorseBatteryStaple",
            },
        )

        self.assertRedirects(response, reverse("admin:overview"))
        self.assertEqual(self.client.session["admin_id"], self.admin.pk)

    def test_invalid_admin_credentials_render_admin_login_form(self):
        response = self.client.post(
            self.login_url,
            {
                "username": "storeadmin",
                "email": "admin@example.com",
                "password": "wrong-password",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Auth_d/login.html")
        self.assertNotIn("admin_id", self.client.session)

    def test_admin_dashboard_requires_admin_login(self):
        response = self.client.get(reverse("admin:overview"))

        self.assertRedirects(response, self.login_url)

    def test_admin_overview_shows_live_metrics_and_recent_orders(self):
        user = get_user_model().objects.create_user(
            username="farmcustomer",
            email="farm@example.com",
            password="StrongPass!123",
        )
        Product.objects.create(
            name="Maize seed",
            description="Seed",
            product_category=Product.Category.SEEDS,
            price_per_unit=Decimal("250.00"),
            stock_quantity=3,
            is_active=True,
        )
        Order.objects.create(
            customer=user,
            status=Order.Status.PAID,
            item_subtotal=Decimal("500.00"),
            delivery_fee=Decimal("0.00"),
            total_amount=Decimal("500.00"),
        )
        MpesaPayment.objects.create(
            customer=user,
            phone="254712345678",
            amount=500,
            checkout_request_id="pending-checkout",
            status=MpesaPayment.Status.PENDING,
        )
        self.client.post(
            self.login_url,
            {
                "username": self.admin.username,
                "email": self.admin.email,
                "password": "CorrectHorseBatteryStaple",
            },
        )

        response = self.client.get(reverse("admin:overview"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_revenue"], Decimal("500.00"))
        self.assertEqual(response.context["total_orders"], 1)
        self.assertEqual(response.context["total_customers"], 1)
        self.assertEqual(response.context["active_products"], 1)
        self.assertEqual(response.context["low_stock_products"], 1)
        self.assertEqual(response.context["pending_payments"], 1)
        self.assertContains(response, "farmcustomer")

    def test_customer_management_is_admin_only_and_shows_customer_activity(self):
        user = get_user_model().objects.create_user(
            username="farmcustomer",
            email="farm@example.com",
            password="StrongPass!123",
        )
        Order.objects.create(
            customer=user,
            status=Order.Status.PAID,
            item_subtotal=Decimal("500.00"),
            delivery_fee=Decimal("0.00"),
            total_amount=Decimal("500.00"),
        )
        response = self.client.get(reverse("admin:customers"))
        self.assertRedirects(response, self.login_url)

        self.client.post(
            self.login_url,
            {
                "username": self.admin.username,
                "email": self.admin.email,
                "password": "CorrectHorseBatteryStaple",
            },
        )
        response = self.client.get(reverse("admin:customers"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_customers"], 1)
        self.assertEqual(response.context["customers_with_orders"], 1)
        customer = response.context["customers"][0]
        self.assertEqual(customer.order_count, 1)
        self.assertContains(response, "farmcustomer")
        self.assertContains(response, "Customer activity")

    def test_customer_management_search_filters_results(self):
        User = get_user_model()
        User.objects.create_user(
            username="farmcustomer",
            email="farm@example.com",
            password="StrongPass!123",
        )
        User.objects.create_user(
            username="othercustomer",
            email="other@example.com",
            password="StrongPass!123",
        )
        self.client.post(
            self.login_url,
            {
                "username": self.admin.username,
                "email": self.admin.email,
                "password": "CorrectHorseBatteryStaple",
            },
        )

        response = self.client.get(reverse("admin:customers"), {"q": "farm"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertContains(response, "farmcustomer")
        self.assertNotContains(response, "othercustomer")
