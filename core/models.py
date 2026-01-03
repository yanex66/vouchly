from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal

# --- BANK OPTIONS ---
BANK_CHOICES = (
    ('Access Bank', 'Access Bank'),
    ('GTBank', 'Guaranty Trust Bank'),
    ('First Bank', 'First Bank of Nigeria'),
    ('UBA', 'United Bank for Africa'),
    ('Zenith Bank', 'Zenith Bank'),
    ('Kuda', 'Kuda Microfinance Bank'),
    ('OPay', 'OPay'),
    ('PalmPay', 'PalmPay'),
    ('Other', 'Other'),
)

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.CASCADE)
    icon = models.ImageField(upload_to='category_icons/', blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        full_path = [self.name]
        k = self.parent
        while k is not None:
            full_path.append(k.name)
            k = k.parent
        return ' -> '.join(full_path[::-1])

class Item(models.Model):
    category = models.ForeignKey(Category, related_name='items', on_delete=models.CASCADE)
    owner = models.ForeignKey(User, related_name='claimed_items', on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Optional: Show a strike-through price")
    website = models.URLField(blank=True, null=True)
    affiliate_link = models.URLField(blank=True, null=True)
    image = models.ImageField(upload_to='item_images/', blank=True, null=True)
    specifications = models.JSONField(default=dict, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    is_featured = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Review(models.Model):
    RATING_CHOICES = (
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    )
    item = models.ForeignKey(Item, related_name='reviews', on_delete=models.CASCADE)
    author = models.ForeignKey(User, related_name='reviews', on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    # THIS IS THE FIELD THE DATABASE IS CURRENTLY MISSING
    is_featured = models.BooleanField(default=False, help_text="Check this to show as 'Review of the Week'")

    class Meta:
        unique_together = ('item', 'author')

    def save(self, *args, **kwargs):
        # Logic to ensure only ONE review is featured at a time
        if self.is_featured:
            Review.objects.filter(is_featured=True).update(is_featured=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item.name} - {self.rating} stars"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(default='default.jpg', upload_to='profile_pics')
    earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    saved_bank_name = models.CharField(max_length=100, choices=BANK_CHOICES, blank=True, null=True)
    saved_account_name = models.CharField(max_length=200, blank=True, null=True)
    saved_account_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f'{self.user.username} Profile'

class Referral(models.Model):
    referrer = models.ForeignKey(User, related_name='referrals', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    clicks = models.IntegerField(default=0)
    sales_count = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('referrer', 'item')

    def __str__(self):
        return f"{self.referrer.username} -> {self.item.name}"

class PayoutRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('REJECTED', 'Rejected'),
    )
    user = models.ForeignKey(User, related_name='payouts', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    bank_name = models.CharField(max_length=100, choices=BANK_CHOICES)
    account_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            old_payout = PayoutRequest.objects.get(pk=self.pk)
            if old_payout.status != 'REJECTED' and self.status == 'REJECTED':
                self.user.profile.earnings += self.amount
                self.user.profile.save()
            elif old_payout.status == 'REJECTED' and self.status != 'REJECTED':
                self.user.profile.earnings -= self.amount
                self.user.profile.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - ${self.amount} ({self.status})"

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()