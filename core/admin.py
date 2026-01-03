from django.contrib import admin
from .models import Category, Item, Review, Profile, Referral, PayoutRequest

# --- INLINE SETTING ---
# This allows you to add/edit Items directly inside the Category page
class ItemInline(admin.TabularInline):
    model = Item
    extra = 1 # Number of empty rows to show for new items
    # Added 'price' and 'discount_price' to the inline editor
    fields = ('name', 'price', 'discount_price', 'is_featured', 'image')
    show_change_link = True # Adds a link to open the full item editor

# 1. Customize Category Admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ItemInline]

# 2. Customize Item Admin
@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    # Added 'price' to the list display
    list_display = ('name', 'price', 'category', 'is_featured', 'created_at')
    list_filter = ('category', 'is_featured')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    
    # Organizing fields to make price prominent in the editor
    fieldsets = (
        (None, {
            'fields': ('category', 'owner', 'name', 'slug', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price'),
            'description': 'Set the current price and an optional discount price for strike-through display.'
        }),
        ('Media & Links', {
            'fields': ('image', 'website', 'affiliate_link')
        }),
        ('Advanced', {
            'fields': ('specifications', 'is_featured'),
            'classes': ('collapse',),
        }),
    )

# 3. Customize Review Admin
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('item', 'author', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')

# 4. Customize Profile Admin
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'earnings')
    search_fields = ('user__username',)
    list_editable = ('earnings',)

# 5. Customize Referral Admin
@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('referrer', 'item', 'clicks', 'sales_count')
    list_filter = ('referrer',)
    search_fields = ('referrer__username', 'item__name')

# 6. Customize Payout Request Admin
@admin.register(PayoutRequest)
class PayoutRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'bank_name', 'account_number', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'bank_name')
    search_fields = ('user__username', 'account_name', 'account_number')
    list_editable = ('status',)

    def current_balance(self, obj):
        return f"₦{obj.user.profile.earnings}"
    current_balance.short_description = "User's Remaining Balance"

    fields = (
        'current_balance',
        'user', 
        'amount', 
        'bank_name', 
        'account_number', 
        'account_name', 
        'status', 
        'rejection_reason', 
        'created_at'
    )
    
    readonly_fields = ('current_balance', 'user', 'amount', 'bank_name', 'account_number', 'account_name', 'created_at')