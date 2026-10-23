from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class CustomerAuthenticationTests(TestCase):
    def test_registration_creates_an_authenticatable_customer(self):
        response = self.client.post(
            reverse("authentication:register"),
            {
                "username": "newcustomer",
                "email": "newcustomer@example.com",
                "password": "StrongPass!123",
                "password_2": "StrongPass!123",
            },
        )

        self.assertRedirects(
            response,
            reverse("authentication:login"),
            fetch_redirect_response=False,
        )
        user = get_user_model().objects.get(username="newcustomer")
        self.assertEqual(user.email, "newcustomer@example.com")
        self.assertTrue(user.check_password("StrongPass!123"))

    def test_registration_rejects_duplicate_email(self):
        get_user_model().objects.create_user(
            username="existing",
            email="existing@example.com",
            password="StrongPass!123",
        )

        response = self.client.post(
            reverse("authentication:register"),
            {
                "username": "another",
                "email": "EXISTING@example.com",
                "password": "StrongPass!123",
                "password_2": "StrongPass!123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertContains(response, "An account with this email already exists.")

    def test_login_honors_safe_next_path(self):
        user = get_user_model().objects.create_user(
            username="customer",
            email="customer@example.com",
            password="StrongPass!123",
        )

        response = self.client.post(
            reverse("authentication:login"),
            {
                "username": user.username,
                "email": user.email,
                "password": "StrongPass!123",
                "next": reverse("payments:checkout"),
            },
        )

        self.assertRedirects(
            response,
            reverse("payments:checkout"),
            fetch_redirect_response=False,
        )
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_rejects_external_next_path(self):
        user = get_user_model().objects.create_user(
            username="customer",
            email="customer@example.com",
            password="StrongPass!123",
        )

        response = self.client.post(
            reverse("authentication:login"),
            {
                "username": user.username,
                "email": user.email,
                "password": "StrongPass!123",
                "next": "https://attacker.example/",
            },
        )

        self.assertRedirects(
            response,
            reverse("home"),
            fetch_redirect_response=False,
        )
