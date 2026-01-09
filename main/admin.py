from django.contrib import admin

# Register your models here.
from .models import BlogPost, Recipe, Comment, Review, DailyUpdate

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

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['place_name', 'category', 'author', 'created_at', 'overall_rating']
    list_filter = ['category', 'created_at', 'author']
    search_fields = ['place_name', 'content']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(DailyUpdate)
class DailyUpdateAdmin(admin.ModelAdmin):
    list_display = ['date', 'author', 'created_at', 'entry_preview']
    list_filter = ['date', 'created_at', 'author']
    search_fields = ['entry', 'author__username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-date']
    
    def entry_preview(self, obj):
        return obj.entry[:50] + "..." if len(obj.entry) > 50 else obj.entry
    entry_preview.short_description = "Entry Preview"