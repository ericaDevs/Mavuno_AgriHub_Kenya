from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password

from .models import Users

class RegistrationViewTests(TestCase):
    def test_success_message_is_shown_on_login_page(self):
        response = self.client.post(
            reverse('authentication:register'),
            {
                'username': 'newuser',
                'email': 'newuser@example.com',
                'password': 'ExamplePassword123!',
                'password_2': 'ExamplePassword123!',
            },
            follow=True,
        )

        self.assertEqual(response.redirect_chain, [(reverse('authentication:login'), 302)])
        self.assertContains(response, 'Account created successfully!')
        user = Users.objects.get(email='newuser@example.com')
        self.assertTrue(check_password('ExamplePassword123!', user.password))
        self.assertNotIn('password_2', {field.name for field in Users._meta.fields})

    def test_invalid_email_error_is_shown_on_registration_form(self):
        response = self.client.post(
            reverse('authentication:register'),
            {
                'username': 'newuser',
                'email': 'not-an-email',
                'password': 'ExamplePassword123!',
                'password_2': 'ExamplePassword123!',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'email', 'Enter a valid email address.')
        self.assertContains(response, 'Enter a valid email address.')

    def test_mismatched_passwords_are_rejected(self):
        response = self.client.post(
            reverse('authentication:register'),
            {
                'username': 'newuser',
                'email': 'newuser@example.com',
                'password': 'ExamplePassword123!',
                'password_2': 'DifferentPassword123!',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'],
            'password_2',
            "The two password fields didn't match.",
        )
        self.assertFalse(Users.objects.filter(email='newuser@example.com').exists())


class LoginViewTests(TestCase):
    def test_login_form_fields_are_rendered(self):
        response = self.client.get(reverse('authentication:login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="password"')

    def test_invalid_credentials_show_error_and_keep_form_visible(self):
        response = self.client.post(
            reverse('authentication:login'),
            {
                'username': 'wronguser',
                'email': 'wrong@example.com',
                'password': 'WrongPassword123!',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid credentials, please check and try again!')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="password"')

    def test_valid_credentials_log_user_in(self):
        user = get_user_model().objects.create_user(
            username='validuser',
            email='valid@example.com',
            password='ExamplePassword123!',
        )

        response = self.client.post(
            reverse('authentication:login'),
            {
                'username': user.username,
                'email': user.email,
                'password': 'ExamplePassword123!',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('authentication:overview'))
        self.assertEqual(self.client.session['_auth_user_id'], str(user.pk))
