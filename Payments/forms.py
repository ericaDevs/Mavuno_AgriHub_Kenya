from django import forms


class CustomerDeliveryInfor(forms.Form):
    full_name = forms.CharField(max_length=150)
    phone = forms.CharField(max_length=20)
    email = forms.EmailField(max_length=200, required=False)
    delivery_address = forms.CharField(widget=forms.Textarea)
    delivery_notes = forms.CharField(widget=forms.Textarea, required=False)

    def __str__ (self):
        self.Meta