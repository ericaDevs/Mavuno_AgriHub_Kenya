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


class Payment_infor(models.Model):
    the_order = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    customer_name = models.CharField(max_length=150)
    status = models.CharField(max_length=50)
    transaction_reff = models.CharField(max_length=20)
    transaction_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.the_order
