import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
import requests
from core.models import Category, Item, Review

class Command(BaseCommand):
    help = 'Generates 100+ products using a mix-and-match algorithm'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting Mass Population (100+ Items)...")

        # 1. Setup User
        user, _ = User.objects.get_or_create(username='StockBot')
        if not user.password:
            user.set_password('pass123')
            user.save()

        # 2. Define Image Pools (Reliable public URLs)
        # We reuse these images across variations to save bandwidth/time
        image_pool = {
            'Electronics': [
                'https://images.unsplash.com/photo-1511384039668-7e67453e3efd?q=80&w=1000', # Tech
                'https://images.unsplash.com/photo-1546868871-7041f2a55e12?q=80&w=1000', # Watch
                'https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?q=80&w=1000', # Laptop
                'https://images.unsplash.com/photo-1592899671815-51351806509d?q=80&w=1000', # Phone
            ],
            'Fashion': [
                'https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=1000', # Shoe
                'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?q=80&w=1000', # T-shirt
                'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?q=80&w=1000', # Headphones
            ],
            'Home': [
                'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?q=80&w=1000', # Chair
                'https://images.unsplash.com/photo-1583847268964-b28dc8f51f92?q=80&w=1000', # Sofa
            ]
        }

        # 3. Generator Data
        brands = ['Samsung', 'Apple', 'Sony', 'Nike', 'Adidas', 'Dell', 'HP', 'LG', 'Rolex', 'Toyota']
        models = ['Pro', 'Max', 'Ultra', 'Air', 'Sport', 'Classic', 'Elite', 'X', 'Series 9', 'Fold']
        types = ['Phone', 'Laptop', 'Watch', 'Headphones', 'Sneakers', 'Camera', 'TV', 'Monitor']

        count = 0
        target = 100

        self.stdout.write("Generating products...")

        while count < target:
            # Randomly build a name
            brand = random.choice(brands)
            model = random.choice(models)
            p_type = random.choice(types)
            
            # Example Name: "Samsung Phone Ultra"
            name = f"{brand} {p_type} {model}"
            
            # Determine Category
            if p_type in ['Phone', 'Laptop', 'Watch', 'Camera', 'TV', 'Monitor', 'Headphones']:
                cat_name = 'Electronics'
            elif p_type in ['Sneakers']:
                cat_name = 'Fashion'
            else:
                cat_name = 'Home'
            
            category, _ = Category.objects.get_or_create(name=cat_name)

            # Skip if exists
            if Item.objects.filter(name=name).exists():
                continue

            # Pick an image from the pool
            img_url = random.choice(image_pool[cat_name])

            # Create Item
            item = Item(
                name=name,
                category=category,
                description=f"The all new {name} features industry leading performance and style. Perfect for daily use.",
                owner=user,
                is_featured=random.choice([True, False, False]) # 33% chance featured
            )

            # Download Image (Fast mode: Using known working URLs)
            try:
                response = requests.get(img_url, timeout=5)
                if response.status_code == 200:
                    filename = f"{random.randint(1000,9999)}_{cat_name.lower()}.jpg"
                    item.image.save(filename, ContentFile(response.content), save=False)
            except:
                pass # If download fails, just skip image but keep item
            
            item.save()
            count += 1
            
            # Add Rating
            Review.objects.create(
                item=item,
                author=user,
                rating=random.randint(3, 5),
                title="Verified Purchase",
                content="Great product, fast shipping!"
            )
            
            if count % 10 == 0:
                self.stdout.write(f" - Created {count} items...")

        self.stdout.write(self.style.SUCCESS(f'Successfully added {count} new products!'))