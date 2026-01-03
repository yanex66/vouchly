import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Category, Item, Review

class Command(BaseCommand):
    help = 'Populates the database with 50+ items and reviews instantly'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting Master Population...")

        # 1. Setup Users (Reviewers)
        user_names = ['TechKing', 'TravelBee', 'Fashionista99', 'GamerX', 'SarahLovesFood']
        users = []
        for name in user_names:
            u, _ = User.objects.get_or_create(username=name)
            if not u.password:
                u.set_password('pass123')
                u.save()
            users.append(u)

        # 2. Master Data Dictionary
        catalog = {
            'Airlines': [
                ('Qatar Airways', 'Voted best airline. The Q-Suite business class is amazing.'),
                ('Emirates', 'Excellent service, great in-flight entertainment system (ICE).'),
                ('Singapore Airlines', ' impeccable service and very comfortable economy seats.'),
                ('Delta Air Lines', 'Reliable US carrier with good SkyMiles benefits.'),
                ('Air Peace', 'Leading Nigerian airline, good for regional West African travel.'),
            ],
            'Smartphones': [
                ('iPhone 16 Pro', 'The latest from Apple with the new A18 chip and AI features.'),
                ('Samsung Galaxy S24 Ultra', 'Best Android screen on the market with S-Pen support.'),
                ('Google Pixel 9', 'The smartest AI camera in a phone.'),
                ('Tecno Phantom V Fold', 'Affordable foldable phone popular in African markets.'),
                ('Infinix Zero 30', 'Great vlog camera and fast charging for the price.'),
            ],
            'Laptops': [
                ('MacBook Air M3', 'Perfect balance of power and battery life for students.'),
                ('Dell XPS 15', 'The best Windows laptop display and build quality.'),
                ('HP Spectre x360', 'Beautiful 2-in-1 convertible laptop.'),
                ('Lenovo ThinkPad X1', 'The ultimate business machine. Indestructible keyboard.'),
            ],
            'Shoes': [
                ('Nike Air Force 1', 'Classic white sneakers that go with everything.'),
                ('Adidas Yeezy Boost', 'Incredibly comfortable walking shoes.'),
                ('Timberland Boots', 'Rugged, durable, and stylish for outdoor wear.'),
                ('Louboutin Heels', 'High-end luxury fashion statement.'),
            ],
            'Watches': [
                ('Rolex Submariner', 'The most iconic diver watch in the world.'),
                ('Apple Watch Series 10', 'Best health tracking and iPhone integration.'),
                ('Casio G-Shock', 'Tough, reliable, and affordable.'),
                ('Seiko 5 Sports', 'Great automatic watch for beginners.'),
            ],
            'Cars': [
                ('Toyota Camry', 'The most reliable sedan on the road.'),
                ('Mercedes Benz G-Wagon', 'The ultimate status symbol SUV.'),
                ('Tesla Model Y', 'Best selling electric SUV globally.'),
                ('Lexus RX 350', 'Luxury and reliability combined.'),
            ]
        }

        # 3. Loop through Catalog
        total_items = 0
        for cat_name, products in catalog.items():
            # Get or Create Category
            category, _ = Category.objects.get_or_create(name=cat_name)
            
            for prod_name, desc in products:
                # Create Item
                item, created = Item.objects.get_or_create(
                    name=prod_name,
                    defaults={
                        'category': category,
                        'description': desc,
                        'owner': users[0], # Assign to first user
                        'is_featured': random.choice([True, False, False]) # 33% chance to be featured
                    }
                )
                
                if created:
                    total_items += 1
                    # Add 3-6 Fake Reviews per item
                    for i in range(random.randint(3, 6)):
                        reviewer = random.choice(users)
                        rating = random.choice([3, 4, 5, 5]) # Skew towards positive
                        
                        titles = ['Amazing!', 'Worth the money', 'Solid choice', 'Could be better', 'My honest thoughts']
                        
                        Review.objects.create(
                            item=item,
                            author=reviewer,
                            rating=rating,
                            title=random.choice(titles),
                            content=f"I used this for a few weeks. {desc} Overall I give it {rating} stars."
                        )

        self.stdout.write(self.style.SUCCESS(f'Done! Added {total_items} new products with reviews.'))