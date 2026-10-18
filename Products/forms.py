from django import forms
from django.core.exceptions import ValidationError

from .models import Product, ProductImage


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    widget = MultipleImageInput

    def clean(self, data, initial=None):
        if not data:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        return [super(MultipleImageField, self).clean(file) for file in files]


class ProductForm(forms.ModelForm):
    images = MultipleImageField(
        required=False,
        label="Product images",
        help_text="Upload 1-12 images in total. Choose multiple files to upload them together.",
    )
    remove_images = forms.ModelMultipleChoiceField(
        queryset=ProductImage.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Remove existing images",
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "description",
            "product_category",
            "price_per_unit",
            "sku",
            "stock_quantity",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "product-form-control"}),
            "description": forms.Textarea(
                attrs={"class": "product-form-control", "rows": 3}
            ),
            "product_category": forms.Select(
                attrs={"class": "product-form-control"}
            ),
            "price_per_unit": forms.NumberInput(
                attrs={"class": "product-form-control", "min": "0", "step": "0.01"}
            ),
            "sku": forms.TextInput(attrs={"class": "product-form-control"}),
            "stock_quantity": forms.NumberInput(
                attrs={"class": "product-form-control", "min": "0", "step": "1"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "h-4 w-4 rounded border-agri-forest/20"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["remove_images"].queryset = self.instance.images.all()
            self.fields["remove_images"].choices = [
                (image.pk, f"Image {index}")
                for index, image in enumerate(self.instance.images.all(), start=1)
            ]

    def clean(self):
        cleaned_data = super().clean()
        uploaded_images = cleaned_data.get("images", [])
        images_to_remove = cleaned_data.get("remove_images")
        existing_count = self.instance.images.count() if self.instance.pk else 0
        removed_count = images_to_remove.count() if images_to_remove else 0
        remaining_count = existing_count - removed_count + len(uploaded_images)

        if remaining_count < 1:
            self.add_error(
                "images", ValidationError("At least one product image is required.")
            )
        elif remaining_count > 12:
            self.add_error(
                "images", ValidationError("A product can have at most 12 images.")
            )
        return cleaned_data
