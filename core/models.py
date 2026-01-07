from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.db.models.signals import post_save
from django.dispatch import receiver

# --- EXISTING MODELS ---

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
        return self.name

class Item(models.Model):
    category = models.ForeignKey(Category, related_name='items', on_delete=models.CASCADE)
    owner = models.ForeignKey(User, related_name='claimed_items', on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
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
    item = models.ForeignKey(Item, related_name='reviews', on_delete=models.CASCADE)
    author = models.ForeignKey(User, related_name='reviews', on_delete=models.CASCADE)
    rating = models.IntegerField()
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        unique_together = ('item', 'author')

    def __str__(self):
        return f"{self.item.name} - {self.rating} stars"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(default='default.jpg', upload_to='profile_pics')
    token_rewards = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f'{self.user.username} Profile'

class Referral(models.Model):
    referrer = models.ForeignKey(User, related_name='referrals_made', on_delete=models.CASCADE)
    referred_user = models.OneToOneField(User, related_name='referred_by', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.referrer.username} invited {self.referred_user.username}"

class PayoutRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ]

    BANK_CHOICES = [
        ('', 'Select Bank'),
        ('access', 'Access Bank'),
        ('ecobank', 'Ecobank Nigeria'),
        ('fidelity', 'Fidelity Bank'),
        ('firstbank', 'First Bank of Nigeria'),
        ('gtbank', 'Guaranty Trust Bank (GTBank)'),
        ('kuda', 'Kuda Bank'),
        ('moniepoint', 'Moniepoint MFB'),
        ('opay', 'Opay'),
        ('palmpay', 'Palmpay'),
        ('uba', 'United Bank for Africa (UBA)'),
        ('zenith', 'Zenith Bank'),
    ]

    user = models.ForeignKey(User, related_name='payouts', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2) 
    bank_name = models.CharField(max_length=100, choices=BANK_CHOICES, null=True, blank=True)
    account_number = models.CharField(max_length=10, null=True, blank=True)
    account_name = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            old_status = PayoutRequest.objects.get(pk=self.pk).status
            if self.status == 'CANCELLED' and old_status != 'CANCELLED':
                profile = self.user.profile
                profile.balance += self.amount
                profile.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.amount} ({self.status})"

# --- NEW CHAT MODEL ---

class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    is_from_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        sender = self.user.username if self.user else "Guest User"
        return f"Chat from {sender} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

# --- SIGNALS ---

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()