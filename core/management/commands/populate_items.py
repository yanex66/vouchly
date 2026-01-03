import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Category, Item, Review

class Command(BaseCommand):
    help = 'Populates the database with dummy items and reviews'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting item population...")

        # 1. Ensure we have a user to be the "author"
        user, created = User.objects.get_or_create(username='ReviewBot', email='bot@example.com')
        if created:
            user.set_password('password123')
            user.save()
            self.stdout.write("Created dummy user 'ReviewBot'")

        # 2. Define our Data: (Category Name, Item Name, Description)
        items_data = [
            # Airlines
            ('Airlines', 'Emirates Airlines', 'World-class service with excellent in-flight entertainment and comfortable seating.'),
            ('Airlines', 'Delta Air Lines', 'Reliable domestic and international flights with great skymiles rewards.'),
            ('Airlines', 'British Airways', 'The flag carrier airline of the United Kingdom, offering premium service.'),
            
            # Electronics
            ('Smartphones', 'iPhone 15 Pro Max', 'Titanium design, A17 Pro chip, and the most powerful iPhone camera system ever.'),
            ('Laptops', 'MacBook Pro M3', 'Mind-blowing performance with the M3 Max chip and up to 22 hours of battery life.'),
            ('Headphones', 'Sony WH-1000XM5', 'Industry-leading noise canceling headphones with crystal clear hands-free calling.'),
            
            # Automotive
            ('Electric Vehicles', 'Tesla Model S Plaid', 'The quickest accelerating car in production today. 0-60 mph in 1.99s.'),
            
            # Fashion
            ('Shoes', 'Nike Air Jordan 1', 'The classic sneaker that started it all. Iconic style and comfort.'),
            
            # Apps
            ('Music Streaming', 'Spotify Premium', 'Ad-free music listening, play any song, and offline playback.'),
        ]

        # 3. Create Items and Fake Reviews
        for cat_name, item_name, desc in items_data:
            # Find the category (case-insensitive search)
            try:
                category = Category.objects.get(name__iexact=cat_name)
            except Category.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Skipped {item_name}: Category '{cat_name}' not found."))
                continue

            # Create the Item
            item, created = Item.objects.get_or_create(
                name=item_name,
                defaults={
                    'category': category,
                    'description': desc,
                    'owner': user,
                    'is_featured': random.choice([True, False]) # Randomly feature some
                }
            )

            if created:
                self.stdout.write(f"Added Item: {item_name}")
                
                # Add 3-5 random reviews for this item
                for i in range(random.randint(3, 5)):
                    rating = random.choice([3, 4, 5]) # Mostly good ratings
                    Review.objects.create(
                        item=item,
                        author=user,
                        rating=rating,
                        title=f"Review #{i+1} for {item_name}",
                        content=f"This is a dummy review. I gave it {rating} stars because it is {random.choice(['amazing', 'good', 'decent'])}."
                    )

        self.stdout.write(self.style.SUCCESS('Successfully populated items and reviews!'))