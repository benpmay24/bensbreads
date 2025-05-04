from django import forms
from .models import BlogPost, Recipe, RamseyPhoto

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