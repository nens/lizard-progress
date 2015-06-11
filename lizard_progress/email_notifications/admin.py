from django.contrib import admin

from .models import Notification
from .models import NotificationType
from .models import NotificationSubscription


class NotificationAdmin(admin.ModelAdmin):
    model = Notification
    list_display = ('created_on', 'emailed', 'emailed_on', 'notification_type',
                    'recipient', )
    ordering = ['created_on', ]
    list_filter = ['created_on', 'emailed_on', 'emailed', 'notification_type',
                   'recipient']


class NotificationTypeAdmin(admin.ModelAdmin):
    model = NotificationType


class NotificationSubscriptionAdmin(admin.ModelAdmin):
    model = NotificationSubscription
    list_display = ('notification_type', 'subscriber')
    list_filter = ['notification_type', 'subscriber_content_type',
                   'subscriber_object_id']


admin.site.register(Notification, NotificationAdmin)
admin.site.register(NotificationType, NotificationTypeAdmin)
admin.site.register(NotificationSubscription, NotificationSubscriptionAdmin)
