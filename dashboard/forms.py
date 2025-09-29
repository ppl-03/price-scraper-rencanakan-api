from django import forms
from dashboard import models

class ItemPriceProvinceForm(forms.ModelForm):
    # Hints from scrape (not saved)
    source = forms.CharField(required=False)
    url = forms.URLField(required=False)

    class Meta:
        model = models.ItemPriceProvince
        fields = ["item_price", "province", "price"]

    def clean_price(self):
        p = self.cleaned_data["price"]
        if p is None or p <= 0:
            raise forms.ValidationError("Price must be greater than 0.")
        return p
