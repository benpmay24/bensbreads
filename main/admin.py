from django.contrib import admin

# Register your models here.
from .models import BlogPost, Recipe

admin.site.register(BlogPost)
admin.site.register(Recipe)