from django.core.management.base import BaseCommand
from core.models import Item, Category, Review, Profile
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Deletes all dummy data (Items, Reviews, Categories)'

    def handle(self, *args, **kwargs):
        self.stdout.write("Cleaning database...")

        # 1. Delete all Reviews
        Review.objects.all().delete()
        self.stdout.write(" - Deleted all Reviews")

        # 2. Delete all Items
        Item.objects.all().delete()
        self.stdout.write(" - Deleted all Items")

        # 3. Delete all Categories
        Category.objects.all().delete()
        self.stdout.write(" - Deleted all Categories")
        
        # 4. Delete dummy users (optional, keeps superusers)
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(" - Deleted dummy users")

        self.stdout.write(self.style.SUCCESS('Database is now clean!'))