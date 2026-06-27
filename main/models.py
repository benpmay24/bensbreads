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


class PuppyMillFacility(models.Model):
    """USDA-licensed dog breeding/dealing facility tracked on Dog Watch."""
    license_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=300)
    dba_name = models.CharField(max_length=300, blank=True)
    license_type = models.CharField(max_length=100, blank=True)
    street_address = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    coordinates_geocoded = models.BooleanField(default=False)
    owners = models.JSONField(default=list, blank=True)
    suppliers = models.JSONField(default=list, blank=True)
    dog_breeds = models.JSONField(default=list, blank=True)
    news_articles = models.JSONField(default=list, blank=True)
    violation_count = models.PositiveIntegerField(default=0)
    direct_violations = models.PositiveIntegerField(default=0)
    critical_violations = models.PositiveIntegerField(default=0)
    inspection_reports = models.JSONField(default=list, blank=True)
    processed_report_urls = models.JSONField(default=list, blank=True)
    usda_profile_url = models.URLField(blank=True)
    source_notes = models.TextField(blank=True)
    is_dog_facility = models.BooleanField(default=True)
    license_expiration = models.DateField(null=True, blank=True)
    last_scraped_at = models.DateTimeField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['state', 'city', 'name']
        verbose_name_plural = 'puppy mill facilities'

    def __str__(self):
        return f"{self.name} ({self.license_number})"

    @property
    def full_address(self):
        parts = [self.street_address, self.city, self.state, self.zip_code]
        return ', '.join(p for p in parts if p)

    @property
    def has_coordinates(self):
        return self.latitude is not None and self.longitude is not None


class FacilityInspectionReport(models.Model):
    """A single USDA APHIS inspection report for a facility."""
    facility = models.ForeignKey(
        PuppyMillFacility,
        on_delete=models.CASCADE,
        related_name='reports',
    )
    inspection_date = models.DateField(null=True, blank=True)
    report_url = models.URLField(max_length=500)
    inspection_type = models.CharField(max_length=80, blank=True)
    direct_count = models.PositiveIntegerField(default=0)
    critical_count = models.PositiveIntegerField(default=0)
    non_critical_count = models.PositiveIntegerField(default=0)
    teachable_count = models.PositiveIntegerField(default=0)
    violations_parsed = models.BooleanField(default=False)
    parse_attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-inspection_date', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['facility', 'report_url'],
                name='unique_facility_report_url',
            ),
        ]

    def __str__(self):
        return f'{self.facility.license_number} — {self.inspection_date or "unknown date"}'

    @property
    def total_violations(self):
        return self.direct_count + self.critical_count + self.non_critical_count


class FacilityViolation(models.Model):
    """An individual noncompliance item cited on an inspection report."""

    class Category(models.TextChoices):
        DIRECT = 'direct', 'Direct'
        CRITICAL = 'critical', 'Critical'
        NON_CRITICAL = 'non_critical', 'Non-critical'
        TEACHABLE = 'teachable', 'Teachable moment'

    facility = models.ForeignKey(
        PuppyMillFacility,
        on_delete=models.CASCADE,
        related_name='violations',
    )
    report = models.ForeignKey(
        FacilityInspectionReport,
        on_delete=models.CASCADE,
        related_name='violations',
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    section = models.CharField(max_length=50)
    title = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    is_repeat = models.BooleanField(default=False)
    inspection_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-inspection_date', 'section']
        indexes = [
            models.Index(fields=['facility', 'category']),
            models.Index(fields=['-inspection_date']),
        ]

    def __str__(self):
        return f'{self.section} ({self.get_category_display()}) — {self.facility.name}'


class DogWatchSyncState(models.Model):
    """Singleton tracking Dog Watch background sync state."""
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    is_running = models.BooleanField(default=False)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_usda_import_at = models.DateTimeField(null=True, blank=True)
    last_summary = models.JSONField(default=dict, blank=True)
    progress = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Dog Watch sync state'

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f'Dog Watch sync (running={self.is_running})'


class ClashCard(models.Model):
    """Clash Royale card catalog (synced from the Royale API)."""
    card_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100)
    elixir = models.PositiveSmallIntegerField(default=0)
    rarity = models.CharField(max_length=30, blank=True)
    card_type = models.CharField(max_length=30, blank=True)
    max_level = models.PositiveSmallIntegerField(default=0)
    max_evolution_level = models.PositiveSmallIntegerField(default=0)
    icon_url = models.URLField(max_length=500, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['elixir', 'name']

    def __str__(self):
        return self.name


class ClashPlayer(models.Model):
    """A player discovered while collecting ranked battle logs."""
    tag = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100, blank=True)
    tier = models.PositiveSmallIntegerField(
        default=0,
        help_text='Path of Legends league number (1–7), 0 if unknown',
    )
    last_battle_fetch_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name or self.tag


class ClashBattle(models.Model):
    """A single Path of Legends ranked battle."""
    battle_uid = models.CharField(max_length=80, unique=True)
    battle_time = models.DateTimeField()
    tier = models.PositiveSmallIntegerField(help_text='Path of Legends league number (1–7)')
    player_tag = models.CharField(max_length=20, db_index=True)
    opponent_tag = models.CharField(max_length=20, blank=True, db_index=True)
    player_won = models.BooleanField()
    player_cards = models.JSONField(help_text='Sorted list of 8 card IDs (player perspective)')
    opponent_cards = models.JSONField(help_text='Sorted list of 8 card IDs')
    player_crowns = models.PositiveSmallIntegerField(default=0)
    opponent_crowns = models.PositiveSmallIntegerField(default=0)
    arena_id = models.PositiveIntegerField(null=True, blank=True)
    game_mode = models.CharField(max_length=50, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-battle_time']
        indexes = [
            models.Index(fields=['tier', '-battle_time']),
            models.Index(fields=['player_tag', '-battle_time']),
            models.Index(fields=['opponent_tag', '-battle_time']),
        ]

    def __str__(self):
        return f'{self.player_tag} vs {self.opponent_tag} @ {self.battle_time:%Y-%m-%d}'


class ClashCenterSyncState(models.Model):
    """Singleton tracking Clash Center background sync state."""
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    is_running = models.BooleanField(default=False)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_cards_sync_at = models.DateTimeField(null=True, blank=True)
    last_summary = models.JSONField(default=dict, blank=True)
    progress = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Clash Center sync state'

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f'Clash Center sync (running={self.is_running})'