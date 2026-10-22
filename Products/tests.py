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
        self.assertContains(response, "View Details")
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

    def test_product_detail_shows_active_product_information_and_images(self):
        product = Product.objects.create(
            name="Hybrid maize seed",
            description="A reliable high-yield seed.",
            product_category=Product.Category.SEEDS,
            price_per_unit="1250.00",
            sku="MAIZE-001",
            stock_quantity=25,
        )
        product_image = product.images.create(image=self.image_upload())

        response = self.client.get(reverse("products:detail", args=[product.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["product"], product)
        self.assertContains(response, "Hybrid maize seed")
        self.assertContains(response, "A reliable high-yield seed.")
        self.assertContains(response, "KSh 1250.00")
        self.assertContains(response, "MAIZE-001")
        self.assertContains(response, "25")
        self.assertContains(response, product_image.image.url)
        self.assertContains(response, "Enquire about this product")
        self.assertContains(response, "Continue shopping")

    def test_product_detail_does_not_show_inactive_or_missing_products(self):
        inactive_product = Product.objects.create(
            name="Inactive seed",
            description="Not available.",
            product_category=Product.Category.SEEDS,
            price_per_unit="100.00",
            is_active=False,
        )

        response = self.client.get(reverse("products:detail", args=[inactive_product.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            self.client.get(reverse("products:detail", args=[99999])).status_code,
            404,
        )

    def test_catalog_and_home_product_actions_link_to_product_detail(self):
        product = Product.objects.create(
            name="Hybrid maize seed",
            description="A reliable high-yield seed.",
            product_category=Product.Category.SEEDS,
            price_per_unit="1250.00",
        )

        catalog_response = self.client.get(reverse("products:products"))
        home_response = self.client.get(reverse("home"))
        detail_url = reverse("products:detail", args=[product.pk])

        self.assertContains(catalog_response, f'href="{detail_url}"')
        self.assertContains(home_response, f'href="{detail_url}"')

    def test_add_to_cart_saves_product_quantity_and_displays_summary(self):
        product = Product.objects.create(
            name="Hybrid maize seed",
            description="A reliable high-yield seed.",
            product_category=Product.Category.SEEDS,
            price_per_unit="1250.00",
            stock_quantity=5,
        )

        response = self.client.post(reverse("products:cart_add", args=[product.pk]))

        self.assertRedirects(response, reverse("products:cart"))
        self.assertEqual(self.client.session["cart"], {str(product.pk): 1})
        cart_response = self.client.get(reverse("products:cart"))
        self.assertContains(cart_response, "Hybrid maize seed")
        self.assertContains(cart_response, "KSh 1250.00")
        self.assertContains(cart_response, "Order summary")
        self.assertContains(cart_response, "Checkout coming soon")
        self.assertEqual(cart_response.context["cart_item_count"], 1)
        self.assertContains(cart_response, 'aria-label="Shopping cart, 1 item"')

    def test_ajax_cart_add_returns_cart_fragment_and_count_without_redirect(self):
        product = Product.objects.create(
            name="Hybrid maize seed",
            description="A reliable high-yield seed.",
            product_category=Product.Category.SEEDS,
            price_per_unit="1250.00",
            stock_quantity=5,
        )

        response = self.client.post(
            reverse("products:cart_add", args=[product.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["item_count"], 1)
        self.assertContains(response, "Hybrid maize seed")
        self.assertIn("added to your cart", response.json()["messages"][0]["text"])

    def test_ajax_cart_quantity_action_returns_updated_fragment(self):
        product = Product.objects.create(
            name="Hybrid maize seed",
            description="A reliable high-yield seed.",
            product_category=Product.Category.SEEDS,
            price_per_unit="1250.00",
            stock_quantity=5,
        )
        session = self.client.session
        session["cart"] = {str(product.pk): 1}
        session.save()

        response = self.client.post(
            reverse("products:cart_update", args=[product.pk]),
            {"adjustment": "1"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["item_count"], 2)
        self.assertContains(response, ">2<")

    def test_cart_plus_and_minus_actions_and_remove(self):
        product = Product.objects.create(
            name="Hybrid maize seed",
            description="A reliable high-yield seed.",
            product_category=Product.Category.SEEDS,
            price_per_unit="1250.00",
            stock_quantity=5,
        )
        session = self.client.session
        session["cart"] = {str(product.pk): 1}
        session.save()

        add_response = self.client.post(
            reverse("products:cart_update", args=[product.pk]),
            {"adjustment": "1"},
        )
        self.assertRedirects(add_response, reverse("products:cart"))
        self.assertEqual(self.client.session["cart"], {str(product.pk): 2})

        decrease_response = self.client.post(
            reverse("products:cart_update", args=[product.pk]),
            {"adjustment": "-1"},
        )
        self.assertRedirects(decrease_response, reverse("products:cart"))
        self.assertEqual(self.client.session["cart"], {str(product.pk): 1})

        decrease_response = self.client.post(
            reverse("products:cart_update", args=[product.pk]),
            {"adjustment": "-1"},
        )
        self.assertRedirects(decrease_response, reverse("products:cart"))
        self.assertEqual(self.client.session["cart"], {})

        session = self.client.session
        session["cart"] = {str(product.pk): 1}
        session.save()
        remove_response = self.client.post(reverse("products:cart_remove", args=[product.pk]))
        self.assertRedirects(remove_response, reverse("products:cart"))
        self.assertEqual(self.client.session["cart"], {})
        self.assertContains(self.client.get(reverse("products:cart")), "Your cart is empty")

    def test_cart_plus_respects_stock_and_invalid_adjustments_are_ignored(self):
        product = Product.objects.create(
            name="Hybrid maize seed",
            description="A reliable high-yield seed.",
            product_category=Product.Category.SEEDS,
            price_per_unit="1250.00",
            stock_quantity=2,
        )

        add_to_home = self.client.post(
            reverse("products:cart_add", args=[product.pk]),
            {"quantity": "2", "next": reverse("home")},
        )
        self.assertRedirects(add_to_home, reverse("home"))
        self.assertEqual(self.client.session["cart"], {str(product.pk): 2})
        home_response = self.client.get(reverse("home"))
        self.assertEqual(home_response.context["cart_item_count"], 2)
        self.assertContains(home_response, 'aria-label="Shopping cart, 2 items"')

        self.client.post(
            reverse("products:cart_add", args=[product.pk]),
            {"quantity": "5"},
        )
        self.assertEqual(self.client.session["cart"], {str(product.pk): 2})

        increase_response = self.client.post(
            reverse("products:cart_update", args=[product.pk]),
            {"adjustment": "1"},
        )
        self.assertRedirects(increase_response, reverse("products:cart"))
        self.assertEqual(self.client.session["cart"], {str(product.pk): 2})

        invalid_response = self.client.post(
            reverse("products:cart_update", args=[product.pk]),
            {"adjustment": "0"},
        )
        self.assertRedirects(invalid_response, reverse("products:cart"))
        self.assertEqual(self.client.session["cart"], {str(product.pk): 2})

    def test_cart_get_prunes_unavailable_and_missing_products(self):
        product = Product.objects.create(
            name="Out of stock seed",
            description="No stock remains.",
            product_category=Product.Category.SEEDS,
            price_per_unit="100.00",
            stock_quantity=0,
        )
        session = self.client.session
        session["cart"] = {str(product.pk): 2, "99999": 1}
        session.save()

        response = self.client.get(reverse("products:cart"))

        self.assertContains(response, "Your cart is empty")
        self.assertEqual(self.client.session["cart"], {})

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
