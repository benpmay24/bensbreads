import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Count, Q, F
import requests
from main.models import BlogPost, RamseyPhoto, Connect4Result, WordFindScore, StarholdResult, Comment, RamseyProfile, VaccineRecord, BoardingExperience, DietEntry, VaccineDocument, DietDocument, BoardingDocument
from .forms import BlogPostForm, RamseyPhotoForm, RamseyProfileForm, VaccineRecordForm, BoardingExperienceForm, DietEntryForm, VaccineDocumentForm, DietDocumentForm, BoardingDocumentForm
from .connect4.board import board
from .connect4.eval_cpu_moves import evalMoves
from .connect4.generate_default import generateDefault


def staff_or_superuser(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def home(request):
    return render(request, 'playground/home.html')


def games(request):
    return render(request, 'games/games.html')


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
    
    return render(request, 'blog/blog.html', {'posts': posts})


# Secrets page (only superusers)
def secrets(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Admin privileges required.')
    posts = BlogPost.objects.filter(private=True).order_by('-created_at')
    return render(request, 'blog/blog.html', {'posts': posts, 'is_secrets': True})


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
    return render(request, 'blog/add_blog_post.html', {'form': form})


@user_passes_test(lambda u: u.is_superuser)
def delete_blog_post(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)
    if request.method == 'POST':
        post.delete()
    return redirect('blog')


def ramsey_bio(request):
    return render(request, 'ramsey/ramsey_bio.html')


def ramsey_gallery(request):
    photos = RamseyPhoto.objects.all().order_by('-uploaded_at')  # adjust as needed
    return render(request, 'ramsey/ramsey_gallery.html', {'photos': photos})


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
    return render(request, 'ramsey/upload_ramsey_photo.html', {'form': form})


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def delete_ramsey_photo(request, pk):
    photo = get_object_or_404(RamseyPhoto, pk=pk)
    if request.method == 'POST':
        if photo.image:
            photo.image.delete(save=False)
        photo.delete()
    return redirect('ramsey_gallery')


# Ramsey Profile Views (Superuser Only)
@user_passes_test(lambda u: u.is_superuser)
def ramsey_profile(request):
    """View and edit Ramsey's profile"""
    profile = RamseyProfile.objects.first()
    if not profile:
        profile = RamseyProfile.objects.create(name="Ramsey")
    
    vaccines = VaccineRecord.objects.all()
    boarding_experiences = BoardingExperience.objects.all()
    diet_entries = DietEntry.objects.all()
    current_diet = DietEntry.objects.filter(is_current=True).first()
    
    vaccine_documents = VaccineDocument.objects.all()
    diet_documents = DietDocument.objects.all()
    boarding_documents = BoardingDocument.objects.all()
    
    return render(request, 'ramsey/ramsey_profile.html', {
        'profile': profile,
        'vaccines': vaccines,
        'boarding_experiences': boarding_experiences,
        'diet_entries': diet_entries,
        'current_diet': current_diet,
        'vaccine_documents': vaccine_documents,
        'diet_documents': diet_documents,
        'boarding_documents': boarding_documents,
    })


@user_passes_test(lambda u: u.is_superuser)
def edit_ramsey_profile(request):
    """Edit Ramsey's profile picture and bio"""
    profile = RamseyProfile.objects.first()
    if not profile:
        profile = RamseyProfile.objects.create(name="Ramsey")
    
    if request.method == 'POST':
        form = RamseyProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('ramsey_profile')
    else:
        form = RamseyProfileForm(instance=profile)
    
    return render(request, 'ramsey/edit_ramsey_profile.html', {'form': form, 'profile': profile})


@user_passes_test(lambda u: u.is_superuser)
def add_vaccine_record(request):
    """Add a new vaccine record"""
    if request.method == 'POST':
        form = VaccineRecordForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('ramsey_profile')
    else:
        form = VaccineRecordForm()
    
    return render(request, 'ramsey/add_vaccine_record.html', {'form': form})


@user_passes_test(lambda u: u.is_superuser)
def edit_vaccine_record(request, pk):
    """Edit a vaccine record"""
    vaccine = get_object_or_404(VaccineRecord, pk=pk)
    
    if request.method == 'POST':
        form = VaccineRecordForm(request.POST, request.FILES, instance=vaccine)
        if form.is_valid():
            form.save()
            return redirect('ramsey_profile')
    else:
        form = VaccineRecordForm(instance=vaccine)
    
    return render(request, 'ramsey/edit_vaccine_record.html', {'form': form, 'vaccine': vaccine})


@user_passes_test(lambda u: u.is_superuser)
def add_boarding_experience(request):
    """Add a new boarding experience"""
    if request.method == 'POST':
        form = BoardingExperienceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('ramsey_profile')
    else:
        form = BoardingExperienceForm()
    
    return render(request, 'ramsey/add_boarding_experience.html', {'form': form})


@user_passes_test(lambda u: u.is_superuser)
def edit_boarding_experience(request, pk):
    """Edit a boarding experience"""
    experience = get_object_or_404(BoardingExperience, pk=pk)
    
    if request.method == 'POST':
        form = BoardingExperienceForm(request.POST, instance=experience)
        if form.is_valid():
            form.save()
            return redirect('ramsey_profile')
    else:
        form = BoardingExperienceForm(instance=experience)
    
    return render(request, 'ramsey/edit_boarding_experience.html', {'form': form, 'experience': experience})


@user_passes_test(lambda u: u.is_superuser)
def add_diet_entry(request):
    """Add a new diet entry"""
    if request.method == 'POST':
        form = DietEntryForm(request.POST)
        if form.is_valid():
            diet_entry = form.save(commit=False)
            # If this is marked as current, unmark all others
            if diet_entry.is_current:
                DietEntry.objects.filter(is_current=True).update(is_current=False)
            diet_entry.save()
            return redirect('ramsey_profile')
    else:
        form = DietEntryForm()
    
    return render(request, 'ramsey/add_diet_entry.html', {'form': form})


@user_passes_test(lambda u: u.is_superuser)
def edit_diet_entry(request, pk):
    """Edit a diet entry"""
    diet_entry = get_object_or_404(DietEntry, pk=pk)
    
    if request.method == 'POST':
        form = DietEntryForm(request.POST, instance=diet_entry)
        if form.is_valid():
            updated_entry = form.save(commit=False)
            # If this is marked as current, unmark all others
            if updated_entry.is_current:
                DietEntry.objects.filter(is_current=True).exclude(pk=pk).update(is_current=False)
            updated_entry.save()
            return redirect('ramsey_profile')
    else:
        form = DietEntryForm(instance=diet_entry)
    
    return render(request, 'ramsey/edit_diet_entry.html', {'form': form, 'diet_entry': diet_entry})


@user_passes_test(lambda u: u.is_superuser)
def delete_vaccine_record(request, pk):
    """Delete a vaccine record"""
    vaccine = get_object_or_404(VaccineRecord, pk=pk)
    if request.method == 'POST':
        if vaccine.document:
            vaccine.document.delete(save=False)
        vaccine.delete()
    return redirect('ramsey_profile')


@user_passes_test(lambda u: u.is_superuser)
def delete_boarding_experience(request, pk):
    """Delete a boarding experience"""
    experience = get_object_or_404(BoardingExperience, pk=pk)
    if request.method == 'POST':
        experience.delete()
    return redirect('ramsey_profile')


@user_passes_test(lambda u: u.is_superuser)
def delete_diet_entry(request, pk):
    """Delete a diet entry"""
    diet_entry = get_object_or_404(DietEntry, pk=pk)
    if request.method == 'POST':
        diet_entry.delete()
    return redirect('ramsey_profile')


@user_passes_test(lambda u: u.is_superuser)
def upload_vaccine_document(request):
    """Upload a vaccine document"""
    if request.method == 'POST':
        form = VaccineDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('ramsey_profile')
    else:
        form = VaccineDocumentForm()
    
    return render(request, 'ramsey/upload_vaccine_document.html', {'form': form})


@user_passes_test(lambda u: u.is_superuser)
def delete_vaccine_document(request, pk):
    """Delete a vaccine document"""
    doc = get_object_or_404(VaccineDocument, pk=pk)
    if request.method == 'POST':
        doc.delete()
    return redirect('ramsey_profile')


@user_passes_test(lambda u: u.is_superuser)
def upload_diet_document(request):
    """Upload a diet document"""
    if request.method == 'POST':
        form = DietDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('ramsey_profile')
    else:
        form = DietDocumentForm()
    
    return render(request, 'ramsey/upload_diet_document.html', {'form': form})


@user_passes_test(lambda u: u.is_superuser)
def delete_diet_document(request, pk):
    """Delete a diet document"""
    doc = get_object_or_404(DietDocument, pk=pk)
    if request.method == 'POST':
        doc.delete()
    return redirect('ramsey_profile')


@user_passes_test(lambda u: u.is_superuser)
def upload_boarding_document(request):
    """Upload a boarding document"""
    if request.method == 'POST':
        form = BoardingDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('ramsey_profile')
    else:
        form = BoardingDocumentForm()
    
    return render(request, 'ramsey/upload_boarding_document.html', {'form': form})


@user_passes_test(lambda u: u.is_superuser)
def delete_boarding_document(request, pk):
    """Delete a boarding document"""
    doc = get_object_or_404(BoardingDocument, pk=pk)
    if request.method == 'POST':
        doc.delete()
    return redirect('ramsey_profile')


@login_required
def download_document(request, doc_type, doc_id):
    """Download a document by type"""
    if not request.user.is_superuser:
        return HttpResponseForbidden('Admin privileges required.')
    
    if doc_type == 'vaccine':
        doc = get_object_or_404(VaccineDocument, pk=doc_id)
    elif doc_type == 'diet':
        doc = get_object_or_404(DietDocument, pk=doc_id)
    elif doc_type == 'boarding':
        doc = get_object_or_404(BoardingDocument, pk=doc_id)
    else:
        return HttpResponse('Invalid document type', status=400)
    
    if doc.document:
        response = HttpResponse(doc.document.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{doc.document_name}"'
        return response
    
    return HttpResponse('Document not found', status=404)


def connect4 (request):
    return render(request,"games/connect4.html")


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


@login_required
def starhold(request):
    """Starhold hub: mode select + leaderboards. Requires login."""
    return render(request, 'games/starhold_hub.html')


@login_required
def starhold_play(request):
    mode = request.GET.get('mode', 'mp')
    difficulty = request.GET.get('difficulty', 'easy')
    if mode not in ('sp', 'mp'):
        mode = 'mp'
    if difficulty not in ('easy', 'hard'):
        difficulty = 'easy'
    return render(request, 'games/starhold.html', {
        'mode': mode,
        'difficulty': difficulty,
    })


@login_required
@require_POST
def save_starhold_result(request):
    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'invalid json'}, status=400)

    result = data.get('result')
    difficulty = data.get('difficulty')
    if result not in ('win', 'loss') or difficulty not in ('easy', 'hard'):
        return JsonResponse({'status': 'invalid payload'}, status=400)

    StarholdResult.objects.create(
        user=request.user,
        result=result,
        difficulty=difficulty,
    )
    return JsonResponse({'status': 'success'})


@login_required
def starhold_leaderboard(request):
    difficulty = request.GET.get('difficulty', 'easy')
    if difficulty not in ('easy', 'hard'):
        difficulty = 'easy'

    from django.db.models import Count, F

    rows = User.objects.annotate(
        wins=Count(
            'starhold_results',
            filter=Q(starhold_results__result='win', starhold_results__difficulty=difficulty),
        ),
        losses=Count(
            'starhold_results',
            filter=Q(starhold_results__result='loss', starhold_results__difficulty=difficulty),
        ),
    ).annotate(
        total_games=F('wins') + F('losses'),
    ).filter(
        total_games__gt=0,
    ).values('username', 'wins', 'losses', 'total_games')

    leaderboard = [
        {
            **entry,
            'win_rate': round((entry['wins'] / entry['total_games']) * 100, 1) if entry['total_games'] else 0,
        }
        for entry in rows
    ]
    leaderboard.sort(key=lambda x: (x['win_rate'], x['wins']), reverse=True)
    return JsonResponse({'difficulty': difficulty, 'leaderboard': leaderboard})


def word_find(request):
    return render(request, 'games/word_find.html')


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
        if score is not none:
            WordFindScore.objects.create(user=request.user, score=score)
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'invalid score'}, status=400)
