from django.db import models
import os
import uuid
from datetime import datetime
from django.contrib.auth.models import User
from django.utils import timezone

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

# Referenced by migration 0017; keep even though the Review model is gone.
def review_image_upload_path(instance, filename):
    # Get the file extension
    ext = filename.split('.')[-1]
    # Generate a new filename with timestamp and random string
    new_filename = f"review_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
    return os.path.join('review_images', new_filename)

def ramsey_profile_pic_upload_path(instance, filename):
    # Get the file extension
    ext = filename.split('.')[-1]
    # Generate a new filename with timestamp and random string
    new_filename = f"ramsey_profile_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
    return os.path.join('ramsey_profile', new_filename)

def ramsey_vaccine_upload_path(instance, filename):
    # Get the file extension
    ext = filename.split('.')[-1]
    # Generate a new filename with timestamp and random string
    new_filename = f"ramsey_vaccine_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
    return os.path.join('ramsey_vaccines', new_filename)

def ramsey_diet_upload_path(instance, filename):
    # Get the file extension
    ext = filename.split('.')[-1]
    # Generate a new filename with timestamp and random string
    new_filename = f"ramsey_diet_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
    return os.path.join('ramsey_diet', new_filename)

def ramsey_boarding_upload_path(instance, filename):
    # Get the file extension
    ext = filename.split('.')[-1]
    # Generate a new filename with timestamp and random string
    new_filename = f"ramsey_boarding_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
    return os.path.join('ramsey_boarding', new_filename)

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
    title = models.CharField(max_length=200)
    description = models.TextField()  # Replaces original ingredients+instructions
    time_required = models.CharField(max_length=100)
    image = models.ImageField(upload_to=recipe_image_upload_path, blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipes')
    created_at = models.DateTimeField(auto_now_add=True)
    featured = models.BooleanField(default=False)  # New field to mark a recipe as featured

    def delete(self, *args, **kwargs):
        # Delete the image through its storage so this works on S3 as well as locally
        if self.image:
            self.image.delete(save=False)
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

class RamseyProfile(models.Model):
    """Ramsey's LinkedIn-style profile"""
    name = models.CharField(max_length=100, default="Ramsey")
    breed = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to=ramsey_profile_pic_upload_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}'s Profile"

    def delete(self, *args, **kwargs):
        # Delete profile picture if exists
        if self.profile_picture and os.path.isfile(self.profile_picture.path):
            os.remove(self.profile_picture.path)
        super().delete(*args, **kwargs)

class VaccineRecord(models.Model):
    """Vaccine records for Ramsey"""
    vaccine_name = models.CharField(max_length=200)
    date_administered = models.DateField()
    expiration_date = models.DateField(blank=True, null=True)
    veterinarian = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_administered']

    def __str__(self):
        return f"{self.vaccine_name} - {self.date_administered}"

class BoardingExperience(models.Model):
    """Boarding facilities Ramsey has stayed at"""
    facility_name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-check_in_date']

    def __str__(self):
        return f"{self.facility_name} - {self.check_in_date}"

class DietEntry(models.Model):
    """Food/diet information for Ramsey"""
    food_name = models.CharField(max_length=200)
    brand = models.CharField(max_length=200, blank=True)
    food_type = models.CharField(max_length=100, choices=[
        ('kibble', 'Kibble'),
        ('wet', 'Wet Food'),
        ('raw', 'Raw'),
        ('homemade', 'Homemade'),
        ('mixed', 'Mixed'),
        ('other', 'Other')
    ])
    date_started = models.DateField()
    date_ended = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_started']

    def __str__(self):
        return f"{self.food_name} - {self.brand}"

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


class StarholdResult(models.Model):
    RESULT_CHOICES = [
        ('win', 'Win'),
        ('loss', 'Loss'),
    ]
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('hard', 'Hard'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='starhold_results')
    result = models.CharField(max_length=4, choices=RESULT_CHOICES)
    difficulty = models.CharField(max_length=8, choices=DIFFICULTY_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.result} ({self.difficulty}) - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class Comment(models.Model):
    post = models.ForeignKey('BlogPost', on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} on {self.post.title}"

class VaccineDocument(models.Model):
    """General vaccine documents for Ramsey (not tied to specific entries)"""
    document = models.FileField(upload_to=ramsey_vaccine_upload_path)
    document_name = models.CharField(max_length=200)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.document_name
    
    def delete(self, *args, **kwargs):
        if self.document and os.path.isfile(self.document.path):
            os.remove(self.document.path)
        super().delete(*args, **kwargs)

class DietDocument(models.Model):
    """General diet documents for Ramsey (not tied to specific entries)"""
    document = models.FileField(upload_to=ramsey_diet_upload_path)
    document_name = models.CharField(max_length=200)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.document_name
    
    def delete(self, *args, **kwargs):
        if self.document and os.path.isfile(self.document.path):
            os.remove(self.document.path)
        super().delete(*args, **kwargs)

class BoardingDocument(models.Model):
    """General boarding documents for Ramsey (not tied to specific entries)"""
    document = models.FileField(upload_to=ramsey_boarding_upload_path)
    document_name = models.CharField(max_length=200)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.document_name
    
    def delete(self, *args, **kwargs):
        if self.document and os.path.isfile(self.document.path):
            os.remove(self.document.path)
        super().delete(*args, **kwargs)
