from django import forms
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError

from .models import Admins


class LoginForm(forms.Form):
    username = forms.CharField(max_length = 100)
    email = forms.CharField(max_length = 150)
    password = forms.CharField(widget=forms.PasswordInput, max_length = 200)


class CustomUserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, strip=False, max_length = 200)
    password_2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput,
        strip=False,
    )

    class Meta:
        model = Admins
        fields = ["username", "email", "password", "password_2"]

    def clean_password_2(self):
        password = self.cleaned_data.get("password")
        password_2 = self.cleaned_data.get("password_2")
        if password and password_2 and password != password_2:
            raise ValidationError("The two password fields didn't match.")
        return password_2

    def save(self, commit=True):
        self.instance.password = make_password(self.cleaned_data["password"])
        return super().save(commit=commit)
