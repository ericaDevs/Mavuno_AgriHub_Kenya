from django.db import models

# Create your models here.
class Order(models.Model):
    order_reff = models.CharField(max_length = 100)
    customer = models.CharField(max_length = 200)
    status = models.CharField(max_length = 20)
    item_subtotal = models.CharField(max_length = 10)
    delivery_fee = models.DecimalField(max_digits = 10, decimal_places = 2)
    total_amount = models.DecimalField(max_digits = 10, decimal_places = 2)
    created_time = models.DateTimeField(auto_now_add = True)
    updated_time = models.DateTimeField(auto_now_add = True)

    def __str__ (self):
        return self.order_reff


class OrderItem(models.Model):
    order = models.CharField(max_length = 100)
    product_name = models.CharField(max_length = 100, null = False)
    unit_price = models.DecimalField(max_digits = 10, decimal_places = 2)
    quantity = models.CharField(max_length = 20)

    def __str__ (self):
        return self.product_name