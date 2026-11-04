from django import forms
from main.models import BlogPost, RamseyPhoto, RamseyProfile, VaccineRecord, BoardingExperience, DietEntry, VaccineDocument, DietDocument, BoardingDocument

class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ['title', 'content', 'image', 'private']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
        }

    private = forms.BooleanField(required=False, label="Mark as Private", initial=False)

class RamseyPhotoForm(forms.ModelForm):
    class Meta:
        model = RamseyPhoto
        fields = ['title', 'image', 'caption', 'date_taken']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a title for this photo'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'caption': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Tell us about this photo...'
            }),
            'date_taken': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'style': 'max-width: 200px;'
            })
        }

class RamseyProfileForm(forms.ModelForm):
    class Meta:
        model = RamseyProfile
        fields = ['name', 'breed', 'date_of_birth', 'bio', 'profile_picture']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ramsey'}),
            'breed': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Golden Retriever'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell us about Ramsey...'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }

class VaccineRecordForm(forms.ModelForm):
    class Meta:
        model = VaccineRecord
        fields = ['vaccine_name', 'date_administered', 'expiration_date', 'veterinarian', 'notes']
        widgets = {
            'vaccine_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Rabies, DHPP'}),
            'date_administered': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiration_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'veterinarian': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Veterinarian name'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class BoardingExperienceForm(forms.ModelForm):
    class Meta:
        model = BoardingExperience
        fields = ['facility_name', 'address', 'city', 'state', 'phone', 'website', 'check_in_date', 'check_out_date', 'review']
        widgets = {
            'facility_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Facility name'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Website URL'}),
            'check_in_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'check_out_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'review': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Share your experience...'}),
        }

class DietEntryForm(forms.ModelForm):
    class Meta:
        model = DietEntry
        fields = ['food_name', 'brand', 'food_type', 'date_started', 'date_ended', 'is_current', 'notes']
        widgets = {
            'food_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Food name'}),
            'brand': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brand name'}),
            'food_type': forms.Select(attrs={'class': 'form-control'}),
            'date_started': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_ended': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class VaccineDocumentForm(forms.ModelForm):
    class Meta:
        model = VaccineDocument
        fields = ['document', 'document_name']
        widgets = {
            'document': forms.FileInput(attrs={'class': 'form-control'}),
            'document_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Rabies Certificate'}),
        }

class DietDocumentForm(forms.ModelForm):
    class Meta:
        model = DietDocument
        fields = ['document', 'document_name']
        widgets = {
            'document': forms.FileInput(attrs={'class': 'form-control'}),
            'document_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Food Receipt'}),
        }

class BoardingDocumentForm(forms.ModelForm):
    class Meta:
        model = BoardingDocument
        fields = ['document', 'document_name']
        widgets = {
            'document': forms.FileInput(attrs={'class': 'form-control'}),
            'document_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Boarding Agreement'}),
        }
