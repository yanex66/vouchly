import requests
import os
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from core.models import Category, Item, Review

class Command(BaseCommand):
    help = 'Downloads real images from the web and creates products with reviews'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting Real Data Fetcher...")

        # 1. Setup a "Reviewer" User
        user, _ = User.objects.get_or_create(username='VerifiedBuyer')
        if not user.password:
            user.set_password('pass123')
            user.save()

        # 2. Real Product Data (Name, Category, Description, Image URL)
        # These URLs are from Unsplash (Public Domain)
        products = [
            {
                "name": "Sony WH-1000XM5 Headphones",
                "category": "Electronics",
                "desc": "Industry-leading noise cancellation with 30-hour battery life and ultra-comfortable fit.",
                "image_url": "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?q=80&w=1000&auto=format&fit=crop",
                "reviews": [
                    (5, "Silence is golden! Best headphones for travel."),
                    (4, "Great sound, but the case is a bit bulky."),
                ]
            },
            {
                "name": "Nike Air Zoom Pegasus",
                "category": "Fashion",
                "desc": "The workhorse with wings. Perfect for daily runs with responsive foam cushioning.",
                "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=1000&auto=format&fit=crop",
                "reviews": [
                    (5, "Most comfortable running shoes I've ever owned."),
                    (5, "Love the color and the bounce!"),
                ]
            },
            {
                "name": "Apple Watch Ultra 2",
                "category": "Electronics",
                "desc": "The most rugged and capable Apple Watch. Designed for endurance athletes and outdoor adventurers.",
                "image_url": "https://images.unsplash.com/photo-1579586337278-3befd40fd17a?q=80&w=1000&auto=format&fit=crop",
                "reviews": [
                    (5, "Battery life lasts me 3 days easily!"),
                    (4, "Expensive, but worth it for the screen brightness."),
                ]
            },
            {
                "name": "Canon EOS R5 Camera",
                "category": "Electronics",
                "desc": "Professional mirrorless camera with 8K video recording and 45MP image sensor.",
                "image_url": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?q=80&w=1000&auto=format&fit=crop",
                "reviews": [
                    (5, "The autofocus is like magic. Incredible detail."),
                ]
            },
            {
                "name": "Modern Leather Sofa",
                "category": "Home",
                "desc": "Mid-century modern design with genuine Italian leather and oak legs.",
                "image_url": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?q=80&w=1000&auto=format&fit=crop",
                "reviews": [
                    (5, "Looks exactly like the pictures. Very firm and supportive."),
                    (3, "Delivery took longer than expected."),
                ]
            }
        ]

        # 3. Loop through and Download
        for p in products:
            self.stdout.write(f"Processing: {p['name']}...")
            
            # Get Category
            cat, _ = Category.objects.get_or_create(name=p['category'])

            # Check if item exists
            if Item.objects.filter(name=p['name']).exists():
                self.stdout.write(f" - {p['name']} already exists. Skipping.")
                continue

            # Create Item
            item = Item(
                name=p['name'],
                category=cat,
                description=p['desc'],
                owner=user,
                is_featured=True  # Feature all of them so they show on Home
            )

            # DOWNLOAD IMAGE
            try:
                response = requests.get(p['image_url'])
                if response.status_code == 200:
                    # Create a filename (e.g., "sony-headphones.jpg")
                    filename = p['name'].lower().replace(" ", "-") + ".jpg"
                    # Save content to the ImageField
                    item.image.save(filename, ContentFile(response.content), save=False)
                    self.stdout.write(self.style.SUCCESS(f" - Image downloaded!"))
                else:
                    self.stdout.write(self.style.ERROR(f" - Failed to download image."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f" - Error downloading image: {e}"))

            item.save()

            # Add Reviews
            for rating, content in p['reviews']:
                Review.objects.create(
                    item=item,
                    author=user,
                    rating=rating,
                    title=f"Review for {p['name']}",
                    content=content
                )
        
        self.stdout.write(self.style.SUCCESS("Done! Real images and data added."))