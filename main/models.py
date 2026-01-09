from django.db import models
import os
import uuid
from datetime import datetime
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg

def ramsey_photo_upload_path(instance, filename):
    # Get the file extension
    ext = filename.split('.')[-1]
    # Generate a new filename with timestamp and random string
    new_filename = f"ramsey_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
    return os.path.join('ramsey_photos', new_filename)

def recipe_image_upload_path(instance, filename):
    # Get the file extension
    ext = filename.split('.')[-1]
    # Generate a new filename with timestamp and random string
    new_filename = f"recipe_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
    return os.path.join('recipe_images', new_filename)

def blog_image_upload_path(instance, filename):
    # Get the file extension
    ext = filename.split('.')[-1]
    # Generate a new filename with timestamp and random string
    new_filename = f"blog_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
    return os.path.join('blog_images', new_filename)

def review_image_upload_path(instance, filename):
    # Get the file extension
    ext = filename.split('.')[-1]
    # Generate a new filename with timestamp and random string
    new_filename = f"review_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
    return os.path.join('review_images', new_filename)

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to=blog_image_upload_path, blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, default=7)
    created_at = models.DateTimeField(auto_now_add=True)
    private = models.BooleanField(default=False)  # New field for private posts

    def __str__(self):
        return self.title

class Recipe(models.Model):
    CATEGORY_CHOICES = [
        ('bread', 'Bread'),
        ('other', 'Other'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()  # Replaces original ingredients+instructions
    time_required = models.CharField(max_length=100)
    image = models.ImageField(upload_to=recipe_image_upload_path, blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipes')
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='other')
    created_at = models.DateTimeField(auto_now_add=True)
    featured = models.BooleanField(default=False)  # New field to mark a recipe as featured

    def delete(self, *args, **kwargs):
        # Delete image if exists
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.title

class Ingredient(models.Model):
    recipe = models.ForeignKey(Recipe, related_name='ingredients', on_delete=models.CASCADE)
    quantity = models.CharField(max_length=100)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.quantity} {self.name}"

class Instruction(models.Model):
    recipe = models.ForeignKey(Recipe, related_name='instructions', on_delete=models.CASCADE)
    step_number = models.PositiveIntegerField()
    step_text = models.TextField()

    class Meta:
        ordering = ['step_number']

    def __str__(self):
        return f"Step {self.step_number} for {self.recipe.title}"

class RamseyPhoto(models.Model):
    title = models.CharField(max_length=200, default="Untitled Photo")
    image = models.ImageField(upload_to=ramsey_photo_upload_path)
    caption = models.TextField(blank=True)
    date_taken = models.DateField(default=timezone.now)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-date_taken', '-uploaded_at']

class Connect4Result(models.Model):
    RESULT_CHOICES = [
        ('win', 'Win'),
        ('loss', 'Loss'),
        ('tie', 'Tie'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    result = models.CharField(max_length=4, choices=RESULT_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.result} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

class WordFindScore(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.score} points"

class Comment(models.Model):
    post = models.ForeignKey('BlogPost', on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} on {self.post.title}"

class Review(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]
    
    place_name = models.CharField(max_length=200)
    place_id = models.CharField(max_length=255, blank=True, null=True)  # Store Google Places ID
    location = models.CharField(max_length=200, blank=True, null=True)  # Keep for backward compatibility
    street_address = models.CharField(max_length=200, blank=True, null=True)  # Street address
    city = models.CharField(max_length=100, blank=True, null=True)  # City name
    state = models.CharField(max_length=50, blank=True, null=True)  # State/province
    zip_code = models.CharField(max_length=20, blank=True, null=True)  # Postal/ZIP code
    content = models.TextField()
    image = models.ImageField(upload_to=review_image_upload_path, blank=True, null=True)
    
    food_rating = models.IntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    ambience_rating = models.IntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    value_rating = models.IntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    service_rating = models.IntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    overall_rating = models.IntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    
    category = models.CharField(max_length=100)  # Changed from ForeignKey to CharField
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    place_website = models.URLField(max_length=500, blank=True, null=True)
    place_phone = models.CharField(max_length=50, blank=True, null=True)
    place_tags = models.JSONField(blank=True, null=True)  # Store tags as a JSON array
    place_photo_url = models.URLField(max_length=500, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.place_name} by {self.author.username}"
    
    def delete(self, *args, **kwargs):
        # Delete image if it exists
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        super().delete(*args, **kwargs)

class DailyUpdate(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_updates')
    entry = models.TextField()
    date = models.DateField(unique=True)  # Only one entry per day
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Daily Update - {self.date}"