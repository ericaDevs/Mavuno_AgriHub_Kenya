from django.conf import settings
from django.db import models


class Delivery_infor(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DISPATCHED = "dispatched", "Dispatched"
        DELIVERED = "delivered", "Delivered"

    order = models.OneToOneField(
        "Orders.Order",
        on_delete=models.CASCADE,
        related_name="delivery",
    )
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20)
    email_address = models.EmailField(max_length=200, blank=True)
    delivery_Address = models.TextField()
    delivery_note = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    def __str__(self):
        return self.full_name


class MpesaPayment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        SUCCESS = "SUCCESS"
        FAILED = "FAILED"
        CANCELLED = "CANCELLED"
        TIMEOUT = "TIMEOUT"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="mpesa_payments",
    )
    order = models.ForeignKey(
        "Orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mpesa_payments",
    )
    phone = models.CharField(max_length=12)
    amount = models.PositiveIntegerField()
    merchant_request_id = models.CharField(max_length=100, blank=True)
    checkout_request_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    result_code = models.IntegerField(null=True, blank=True)
    result_desc = models.CharField(max_length=255, blank=True)
    mpesa_receipt = models.CharField(max_length=30, blank=True, unique=False)
    cart_snapshot = models.JSONField(null=True, blank=True)
    delivery_snapshot = models.JSONField(null=True, blank=True)
    raw_callback = models.JSONField(null=True, blank=True)  # keep for audits
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"MpesaPayment {self.checkout_request_id} ({self.status})"
