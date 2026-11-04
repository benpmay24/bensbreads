from django.contrib import admin

# Register your models here.
from .models import (
    BlogPost, Recipe, Comment, RamseyProfile, VaccineRecord,
    BoardingExperience, DietEntry, VaccineDocument, DietDocument, BoardingDocument,
    StarholdResult,
)

admin.site.register(BlogPost)
admin.site.register(Recipe)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'created_at', 'text_preview']
    list_filter = ['created_at', 'post']
    search_fields = ['user__username', 'post__title', 'text']
    readonly_fields = ['created_at']
    
    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
    text_preview.short_description = "Comment Preview"

@admin.register(RamseyProfile)
class RamseyProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'breed', 'date_of_birth', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Profile Information', {
            'fields': ('name', 'breed', 'date_of_birth', 'bio')
        }),
        ('Profile Picture', {
            'fields': ('profile_picture',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(VaccineRecord)
class VaccineRecordAdmin(admin.ModelAdmin):
    list_display = ['vaccine_name', 'date_administered', 'expiration_date', 'veterinarian']
    list_filter = ['date_administered', 'expiration_date']
    search_fields = ['vaccine_name', 'veterinarian']
    readonly_fields = ['created_at']
    ordering = ['-date_administered']

@admin.register(BoardingExperience)
class BoardingExperienceAdmin(admin.ModelAdmin):
    list_display = ['facility_name', 'check_in_date', 'check_out_date', 'city']
    list_filter = ['check_in_date', 'city']
    search_fields = ['facility_name', 'city']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-check_in_date']

@admin.register(DietEntry)
class DietEntryAdmin(admin.ModelAdmin):
    list_display = ['food_name', 'brand', 'food_type', 'date_started', 'is_current']
    list_filter = ['food_type', 'date_started', 'is_current']
    search_fields = ['food_name', 'brand']
    readonly_fields = ['created_at']
    ordering = ['-date_started']

@admin.register(VaccineDocument)
class VaccineDocumentAdmin(admin.ModelAdmin):
    list_display = ['document_name', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['document_name']
    readonly_fields = ['uploaded_at']
    ordering = ['-uploaded_at']

@admin.register(DietDocument)
class DietDocumentAdmin(admin.ModelAdmin):
    list_display = ['document_name', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['document_name']
    readonly_fields = ['uploaded_at']
    ordering = ['-uploaded_at']

@admin.register(BoardingDocument)
class BoardingDocumentAdmin(admin.ModelAdmin):
    list_display = ['document_name', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['document_name']
    readonly_fields = ['uploaded_at']
    ordering = ['-uploaded_at']

@admin.register(StarholdResult)
class StarholdResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'result', 'difficulty', 'timestamp']
    list_filter = ['result', 'difficulty', 'timestamp']
    search_fields = ['user__username']
    readonly_fields = ['timestamp']
