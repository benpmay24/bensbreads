from django import forms
from .models import Recipe, Ingredient, Instruction
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['title', 'description', 'time_required', 'image']

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(required=True, max_length=30)
    last_name = forms.CharField(required=True, max_length=30)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ['quantity', 'name']
        widgets = {
            'quantity': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 500 g', 'aria-label': 'Amount'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. bread flour', 'aria-label': 'Ingredient'}),
        }


class InstructionForm(forms.ModelForm):
    class Meta:
        model = Instruction
        fields = ['step_text']
        widgets = {
            'step_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Describe this step...',
                'aria-label': 'Step instructions',
            }),
        }
