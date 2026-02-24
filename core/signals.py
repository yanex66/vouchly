# core/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Item

# Add weak=False here to prevent the signal from being ignored
@receiver(post_save, sender=Item, weak=False)
def notify_users_of_new_product(sender, instance, created, **kwargs):
    print(f"DEBUG: Signal successfully fired for: {instance.name}") # Keep this!
    
    if created:
        print("DEBUG: New product detected. Sending alerts...")
        # ... rest of your email and Termii logic ...