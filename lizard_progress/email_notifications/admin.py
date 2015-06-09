from django.contrib import admin

from .models import Notification
from .models import NotificationType
from .models import NotificationSubscription


class NotificationAdmin(admin.ModelAdmin):
    model = Notification


class NotificationTypeAdmin(admin.ModelAdmin):
    model = NotificationType


class NotificationSubscriptionAdmin(admin.ModelAdmin):
    model = NotificationSubscription


admin.site.register(Notification, NotificationAdmin)
admin.site.register(NotificationType, NotificationTypeAdmin)
admin.site.register(NotificationSubscription, NotificationSubscriptionAdmin)
