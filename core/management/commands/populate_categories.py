from django.core.management.base import BaseCommand
from core.models import Category

class Command(BaseCommand):
    help = 'Populates the database with a rich set of categories'

    def handle(self, *args, **kwargs):
        # The structure is 'Parent Category': ['Child 1', 'Child 2', ...]
        data = {
            'Travel & Transport': [
                'Airlines', 'Hotels', 'Car Rentals', 'Cruises', 'Trains', 'Travel Agencies'
            ],
            'Electronics': [
                'Laptops', 'Smartphones', 'Cameras', 'Headphones', 'Gaming Consoles', 'Drones'
            ],
            'Fashion': [
                'Men', 'Women', 'Kids', 'Shoes', 'Watches', 'Jewelry'
            ],
            'Software & Apps': [
                'Productivity', 'Security', 'Graphic Design', 'Video Games', 'SaaS', 'Mobile Apps'
            ],
            'Home & Kitchen': [
                'Furniture', 'Appliances', 'Decor', 'Gardening', 'Tools'
            ],
            'Health & Beauty': [
                'Skincare', 'Makeup', 'Supplements', 'Fitness Equipment', 'Mental Health'
            ],
            'Automotive': [
                'Cars', 'Motorcycles', 'Car Parts', 'Electric Vehicles'
            ],
            'Services': [
                'Banking', 'Insurance', 'Real Estate', 'Legal', 'Education'
            ],
            'Entertainment': [
                'Movies', 'Music Streaming', 'Books', 'Events'
            ]
        }

        self.stdout.write("Starting category population...")

        for parent_name, children in data.items():
            # Create the Parent
            parent, created = Category.objects.get_or_create(name=parent_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created Parent: {parent_name}'))
            
            # Create the Children
            for child_name in children:
                child, child_created = Category.objects.get_or_create(name=child_name, parent=parent)
                if child_created:
                    self.stdout.write(f'  - Added: {child_name}')

        self.stdout.write(self.style.SUCCESS('Successfully populated all categories!'))