from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth import views as auth_views
from django.conf import settings
from .models import Recipe, Ingredient, Instruction
from .forms import RecipeForm, CustomUserCreationForm, IngredientForm, InstructionForm
from django.db import transaction
from django.http import HttpResponse
from django.forms import inlineformset_factory
from django.utils.http import url_has_allowed_host_and_scheme, urlencode
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def safe_next_url(request, url):
    """Return `url` if it's safe to redirect to after login/logout, else ''.

    Allows the current host, both configured site URLs, and any host under the
    shared cookie domain (e.g. *.bensbreads.com) so the playground always gets
    users back regardless of the exact subdomain or www/apex form in use.
    """
    if not url:
        return ''
    allowed = {request.get_host()}
    for site_url in (settings.MAIN_SITE_URL, settings.PLAYGROUND_SITE_URL):
        allowed.add(urlparse(site_url).netloc)
    if url_has_allowed_host_and_scheme(url, allowed_hosts=allowed):
        return url
    parsed = urlparse(url)
    domain = (settings.SESSION_COOKIE_DOMAIN or '').lstrip('.')
    host = parsed.hostname or ''
    if parsed.scheme in ('http', 'https') and domain and (host == domain or host.endswith('.' + domain)):
        return url
    logger.warning('Rejected post-login redirect to %r (allowed: %s, cookie domain: %r)', url, sorted(allowed), domain)
    return ''


class CrossSiteRedirectMixin:
    """Let login/logout send users back to the playground site."""

    def get_redirect_url(self):
        redirect_to = self.request.POST.get(
            self.redirect_field_name, self.request.GET.get(self.redirect_field_name)
        )
        return safe_next_url(self.request, redirect_to)


class LoginView(CrossSiteRedirectMixin, auth_views.LoginView):
    pass


class LogoutView(CrossSiteRedirectMixin, auth_views.LogoutView):
    pass


def staff_or_superuser(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def home(request):
    # Get all recipes that are marked as featured
    featured_recipes = Recipe.objects.filter(featured=True)
    return render(request, 'index.html', {'featured_recipes': featured_recipes})


def signup(request):
    # Carry ?next= through signup so new users still end up back where they started.
    next_url = safe_next_url(request, request.POST.get('next', request.GET.get('next')))
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()
            login_url = reverse('login')
            if next_url:
                login_url += '?' + urlencode({'next': next_url})
            return redirect(login_url)
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/signup.html', {'form': form, 'next': next_url})


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
    return render(request, "admin/manage_users.html", {'users': users})


def recipes(request):
    recipes = Recipe.objects.all().order_by('-created_at')
    bread_recipes = recipes.filter(category='bread')
    other_recipes = recipes.filter(category='other')
    return render(request, 'recipes/recipes.html', {
        'recipes': recipes,
        'bread_recipes': bread_recipes,
        'other_recipes': other_recipes
    })


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

    return render(request, 'recipes/add_recipe.html', {
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


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def toggle_featured_recipe(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    recipe.featured = not recipe.featured  # Toggle the featured status
    recipe.save()
    return redirect('recipes')  # Redirect back to the recipes page after toggling


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

    return render(request, 'recipes/edit_recipe.html', {
        'form': form,
        'recipe': recipe,
        'ingredient_formset': ingredient_formset,
        'instruction_formset': instruction_formset,
    })


def recipe_detail(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    return render(request, 'recipes/recipe_detail.html', {'recipe': recipe})
