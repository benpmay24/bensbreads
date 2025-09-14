from django import forms
from .models import BlogPost, Recipe, RamseyPhoto, Ingredient, Instruction, Review
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ['title', 'content', 'image', 'private']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
        }

    private = forms.BooleanField(required=False, label="Mark as Private", initial=False)

class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['title', 'description', 'time_required', 'category', 'image']

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

# Custom form extending UserCreationForm
class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(required=True, max_length=30)
    last_name = forms.CharField(required=True, max_length=30)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

class IngredientForm(forms.ModelForm):
    DELETE = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input delete-checkbox'
        })
    )
    
    class Meta:
        model = Ingredient
        fields = ['quantity', 'name']
        widgets = {
            'quantity': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class InstructionForm(forms.ModelForm):
    DELETE = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input delete-checkbox'
        })
    )
    
    class Meta:
        model = Instruction
        fields = ['step_text']
        widgets = {
            'step_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['place_name', 'location', 'food_rating', 'ambience_rating', 'value_rating', 'service_rating', 'overall_rating', 'content', 'image']  # Added service_rating and overall_rating
        widgets = {
            'place_name': forms.TextInput(attrs={'placeholder': 'Name of restaurant, cafe, etc.'}),
            'location': forms.TextInput(attrs={'placeholder': 'City, neighborhood, etc.'}),
            'content': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Share your experience...'}),
            'food_rating': forms.RadioSelect(),
            'ambience_rating': forms.RadioSelect(),
            'value_rating': forms.RadioSelect(),
            'service_rating': forms.RadioSelect(),
            'overall_rating': forms.RadioSelect(),
        }