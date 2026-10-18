from django.core.validators import MinValueValidator
from django.db import models


class Product(models.Model):
    class Category(models.TextChoices):
        SEEDS = "seeds", "Seeds"
        FERTILIZERS = "fertilizers", "Fertilizers"
        TOOLS = "tools", "Tools"
        IRRIGATION = "irrigation", "Irrigation"
        PEST_CONTROL = "pest-control", "Pest control"
        CROP_CARE = "crop-care", "Crop care"
        OTHER = "other", "Other"

    name = models.CharField(max_length=200)
    description = models.TextField()
    product_category = models.CharField(max_length=30, choices=Category.choices)
    price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    sku = models.CharField(max_length=64, unique=True, blank=True, null=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        related_name="images",
        on_delete=models.CASCADE,
    )
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return f"Image for {self.product.name}"
