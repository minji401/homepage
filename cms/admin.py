from django.contrib import admin

from .models import Application, Banner, Board, Comment, Popup, Post, SearchTerm, SiteContent, VisitLog


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "board", "is_pinned", "is_hidden", "created_at")


admin.site.register(Comment)
admin.site.register(Application)
admin.site.register(SiteContent)
admin.site.register(Popup)
admin.site.register(Banner)
admin.site.register(SearchTerm)
admin.site.register(VisitLog)
