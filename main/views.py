import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from .models import BlogPost, Recipe, Ingredient, Instruction, RamseyPhoto, Connect4Result, WordFindScore
from .forms import BlogPostForm, RecipeForm, RamseyPhotoForm, CustomUserCreationForm, IngredientForm, InstructionForm
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .connect4.board import board
from .connect4.eval_cpu_moves import evalMoves
from .connect4.generate_default import generateDefault
from django.http import HttpResponse
from django.forms import inlineformset_factory
import requests

# Home, Games, About, Blog, Signup, Manage Users views — same as you wrote

def staff_or_superuser(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

def home(request):
    # Get all recipes that are marked as featured
    featured_recipes = Recipe.objects.filter(featured=True)
    return render(request, 'index.html', {'featured_recipes': featured_recipes})

def games(request):
    return render(request, 'games.html')

# Home view (showing public posts)
def blog(request):
    posts = BlogPost.objects.filter(private=False).order_by('-created_at')  # Only non-private posts
    return render(request, 'blog.html', {'posts': posts})

# views.py
from django.http import HttpResponseForbidden

# Secrets page (only superusers)
def secrets(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Admin privileges required.')
    posts = BlogPost.objects.filter(private=True).order_by('-created_at')
    return render(request, 'blog.html', {'posts': posts, 'is_secrets': True})

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'signup.html', {'form': form})

@user_passes_test(lambda u: u.is_superuser)
def manage_users(request):
    users = User.objects.exclude(username=request.user.username)
    if request.method == "POST":
        for user in users:
            user_id_str = str(user.id)
            user.is_staff = request.POST.get(f'staff_{user_id_str}') == 'on'
            user.is_superuser = request.POST.get(f'superuser_{user_id_str}') == 'on'
            user.save()
        return redirect('manage_users')
    return render(request, "manage_users.html", {'users': users})

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

@user_passes_test(lambda u: u.is_superuser)
def delete_blog_post(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)
    if request.method == 'POST':
        post.delete()
    return redirect('blog')

def recipes(request):
    recipes = Recipe.objects.all().order_by('-created_at')
    return render(request, 'recipes.html', {'recipes': recipes})

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from .forms import RecipeForm
from .models import Recipe, Ingredient, Instruction

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from .forms import RecipeForm
from .models import Recipe, Ingredient, Instruction
from django.db.models import Count, Q



@login_required
@user_passes_test(lambda u: u.is_staff)
def add_recipe(request):
    from django.forms import inlineformset_factory
    
    # Create formsets for ingredients and instructions
    IngredientFormSet = inlineformset_factory(
        Recipe, Ingredient, 
        form=IngredientForm,
        extra=1,  # Show one empty form by default
        can_delete=True
    )
    InstructionFormSet = inlineformset_factory(
        Recipe, Instruction, 
        form=InstructionForm,
        extra=1,  # Show one empty form by default
        can_delete=True
    )
    
    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES)
        ingredient_formset = IngredientFormSet(request.POST, prefix='ingredients')
        instruction_formset = InstructionFormSet(request.POST, prefix='instructions')
        
        if form.is_valid() and ingredient_formset.is_valid() and instruction_formset.is_valid():
            with transaction.atomic():
                recipe = form.save(commit=False)
                recipe.featured = 'featured' in request.POST
                recipe.save()
                
                # Save ingredients
                ingredient_formset.instance = recipe
                ingredient_formset.save()
                
                # Save instructions
                instruction_formset.instance = recipe
                instructions = instruction_formset.save(commit=False)
                for i, instruction in enumerate(instructions):
                    instruction.step_number = i + 1
                    instruction.save()

            return redirect('recipes')
    else:
        form = RecipeForm()
        ingredient_formset = IngredientFormSet(prefix='ingredients')
        instruction_formset = InstructionFormSet(prefix='instructions')

    return render(request, 'add_recipe.html', {
        'form': form,
        'ingredient_formset': ingredient_formset,
        'instruction_formset': instruction_formset,
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def delete_recipe(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    if request.method == 'POST':
        if recipe.image:
            recipe.image.delete(save=False)
        recipe.delete()
    return redirect('recipes')

def ramsey_bio(request):
    return render(request, 'ramsey_bio.html')

def ramsey_gallery(request):
    photos = RamseyPhoto.objects.all().order_by('-uploaded_at')  # adjust as needed
    return render(request, 'ramsey_gallery.html', {'photos': photos})

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def upload_ramsey_photo(request):
    if request.method == 'POST':
        form = RamseyPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('ramsey_gallery')
    else:
        form = RamseyPhotoForm()
    return render(request, 'upload_ramsey_photo.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def toggle_featured_recipe(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    recipe.featured = not recipe.featured  # Toggle the featured status
    recipe.save()
    return redirect('recipes')  # Redirect back to the recipes page after toggling

def connect4 (request):
    return render(request,"connect4.html")

# Replace with your logic to determine CPU's move
def get_cpu_move(cur_board):
    # Example: Just pick the first empty column for simplicity
    current_board=board(blankChar=None,P1="red",P2="yellow",numRows=6,numCols=7,content=cur_board)
    [points,scores]=generateDefault()
    move=evalMoves(current_board,"yellow",points)
    return move  # No valid moves left

@csrf_exempt
def cpu_move(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        board = data.get('board')
        move = get_cpu_move(board)
        return JsonResponse({'move': move})

    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
@login_required
def save_connect4_result(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        result = data.get('result')
        if result in ['win', 'loss', 'tie']:
            Connect4Result.objects.create(user=request.user, result=result)
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'invalid result'}, status=400)
    
@login_required
def connect4_leaderboard(request):
    leaderboard = User.objects.annotate(
        wins=Count('connect4result', filter=Q(connect4result__result='win')),
        losses=Count('connect4result', filter=Q(connect4result__result='loss')),
        ties=Count('connect4result', filter=Q(connect4result__result='tie'))
    ).values('username', 'wins', 'losses', 'ties')

    return JsonResponse(list(leaderboard), safe=False)

def health(request):
    """
    Simple health check that just returns OK
    Faster response for basic keep-alive pings
    """
    return HttpResponse("OK", status=200)

@login_required
@user_passes_test(lambda u: u.is_staff)
def edit_recipe(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    
    # Create formsets for ingredients and instructions using custom forms
    IngredientFormSet = inlineformset_factory(
        Recipe, Ingredient, 
        form=IngredientForm,
        extra=0,  # Don't show empty forms by default
        can_delete=True
    )
    InstructionFormSet = inlineformset_factory(
        Recipe, Instruction, 
        form=InstructionForm,
        extra=0,  # Don't show empty forms by default
        can_delete=True
    )
    
    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES, instance=recipe)
        ingredient_formset = IngredientFormSet(request.POST, instance=recipe, prefix='ingredients')
        instruction_formset = InstructionFormSet(request.POST, instance=recipe, prefix='instructions')
        
        if form.is_valid() and ingredient_formset.is_valid() and instruction_formset.is_valid():
            with transaction.atomic():
                # Update the recipe
                recipe = form.save(commit=False)
                recipe.featured = 'featured' in request.POST
                recipe.save()
                
                # Save the formsets - they handle creation, updates, and deletions automatically
                ingredient_formset.save()
                
                # Save instructions and update step numbers for remaining instructions
                instructions = instruction_formset.save(commit=False)
                # Delete marked instructions first
                for instruction in instruction_formset.deleted_objects:
                    instruction.delete()
                
                # Save and renumber remaining instructions
                for i, instruction in enumerate(instructions):
                    instruction.recipe = recipe
                    instruction.step_number = i + 1
                    instruction.save()

            return redirect('recipes')
    else:
        form = RecipeForm(instance=recipe)
        ingredient_formset = IngredientFormSet(instance=recipe, prefix='ingredients')
        instruction_formset = InstructionFormSet(instance=recipe, prefix='instructions')

    return render(request, 'edit_recipe.html', {
        'form': form,
        'recipe': recipe,
        'ingredient_formset': ingredient_formset,
        'instruction_formset': instruction_formset,
    })

def recipe_detail(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    return render(request, 'recipe_detail.html', {'recipe': recipe})

def word_find(request):
    return render(request, 'word_find.html')

def validate_word(request):
    if request.method == 'POST':
        word = request.POST.get('word', '').lower()
        if not word:
            return JsonResponse({'valid': False, 'error': 'No word provided'})

        try:
            # Check if the word is valid using an external dictionary API
            response = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
            if response.status_code == 200:
                return JsonResponse({'valid': True})
            else:
                return JsonResponse({'valid': False, 'error': f"API returned status {response.status_code}"})
        except requests.exceptions.RequestException as e:
            return JsonResponse({'valid': False, 'error': f"API request failed: {str(e)}"})

    return JsonResponse({'error': 'Invalid request'}, status=400)

def word_find_leaderboard(request):
    scores = WordFindScore.objects.order_by('-score')[:10]
    leaderboard = [{'user': score.user.username, 'score': score.score} for score in scores]
    return JsonResponse({'leaderboard': leaderboard})

@csrf_exempt
@login_required
def save_word_find_result(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        score = data.get('score')
        if score is not None:
            WordFindScore.objects.create(user=request.user, score=score)
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'invalid score'}, status=400)