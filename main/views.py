import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from .models import BlogPost, Recipe, Ingredient, Instruction, RamseyPhoto, Connect4Result, WordFindScore, Comment, Review
from .forms import BlogPostForm, RecipeForm, RamseyPhotoForm, CustomUserCreationForm, IngredientForm, InstructionForm, ReviewForm
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .connect4.board import board
from .connect4.eval_cpu_moves import evalMoves
from .connect4.generate_default import generateDefault
from django.http import HttpResponse
from django.forms import inlineformset_factory
import requests
from django.conf import settings
from django.views.decorators.http import require_GET

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
    
    # Handle comment submission
    if request.method == 'POST' and request.user.is_authenticated:
        post_id = request.POST.get('post_id')
        comment_text = request.POST.get('comment', '').strip()
        if (post_id and comment_text):
            try:
                post = BlogPost.objects.get(id=post_id)
                Comment.objects.create(
                    post=post,
                    user=request.user,
                    text=comment_text
                )
            except BlogPost.DoesNotExist:
                pass
        return redirect('blog')
    
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
    return render(request, 'registration/signup.html', {'form': form})

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
        form = BlogPostForm(request.POST, request.FILES)
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
    bread_recipes = recipes.filter(category='bread')
    other_recipes = recipes.filter(category='other')
    return render(request, 'recipes.html', {
        'recipes': recipes,
        'bread_recipes': bread_recipes,
        'other_recipes': other_recipes
    })

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
from django.db.models import Count, Q, F, FloatField, ExpressionWrapper



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
                recipe.author = request.user  # Set the author to the current user
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
def delete_ramsey_photo(request, pk):
    photo = get_object_or_404(RamseyPhoto, pk=pk)
    if request.method == 'POST':
        if photo.image:
            photo.image.delete(save=False)
        photo.delete()
    return redirect('ramsey_gallery')

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
    
def connect4_leaderboard(request):
    # Only include users who have played at least one game
    leaderboard = User.objects.annotate(
        wins=Count('connect4result', filter=Q(connect4result__result='win')),
        losses=Count('connect4result', filter=Q(connect4result__result='loss')),
        ties=Count('connect4result', filter=Q(connect4result__result='tie')),
    ).annotate(
        total_games=F('wins') + F('losses') + F('ties')
    ).filter(
        total_games__gt=0
    ).values('username', 'wins', 'losses', 'ties', 'total_games')

    # Add win_percentage to each entry
    leaderboard = [
        {
            **entry,
            'win_percentage': (entry['wins'] / entry['total_games']) if entry['total_games'] > 0 else 0
        }
        for entry in leaderboard
    ]

    # Sort by win_percentage descending, then by wins descending
    leaderboard.sort(key=lambda x: (x['win_percentage'], x['wins']), reverse=True)

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

def reviews(request):
    """Display recent reviews with filter options."""
    # Get filter parameters from the request
    tag_filter = request.GET.get('tag', None)
    reviewer_filter = request.GET.get('reviewer', None)
    city_filter = request.GET.get('city', None)
    
    # Start with all reviews
    reviews_query = Review.objects.all()
    
    # Apply filters if present
    if tag_filter:
        # Instead of using contains lookup on JSON field which isn't supported by SQLite,
        # we'll filter after we get the queryset results
        pass
    
    if reviewer_filter:
        reviews_query = reviews_query.filter(author_id=reviewer_filter)
    
    if city_filter:
        # Now use the dedicated city field instead of location
        reviews_query = reviews_query.filter(city=city_filter)
    
    # Order by most recent
    reviews_query = reviews_query.order_by('-created_at')
    
    # If we have a tag filter, manually filter the queryset after database retrieval
    if tag_filter:
        filtered_reviews = []
        for review in reviews_query:
            if review.place_tags and any(tag_filter.lower() in tag.lower().replace('_', ' ') for tag in review.place_tags):
                filtered_reviews.append(review)
        recent_reviews = filtered_reviews[:12]  # Limit to 12 results
    else:
        recent_reviews = reviews_query[:12]  # Limit to 12 results
    
    # Get all unique tags from all reviews for the filter dropdown
    all_tags = set()
    for review in Review.objects.all():
        if review.place_tags:
            for tag in review.place_tags:
                all_tags.add(tag.replace('_', ' ').title())
    
    # Get all reviewers who have written reviews
    reviewers = User.objects.filter(reviews__isnull=False).distinct()
    
    # Get all cities from the dedicated city field
    cities = Review.objects.exclude(city__isnull=True).exclude(city='').values_list('city', flat=True).distinct()
    
    return render(request, 'reviews.html', {
        'recent_reviews': recent_reviews,
        'all_tags': sorted(all_tags),
        'reviewers': reviewers,
        'cities': sorted(cities),
        'active_tag': tag_filter,
        'active_reviewer': reviewer_filter,
        'active_city': city_filter,
    })

def review_detail(request, pk):
    """Display a specific review."""
    review = get_object_or_404(Review, pk=pk)
    return render(request, 'review_detail.html', {'review': review})

