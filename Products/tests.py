from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Product


class ProductManagementTests(TestCase):
    def setUp(self):
        self.media_dir = TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        session = self.client.session
        session["admin_id"] = 1
        session.save()

    def image_upload(self, name="product.png"):
        buffer = BytesIO()
        Image.new("RGB", (2, 2), color="green").save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

    def product_data(self, **overrides):
        data = {
            "name": "Hybrid maize seed",
            "description": "A reliable high-yield seed.",
            "product_category": Product.Category.SEEDS,
            "price_per_unit": "1250.00",
            "sku": "MAIZE-001",
            "stock_quantity": "25",
            "is_active": "on",
        }
        data.update(overrides)
        return data

    def test_catalog_renders_active_database_products_with_the_shared_layout(self):
        product = Product.objects.create(
            name="Hybrid maize seed",
            description="A reliable high-yield seed.",
            product_category=Product.Category.SEEDS,
            price_per_unit="1250.00",
            stock_quantity=25,
        )
        product_image = product.images.create(image=self.image_upload())
        Product.objects.create(
            name="Hidden product",
            description="Not shown in the public catalog.",
            product_category=Product.Category.SEEDS,
            price_per_unit="10.00",
            is_active=False,
        )

        response = self.client.get(reverse("products:products"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hybrid maize seed")
        self.assertContains(response, "A reliable high-yield seed.")
        self.assertContains(response, "KSh 1250.00")
        self.assertContains(response, product_image.image.url)
        self.assertContains(response, "Categories")
        self.assertContains(response, "Browse category")
        self.assertContains(response, "xl:grid-cols-3")
        self.assertContains(response, "Connecting farmers to the knowledge")
        self.assertNotContains(response, "Hidden product")

    def test_catalog_search_and_category_filters(self):
        Product.objects.create(
            name="Hybrid maize seed",
            description="A reliable high-yield seed.",
            product_category=Product.Category.SEEDS,
            price_per_unit="1250.00",
        )
        Product.objects.create(
            name="Organic fertilizer",
            description="Nutrient-rich soil treatment.",
            product_category=Product.Category.FERTILIZERS,
            price_per_unit="800.00",
        )

        response = self.client.get(
            reverse("products:products"),
            {"q": "maize", "category": Product.Category.SEEDS},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hybrid maize seed")
        self.assertNotContains(response, "Organic fertilizer")

    def test_homepage_renders_product_cards_with_actions(self):
        Product.objects.create(
            name="Hybrid maize seed",
            description="A reliable high-yield seed.",
            product_category=Product.Category.SEEDS,
            price_per_unit="1250.00",
            stock_quantity=25,
        )

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hybrid maize seed")
        self.assertContains(response, "Add to cart")
        self.assertContains(response, "View Product")
        self.assertContains(response, "Why Choose Mavuno AgriHub?")
        self.assertContains(response, "Trusted farm inputs")
        self.assertContains(response, "Farm care made simple")
        self.assertContains(response, "Sustainable growing")

    def test_product_list_requires_admin_session(self):
        self.client.session.flush()
        response = self.client.get(reverse("admin:products"))
        self.assertRedirects(response, reverse("admin:login"))

    def test_admin_can_create_product_with_images(self):
        response = self.client.post(
            reverse("admin:product_add"),
            {**self.product_data(), "images": [self.image_upload()]},
        )

        self.assertRedirects(response, reverse("admin:products"))
        product = Product.objects.get(sku="MAIZE-001")
        self.assertEqual(product.images.count(), 1)
        self.assertEqual(product.stock_quantity, 25)

    def test_product_management_page_renders_existing_product_and_image(self):
        product = Product.objects.create(
            name="Hybrid maize seed",
            description="A reliable high-yield seed.",
            product_category=Product.Category.SEEDS,
            price_per_unit="1250.00",
            stock_quantity=25,
        )
        product_image = product.images.create(image=self.image_upload())

        response = self.client.get(reverse("admin:products"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hybrid maize seed")
        self.assertContains(response, "min-w-[760px]")
        self.assertContains(response, "<table")
        self.assertContains(response, "product-edit-dialog-")
        self.assertTrue(product_image.image.storage.exists(product_image.image.name))

    def test_product_requires_at_least_one_image(self):
        response = self.client.post(
            reverse("admin:product_add"),
            self.product_data(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.exists())
        self.assertContains(response, "At least one product image is required.")

    def test_product_price_cannot_be_negative(self):
        response = self.client.post(
            reverse("admin:product_add"),
            {
                **self.product_data(price_per_unit="-1.00"),
                "images": [self.image_upload()],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.exists())

    def test_product_cannot_have_more_than_twelve_images(self):
        response = self.client.post(
            reverse("admin:product_add"),
            {
                **self.product_data(),
                "images": [self.image_upload(f"product-{index}.png") for index in range(13)],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.exists())
        self.assertContains(response, "A product can have at most 12 images.")

    def test_admin_can_edit_and_remove_product(self):
        product = Product.objects.create(
            name="Old name",
            description="Old description",
            product_category=Product.Category.SEEDS,
            price_per_unit="12.00",
            stock_quantity=2,
        )
        existing_image = product.images.create(image=self.image_upload("old.png"))

        response = self.client.post(
            reverse("admin:product_edit", args=[product.pk]),
            {
                **self.product_data(name="Updated seed", sku="", stock_quantity="8"),
                "remove_images": str(existing_image.pk),
                "images": [self.image_upload("new.png")],
            },
        )

        self.assertRedirects(response, reverse("admin:products"))
        product.refresh_from_db()
        self.assertEqual(product.name, "Updated seed")
        self.assertEqual(product.stock_quantity, 8)
        self.assertEqual(product.images.count(), 1)
        self.assertFalse(product.images.filter(pk=existing_image.pk).exists())

        response = self.client.post(reverse("admin:product_delete", args=[product.pk]))
        self.assertRedirects(response, reverse("admin:products"))
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
