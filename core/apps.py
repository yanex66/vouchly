# core/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_save

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        print("✅ CORE CONFIG LOADED: Connecting Signals...")
        from . import signals
        from .models import Item
        
        # Manually connect the signal to be 100% sure
        post_save.connect(signals.notify_users_of_new_product, sender=Item)