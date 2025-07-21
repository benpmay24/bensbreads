from django.contrib import admin

# Register your models here.
from .models import BlogPost, Recipe, Comment

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