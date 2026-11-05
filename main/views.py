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
    return render(request, 'recipes/recipes.html', {'recipes': recipes})


IngredientFormSet = inlineformset_factory(
    Recipe, Ingredient, form=IngredientForm, extra=0, can_delete=True,
)
# can_order: the page writes each step's on-screen position into ORDER, so steps can be
# reordered and are always renumbered 1..n from what the user sees.
InstructionFormSet = inlineformset_factory(
    Recipe, Instruction, form=InstructionForm, extra=0, can_delete=True, can_order=True,
)


def _recipe_form_view(request, recipe=None):
    """Shared add/edit flow for a recipe with its ingredients and steps."""
    is_edit = recipe is not None
    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES, instance=recipe)
        ingredient_formset = IngredientFormSet(request.POST, instance=recipe, prefix='ingredients')
        instruction_formset = InstructionFormSet(request.POST, instance=recipe, prefix='instructions')

        if form.is_valid() and ingredient_formset.is_valid() and instruction_formset.is_valid():
            with transaction.atomic():
                recipe = form.save(commit=False)
                if not is_edit:
                    recipe.author = request.user
                recipe.featured = 'featured' in request.POST
                recipe.save()

                ingredient_formset.instance = recipe
                ingredient_formset.save()

                for step_form in instruction_formset.deleted_forms:
                    if step_form.instance.pk:
                        step_form.instance.delete()
                for number, step_form in enumerate(instruction_formset.ordered_forms, start=1):
                    step = step_form.save(commit=False)
                    step.recipe = recipe
                    step.step_number = number
                    step.save()

            return redirect('recipe_detail', pk=recipe.pk)
    else:
        form = RecipeForm(instance=recipe)
        ingredient_formset = IngredientFormSet(instance=recipe, prefix='ingredients')
        instruction_formset = InstructionFormSet(instance=recipe, prefix='instructions')

    return render(request, 'recipes/recipe_form.html', {
        'form': form,
        'recipe': recipe,
        'is_edit': is_edit,
        'featured': ('featured' in request.POST) if request.method == 'POST' else bool(recipe and recipe.featured),
        'ingredient_formset': ingredient_formset,
        'instruction_formset': instruction_formset,
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def add_recipe(request):
    return _recipe_form_view(request)


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
    return _recipe_form_view(request, get_object_or_404(Recipe, pk=pk))


def recipe_detail(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    return render(request, 'recipes/recipe_detail.html', {'recipe': recipe})
