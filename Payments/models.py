from django.db import models

# Create your models here.
class Delivery_infor(models.Model):
    full_name = models.CharField(max_length = 150, null = False)
    phone_number = models.CharField(max_length = 10, null = False)
    email_address = models.EmailField(max_length = 200)
    delivery_Address = models.TextField()
    delivery_note = models.TextField()
    status = models.CharField(max_length = 100)

    def __str__(self):
        return self.full_name


class Payment_infor(models.Model):
    the_order = models.CharField(max_length = 200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    customer_name = models.CharField(max_length=150, null = False)
    status = models.CharField(max_length = 50)
    transaction_reff = models.CharField(max_length = 20)
    transaction_date = models.DateTimeField(auto_now_add = True)

    def __str__ (self):
        return self.the_order
