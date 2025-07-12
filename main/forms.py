from django import forms
from .models import BlogPost, Recipe, RamseyPhoto, Ingredient, Instruction
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ['title', 'content', 'private']

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