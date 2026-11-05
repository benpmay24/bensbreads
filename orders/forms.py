from django import forms

from .models import MAX_QUANTITY, Product


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """An image field that accepts several files at once and returns a list."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput(attrs={'accept': 'image/*'}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(d, initial) for d in data if d]
        return [single_clean(data, initial)] if data else []


class ProductForm(forms.ModelForm):
    new_images = MultipleImageField(required=False, label='Photos')

    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'is_available']
        labels = {'is_available': 'Show on the order page'}
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Country Sourdough'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Flavor, size, ingredients worth knowing...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        existing = self.instance.images.all() if self.instance.pk else []
        self.fields['remove_images'] = forms.MultipleChoiceField(
            required=False,
            choices=[(str(img.pk), str(img.pk)) for img in existing],
            widget=forms.CheckboxSelectMultiple,
        )
        self.existing_images = list(existing)

    def clean(self):
        cleaned = super().clean()
        removing = set(cleaned.get('remove_images') or [])
        kept = [img for img in self.existing_images if str(img.pk) not in removing]
        if not kept and not cleaned.get('new_images'):
            self.add_error('new_images', 'Add at least one photo.')
        return cleaned


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=MAX_QUANTITY, initial=1)


class CheckoutForm(forms.Form):
    notes = forms.CharField(
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Anything we should know? (pickup time, allergies...)'}),
    )
