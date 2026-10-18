from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse

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
