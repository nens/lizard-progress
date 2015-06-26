from django.dispatch import Signal

notify = Signal(
    providing_args=[
        'notification_type',
        'recipient',
        'actor',
        'action_object',
        'target',
        'extra',
    ]
)
