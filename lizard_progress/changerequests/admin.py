from django.contrib import admin

from . import models


class CommentInline(admin.StackedInline):
    model = models.RequestComment


class RequestAdmin(admin.ModelAdmin):
    model = models.Request
    inlines = [CommentInline]


admin.site.register(models.Request, RequestAdmin)
