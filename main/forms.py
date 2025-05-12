from django import forms
from .models import BlogPost, Recipe, RamseyPhoto
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
        fields = ['title', 'description', 'time_required', 'image']

class RamseyPhotoForm(forms.ModelForm):
    class Meta:
        model = RamseyPhoto
        fields = ['image']

# Custom form extending UserCreationForm
class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(required=True, max_length=30)
    last_name = forms.CharField(required=True, max_length=30)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']