@login_required
@user_passes_test(lambda u: u.is_staff)
def add_review(request):
    """Add a new review."""
    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            review = form.save(commit=False)
            review.author = request.user

            # Use the correct key to fetch the category
            category = request.POST.get('category')
            review.category = category if category else 'Uncategorized'

            # Parse and store address components
            location = request.POST.get('location', '')
            review.location = location  # Keep the full address for backward compatibility
            
            # Parse address components (basic implementation)
            if location:
                parts = location.split(',')
                if len(parts) >= 3:  # Format: Street, City, State ZIP
                    review.street_address = parts[0].strip()
                    review.city = parts[1].strip()
                    state_zip = parts[2].strip().split(' ', 1)
                    review.state = state_zip[0].strip()
                    if len(state_zip) > 1:
                        review.zip_code = state_zip[1].strip()
                elif len(parts) == 2:  # Format: City, State
                    review.city = parts[0].strip()
                    review.state = parts[1].strip()
                elif len(parts) == 1:  # Just a city or location name
                    review.city = parts[0].strip()

            # Save additional place details
            review.place_website = request.POST.get('place_website', '')
            review.place_phone = request.POST.get('place_phone', '')
            review.place_tags = json.loads(request.POST.get('place_tags', '[]'))  # Expecting JSON array
            review.place_photo_url = request.POST.get('place_photo_url', '')

            review.save()
            return redirect('review_detail', pk=review.id)
    else:
        form = ReviewForm()

    return render(request, 'add_review.html', {
        'form': form,
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def edit_review(request, pk):
    """Edit an existing review."""
    review = get_object_or_404(Review, id=pk)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES, instance=review)
        if form.is_valid():
            review = form.save(commit=False)
            
            # Use the correct key to fetch the category
            category = request.POST.get('category')
            review.category = category if category else 'Uncategorized'

            # Parse and store address components
            location = request.POST.get('location', '')
            review.location = location  # Keep the full address for backward compatibility
            
            # Parse address components (basic implementation)
            if location:
                parts = location.split(',')
                if len(parts) >= 3:  # Format: Street, City, State ZIP
                    review.street_address = parts[0].strip()
                    review.city = parts[1].strip()
                    state_zip = parts[2].strip().split(' ', 1)
                    review.state = state_zip[0].strip()
                    if len(state_zip) > 1:
                        review.zip_code = state_zip[1].strip()
                elif len(parts) == 2:  # Format: City, State
                    review.city = parts[0].strip()
                    review.state = parts[1].strip()
                elif len(parts) == 1:  # Just a city or location name
                    review.city = parts[0].strip()

            # Save additional place details
            review.place_website = request.POST.get('place_website', '')
            review.place_phone = request.POST.get('place_phone', '')
            
            # Handle place_tags specially - it might be already a JSON string
            place_tags = request.POST.get('place_tags', '[]')
            try:
                # First, try to parse it as JSON
                json.loads(place_tags)
                # If it parsed successfully, it's already a JSON string
                review.place_tags = json.loads(place_tags)
            except json.JSONDecodeError:
                # If it's not valid JSON, check if it's already a Python list
                if isinstance(review.place_tags, list):
                    # Keep it as is
                    pass
                else:
                    # Set to empty list as fallback
                    review.place_tags = []
            
            review.place_photo_url = request.POST.get('place_photo_url', '')

            review.save()
            return redirect('review_detail', pk=review.id)
    else:
        form = ReviewForm(instance=review)
    
    # Serialize place_tags to JSON for the template
    place_tags_json = json.dumps(review.place_tags) if review.place_tags else '[]'
    
    return render(request, 'edit_review.html', {
        'form': form,
        'review': review,
        'place_tags_json': place_tags_json,
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def delete_review(request, pk):
    """Delete a review."""
    review = get_object_or_404(Review, pk=pk)
    if request.method == 'POST':
        review.delete()
        return redirect('reviews')
    
    return redirect('review_detail', pk=review.pk)

@require_GET
def place_search(request):
    """
    Proxy endpoint for Google Places API search (using the new Places API)
    """
    query = request.GET.get('query', '')
    if not query:
        return JsonResponse({'error': 'Query parameter is required'}, status=400)
    
    # Get API key from settings
    api_key = settings.GOOGLE_PLACES_API_KEY if hasattr(settings, 'GOOGLE_PLACES_API_KEY') else ''
    
    if not api_key:
        # For development, return mock data that includes the search query
        return JsonResponse({
            'results': [
                {
                    'place_id': 'mock_place_id_1',
                    'name': f"{query} Restaurant",
                    'formatted_address': f"123 Main St, San Francisco, CA 94105",
                    'vicinity': 'San Francisco',
                    'types': ['restaurant', 'food', 'point_of_interest', 'establishment'],
                    'price_level': 2,
                    'rating': 4.3,
                    'user_ratings_total': 253,
                    'photo_url': 'https://via.placeholder.com/150',
                    'website': 'https://example.com',
                    'phone_number': '+1 (555) 123-4567'
                },
                {
                    'place_id': 'mock_place_id_2',
                    'name': f"Another {query} Place",
                    'formatted_address': f"456 Market St, San Francisco, CA 94103",
                    'vicinity': 'San Francisco',
                    'types': ['cafe', 'bakery', 'food', 'point_of_interest', 'establishment'],
                    'price_level': 1,
                    'rating': 4.7,
                    'user_ratings_total': 128,
                    'photo_url': 'https://via.placeholder.com/150',
                    'website': 'https://example.com/cafe',
                    'phone_number': '+1 (555) 987-6543'
                }
            ]
        })
    
    # Try using the Places API with expanded field mask
    url = 'https://places.googleapis.com/v1/places:searchText'
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': api_key,
        'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.id,places.types,places.priceLevel,places.rating,places.userRatingCount,places.photos,places.primaryType,places.shortFormattedAddress,places.internationalPhoneNumber,places.websiteUri,places.primaryTypeDisplayName'
    }
    
    # Just use the textQuery parameter which is required
    payload = {
        'textQuery': f"{query} restaurant"  # Add "restaurant" to bias toward food places
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        
        # Transform the response to match the format expected by the frontend
        if 'places' in data:
            transformed_results = []
            for place in data['places']:
                # Get the first photo if available
                photo_url = None
                if place.get('photos') and len(place.get('photos', [])) > 0:
                    # If you want to fetch the actual photo, you'd need another API call
                    # For now, just note that a photo is available
                    photo_reference = place.get('photos', [])[0].get('name', '')
                    if photo_reference:
                        photo_url = f"Photo available (reference: {photo_reference})"
                
                result = {
                    'place_id': place.get('id', ''),
                    'name': place.get('displayName', {}).get('text', ''),
                    'formatted_address': place.get('formattedAddress', ''),
                    'short_address': place.get('shortFormattedAddress', ''),
                    'types': place.get('types', []),
                    'primary_type': place.get('primaryType', ''),
                    'primary_type_display': place.get('primaryTypeDisplayName', {}).get('text', ''),
                    'price_level': place.get('priceLevel', 0),
                    'rating': place.get('rating', 0),
                    'user_ratings_total': place.get('userRatingCount', 0),
                    'photo_reference': photo_reference if 'photo_reference' in locals() else None,
                    'photo_url': photo_url,
                    'website': place.get('websiteUri', ''),
                    'phone_number': place.get('internationalPhoneNumber', '')
                }
                transformed_results.append(result)
            
            return JsonResponse({'results': transformed_results})
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_GET
def place_photo(request):
    """
    Proxy endpoint for Google Places API photos
    """
    photo_reference = request.GET.get('reference', '')
    max_width = request.GET.get('maxwidth', 400)
    max_height = request.GET.get('maxheight', 400)

    if not photo_reference:
        return JsonResponse({'error': 'Photo reference parameter is required'}, status=400)

    # Get API key from settings
    api_key = settings.GOOGLE_PLACES_API_KEY if hasattr(settings, 'GOOGLE_PLACES_API_KEY') else ''

    if not api_key:
        return JsonResponse({'photo_url': 'https://via.placeholder.com/400x200?text=No+API+Key'})

    # Handle both formats of photo references
    if photo_reference.startswith('places/'):  # New Places API format
        parts = photo_reference.split('/')
        if len(parts) >= 4 and parts[2] == 'photos':
            photo_name = parts[3]
            url = f'https://places.googleapis.com/v1/places/{parts[1]}/photos/{photo_name}/media'
            query_params = []
            if max_width:
                query_params.append(f'max_width_px={int(max_width)}')
            if max_height:
                query_params.append(f'max_height_px={int(max_height)}')
            if not query_params:
                query_params.append('max_width_px=400')
            url = f"{url}?{'&'.join(query_params)}"
            headers = {'X-Goog-Api-Key': api_key}
            try:
                response = requests.get(url, headers=headers, allow_redirects=False)
                if response.status_code == 302:
                    photo_url = response.headers.get('Location')
                    return JsonResponse({'photo_url': photo_url})
                elif response.status_code == 200:
                    return JsonResponse({'photo_url': url})
                else:
                    return JsonResponse({'error': f'API returned status {response.status_code}'}, status=response.status_code)
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        else:
            return JsonResponse({'error': 'Invalid photo reference format'}, status=400)
    else:  # Legacy Places API format
        url = 'https://maps.googleapis.com/maps/api/place/photo'
        params = {
            'photoreference': photo_reference,
            'maxwidth': max_width,
            'maxheight': max_height,
            'key': api_key
        }
        try:
            response = requests.get(url, params=params, allow_redirects=False)
            if response.status_code == 302:
                photo_url = response.headers.get('Location')
                return JsonResponse({'photo_url': photo_url})
            else:
                return JsonResponse({'error': f'API returned status {response.status_code}'}, status=response.status_code)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)