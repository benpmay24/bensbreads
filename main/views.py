from django.shortcuts import render
from django.contrib.auth.forms import UserCreationForm
from . import models
from django.contrib.auth.models import User

# Create your views here.

# Home view
def home(request):
    return render(request, 'index.html')

# Games view
def games(request):
    return render(request, 'games.html')

# About view
def about(request):
    return render(request, 'about.html')

from .models import BlogPost, Recipe

def blog(request):
    posts = BlogPost.objects.all().order_by('-created_at')
    return render(request, 'blog.html', {'posts': posts})

def recipes(request):
    recipes = Recipe.objects.all().order_by('-created_at')
    return render(request, 'recipes.html', {'recipes': recipes})

from django.contrib.auth.decorators import login_required,user_passes_test
from django.shortcuts import redirect
from .forms import BlogPostForm, RecipeForm

def staff_or_superuser(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@user_passes_test(staff_or_superuser)
def add_blog_post(request):
    if request.method == 'POST':
        form = BlogPostForm(request.POST)
        if form.is_valid():
            blog_post = form.save(commit=False)
            blog_post.author = request.user
            blog_post.save()
            return redirect('blog')
    else:
        form = BlogPostForm()
    return render(request, 'add_blog_post.html', {'form': form})

# @login_required
def add_recipe(request):
    if request.method == 'POST':
        form = RecipeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('recipes')
    else:
        form = RecipeForm()
    return render(request, 'add_recipe.html', {'form': form})

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})




@user_passes_test(lambda u: u.is_superuser)
def manage_users(request):
    users = User.objects.exclude(username=request.user.username)  # Don't list self

    if request.method == "POST":
        for user in users:
            user_id_str = str(user.id)
            user.is_staff = request.POST.get(f'staff_{user_id_str}') == 'on'
            user.is_superuser = request.POST.get(f'superuser_{user_id_str}') == 'on'
            user.save()
        return redirect('manage_users')

    return render(request, "manage_users.html", {'users': users})

from django.shortcuts import get_object_or_404, redirect
from .models import BlogPost

@user_passes_test(lambda u: u.is_superuser)
def delete_blog_post(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)
    if request.method == 'POST':
        post.delete()
    return redirect('blog')

# Recipe view
def recipes(request):
    recipes = Recipe.objects.all()
    return render(request, 'recipes.html', {'recipes': recipes})

# Add Recipe view (only for staff or higher)
@login_required
@user_passes_test(lambda u: u.is_staff)
def add_recipe(request):
    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('recipes')
    else:
        form = RecipeForm()

    return render(request, 'add_recipe.html', {'form': form})

# Delete Recipe view (only for staff or higher)
@login_required
@user_passes_test(lambda u: u.is_staff)
def delete_recipe(request, pk):
    recipe = Recipe.objects.get(pk=pk)
    recipe.delete()
    return redirect('recipes')