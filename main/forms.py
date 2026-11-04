from django import forms
from .models import Recipe, Ingredient, Instruction
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['title', 'description', 'time_required', 'category', 'image']

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
