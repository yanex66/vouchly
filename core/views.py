import os
import decimal
import requests
import urllib.parse
import random
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.db import models
from django.db.models import Q, Avg, Count, Sum, F
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify

# Model and Form Imports
from .models import (
    Item, Category, Review, Profile, Referral, 
    PayoutRequest, ProductReferral, ChatMessage, PromotionPlan,
    AdvertiserVerification, SubscriptionPrice, Order
)
from .forms import (
    ReviewForm, UserRegisterForm, ProfileUpdateForm, 
    PayoutRequestForm, PromotionRequestForm, AdvertiserVerificationForm
)

# 1. HOMEPAGE & DISCOVERY
def home(request):
    hero_items = Item.objects.filter(is_featured=True)
    top_rated = Item.objects.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')[:4]
    latest_items = Item.objects.order_by('-created_at')[:4]
    featured_reviewers = User.objects.annotate(num_reviews=Count('reviews')).filter(num_reviews__gt=0).order_by('-num_reviews')[:4]
    featured_review = Review.objects.filter(is_featured=True).first()
    
    context = {
        'hero_items': hero_items, 
        'top_rated': top_rated,
        'latest_items': latest_items, 
        'featured_review': featured_review,
        'featured_reviewers': featured_reviewers,
        'is_authenticated': request.user.is_authenticated,
    }
    return render(request, 'core/home.html', context)

# 2. THE MARKETPLACE STOREFRONT
def marketplace(request):
    """The main commercial storefront hub."""
    items = Item.objects.all().order_by('-created_at')
    categories = Category.objects.filter(parent=None)
    
    paginator = Paginator(items, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'core/marketplace.html', {
        'items': page_obj,
        'categories': categories
    })

def category_list(request):
    """Redirects to marketplace for the main UI."""
    return redirect('marketplace')

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    items = Item.objects.filter(category=category).order_by('-created_at')
    categories = Category.objects.filter(parent=None)
    return render(request, 'core/marketplace.html', {
        'category': category, 
        'items': items,
        'categories': categories
    })

# 3. HYBRID REVENUE ENGINE (FIXED REDIRECT LOOP)
@login_required(login_url='/login/')
def buy_item(request, slug):
    """Bridge for Marketer clicks. Redirects to Partner Site for Official Items."""
    item = get_object_or_404(Item, slug=slug)
    ref = request.GET.get('ref', 'DIRECT')
    
    if ref != 'DIRECT':
        referrer = User.objects.filter(username=ref).first()
        if referrer:
            pr, _ = ProductReferral.objects.get_or_create(referrer=referrer, item=item)
            pr.clicks += 1
            pr.save()

    if not item.is_escrow_required and item.external_url:
        return HttpResponseRedirect(item.external_url)
    
    return redirect(f'/checkout/{slug}/?ref={ref}')

@login_required(login_url='/login/')
def product_checkout(request, slug):
    item = get_object_or_404(Item, slug=slug)
    ref_code = request.GET.get('ref', 'DIRECT')
    referrer = User.objects.filter(username=ref_code).first() if ref_code != 'DIRECT' else None

    if not item.is_escrow_required:
        return redirect('item_detail', slug=slug)

    order, created = Order.objects.get_or_create(
        item=item,
        buyer=request.user,
        seller=item.owner,
        status='PENDING',
        defaults={
            'amount': item.price,
            'commission_earned': item.commission_naira,
            'referrer': referrer
        }
    )

    return render(request, 'core/product_checkout.html', {
        'order': order,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
        'flw_public_key': settings.FLUTTERWAVE_PUBLIC_KEY,
    })

@login_required(login_url='/login/')
def verify_product_payment(request):
    reference = request.GET.get('reference') or request.GET.get('transaction_id')
    gateway = request.GET.get('gateway')
    is_success = False
    
    if gateway == 'paystack':
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        res = requests.get(url, headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}).json()
        if res.get('status') and res['data']['status'] == 'success': is_success = True
    elif gateway == 'flutterwave':
        url = f"https://api.flutterwave.com/v3/transactions/{reference}/verify"
        res = requests.get(url, headers={"Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}"}).json()
        if res.get('status') == 'success' and res['data']['status'] == 'successful': is_success = True
    
    if is_success:
        order = Order.objects.filter(buyer=request.user, status='PENDING').last()
        if order:
            order.status = 'PAID'
            order.payment_reference = reference
            order.save()
            messages.success(request, "Funds Held in Escrow. Check your dashboard for the PIN.")
            return redirect('dashboard')
    
    messages.error(request, "Payment failed verification.")
    return redirect('dashboard')

# 4. DELIVERY & ESCROW PIN Logic
@login_required
def confirm_receipt(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user, status='SHIPPED')
    
    if request.method == 'POST':
        input_pin = request.POST.get('delivery_pin')
        if input_pin == order.delivery_pin:
            order.status = 'COMPLETED'
            order.save()
            
            # Seller Payout
            seller_prof = order.seller.profile
            seller_prof.balance += (order.amount - order.commission_earned)
            seller_prof.save()
            
            # Marketer Payout
            if order.referrer:
                marketer_prof = order.referrer.profile
                marketer_prof.balance += order.commission_earned
                marketer_prof.save()
                
            messages.success(request, "PIN Verified! Funds released to all parties.")
            return redirect('dashboard')
        else:
            messages.error(request, "Incorrect PIN. Do not release funds yet.")
            
    return render(request, 'core/confirm_receipt.html', {'order': order})

@login_required
def mark_as_shipped(request, order_id):
    order = get_object_or_404(Order, id=order_id, seller=request.user, status='PAID')
    order.status = 'SHIPPED'
    order.save()
    messages.success(request, "Status updated to Shipped.")
    return redirect('dashboard')

# 5. DASHBOARDS
@login_required(login_url='/login/')
def user_dashboard(request):
    profile = request.user.profile
    context = {
        'profile': profile,
        'now': timezone.now(),
        'available_balance': profile.token_rewards if profile.user_type == 'ADVERTISER' else profile.balance,
        'balance_label': "REWARDS" if profile.user_type == 'ADVERTISER' else "BALANCE",
    }
    
    if profile.user_type == 'ADVERTISER':
        context['my_sales'] = Order.objects.filter(seller=request.user).order_by('-created_at')
        context['my_products'] = Item.objects.filter(owner=request.user)
        return render(request, 'core/advertiser_dashboard.html', context)
    else:
        context['my_purchases'] = Order.objects.filter(buyer=request.user).order_by('-created_at')
        context['referred_orders'] = Order.objects.filter(referrer=request.user).exclude(status='COMPLETED')
        context['my_click_stats'] = ProductReferral.objects.filter(referrer=request.user)
        return render(request, 'core/marketer_dashboard.html', context)

@login_required(login_url='/login/')
def referrals_page(request):
    """Manages the marketer's network/referral history."""
    profile = request.user.profile
    referral_list = Referral.objects.filter(referrer=request.user).order_by('-created_at')
    paginator = Paginator(referral_list, 10)
    my_referrals = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'core/referrals.html', {
        'my_referrals': my_referrals, 
        'profile': profile
    })

# 6. WALLET & PAYOUTS
@login_required(login_url='/login/')
def redeem_tokens(request):
    profile = request.user.profile
    if request.method == 'POST':
        amount = decimal.Decimal(request.POST.get('amount', 0))
        if 0 < amount <= profile.token_rewards:
            profile.token_rewards -= amount
            profile.balance += amount
            profile.save()
            messages.success(request, "Tokens redeemed to balance!")
            return redirect('dashboard')
    return render(request, 'core/redeem_tokens.html', {'vocoin_balance': profile.token_rewards})

@login_required(login_url='/login/')
def request_payout(request):
    profile = request.user.profile
    balance = profile.token_rewards if profile.user_type == 'ADVERTISER' else profile.balance
    if request.method == 'POST':
        form = PayoutRequestForm(request.POST, user_balance=balance)
        if form.is_valid():
            payout = form.save(commit=False)
            payout.user = request.user
            if profile.user_type == 'ADVERTISER': profile.token_rewards -= payout.amount
            else: profile.balance -= payout.amount
            profile.save(); payout.save()
            messages.success(request, "Withdrawal request submitted.")
            return redirect('dashboard')
    else:
        form = PayoutRequestForm(user_balance=balance)
    return render(request, 'core/request_payout.html', {'form': form, 'available_balance': balance})

# 7. AUTHENTICATION & PROFILE
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created! Please login.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'core/register.html', {'form': form})

def set_role_session(request):
    role = request.GET.get('role')
    if role in ['MARKETER', 'ADVERTISER']:
        request.session['pre_selected_role'] = role
        return JsonResponse({'status': 'success', 'role': role})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('edit_profile')
    else:
        form = ProfileUpdateForm(instance=request.user.profile)
    return render(request, 'core/edit_profile.html', {'form': form})

# 8. ADVERTISER WORKFLOW & ANALYTICS
@login_required(login_url='/login/')
def promote_request(request):
    if request.user.profile.user_type != 'ADVERTISER': return redirect('dashboard')
    if request.user.profile.verification_status != 'VERIFIED':
        messages.warning(request, "Verify your identity first.")
        return redirect('verify_identity')
    
    if request.method == 'POST':
        form = PromotionRequestForm(request.POST, request.FILES)
        if form.is_valid():
            promo = form.save(commit=False)
            promo.seller = request.user
            promo.duration_days = 30; promo.save()
            return redirect('promotion_payment', pk=promo.pk)
    else:
        form = PromotionRequestForm()
    return render(request, 'core/promote_request.html', {'form': form})

def promotion_payment(request, pk):
    promo = get_object_or_404(PromotionPlan, pk=pk)
    price_setting = SubscriptionPrice.objects.filter(duration_days=promo.duration_days).first()
    return render(request, 'core/promotion_payment.html', {
        'promotion': promo, 'amount': price_setting.price if price_setting else 500,
        'flw_public_key': settings.FLUTTERWAVE_PUBLIC_KEY, 'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
        'user_email': request.user.email
    })

@login_required(login_url='/login/')
def verify_promotion_payment(request):
    reference = request.GET.get('reference') or request.GET.get('transaction_id')
    gateway = request.GET.get('gateway')
    is_success = False
    
    if gateway == 'paystack':
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        res = requests.get(url, headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}).json()
        if res.get('status') and res['data']['status'] == 'success': is_success = True
    elif gateway == 'flutterwave':
        url = f"https://api.flutterwave.com/v3/transactions/{reference}/verify"
        res = requests.get(url, headers={"Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}"}).json()
        if res.get('status') == 'success' and res['data']['status'] == 'successful': is_success = True
    
    if is_success:
        promo = PromotionPlan.objects.filter(seller=request.user, is_paid=False).last()
        if promo:
            expiry = timezone.now() + timedelta(days=promo.duration_days)
            promo.is_paid, promo.payment_reference, promo.subscription_expiry = True, reference, expiry
            promo.save()
            Item.objects.create(
                category=promo.category, owner=promo.seller, name=promo.product_name,
                description=promo.description, image=promo.product_image, price=promo.product_price,
                commission_naira=(promo.product_price * promo.commission_percentage) / 100,
                expiry_date=expiry, is_featured=True
            )
            return redirect('dashboard')
    return redirect('dashboard')

@login_required(login_url='/login/')
def ad_analytics(request):
    my_items = Item.objects.filter(owner=request.user).annotate(total_clicks=Sum('referral_clicks__clicks')).filter(total_clicks__gt=0)
    top_marketers = ProductReferral.objects.filter(item__owner=request.user).values('referrer__username').annotate(total_clicks=Sum('clicks')).order_by('-total_clicks')[:6]
    return render(request, 'core/ad_analytics.html', {'my_items': my_items, 'top_marketers': top_marketers})

# 9. REVIEWS & DETAILS (FIXED: PERCENTAGE DISPLAY & LINK BRIDGE)
def item_detail(request, slug):
    item = get_object_or_404(Item, slug=slug)
    
    if item.is_escrow_required:
        ref_link = f"{request.build_absolute_uri('/')[:-1]}/checkout/{item.slug}/?ref={request.user.username}" if request.user.is_authenticated else ""
    else:
        ref_link = f"{request.build_absolute_uri('/')[:-1]}/buy/{item.slug}/?ref={request.user.username}" if request.user.is_authenticated else ""
    
    avg_rating = item.reviews.aggregate(Avg('rating'))['rating__avg'] or 5.0
    
    return render(request, 'core/item_detail.html', {
        'item': item, 
        'referral_link': ref_link, 
        'avg_rating': avg_rating,
        'form': ReviewForm()
    })

@login_required
def add_review(request, slug):
    item = get_object_or_404(Item, slug=slug)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.item, review.author = item, request.user
            review.save()
    return redirect('item_detail', slug=slug)

@login_required
def delete_review(request, review_id):
    get_object_or_404(Review, id=review_id, author=request.user).delete()
    return redirect('dashboard')

# 10. SYSTEM UTILS
@login_required
def verify_bank_account(request):
    num = request.GET.get('account_number'); slug = request.GET.get('bank_slug')
    mapping = {'access':'044', 'gtbank': '058', 'zenith': '057', 'opay': '999992', 'palmpay': '999991', 'kuda': '999109'}
    url = f"https://api.paystack.co/bank/resolve?account_number={num}&bank_code={mapping.get(slug)}"
    try:
        res = requests.get(url, headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}).json()
        if res.get('status'): return JsonResponse({'status': True, 'account_name': res['data']['account_name']})
    except: pass
    return JsonResponse({'status': False})

@login_required
def verify_identity(request):
    if request.method == 'POST':
        form = AdvertiserVerificationForm(request.POST, request.FILES)
        if form.is_valid():
            v = form.save(commit=False); v.user = request.user; v.save()
            request.user.profile.verification_status = 'PENDING'; request.user.profile.save()
            return redirect('dashboard')
    else: form = AdvertiserVerificationForm()
    return render(request, 'core/verify_identity.html', {'form': form})

def search(request):
    q = request.GET.get('query', '')
    results = Item.objects.filter(Q(name__icontains=q) | Q(description__icontains=q))
    return render(request, 'core/marketplace.html', {'items': results, 'query': q})

@login_required(login_url='/login/')
def checkout_desk(request):
    """The 'waiting room' for initiated but unpaid orders."""
    pending_orders = Order.objects.filter(buyer=request.user, status='PENDING').order_by('-created_at')
    return render(request, 'core/checkout_desk.html', {'pending_orders': pending_orders})

def payment_success(request, pk): return render(request, 'core/payment_success.html', {'pk': pk})
def about(request): return render(request, 'core/about.html', {'is_authenticated': request.user.is_authenticated})
def contact(request): return render(request, 'core/contact.html')
def privacy(request): return render(request, 'core/privacy.html')
def terms(request): return render(request, 'core/terms.html')

# --- 11. BULK CATEGORY UPLOAD (Temporary Admin Tool) ---
def bulk_add_categories(request):
    """
    Visit: vouchly.store/run-bulk-categories/ while logged in as admin.
    """
    if not request.user.is_superuser:
        return HttpResponse("Unauthorized", status=401)
        
    category_names = [
        "Digital Courses", "AI & Automation Tools", "E-books & Guides", 
        "Software & Subscriptions", "Smartphones & Tablets", "Computers & Laptops", 
        "Gadgets & Wearables", "Gaming & Consoles", "Men's Fashion", 
        "Women's Fashion", "Health & Wellness", "Beauty & Skincare", 
        "Marketing & Advertising", "Freelance Services", "Business Consulting", 
        "Real Estate & Housing", "Home & Kitchen", "Automobiles & Parts", 
        "Crypto & Finance", "Data & Airtime", "Gift Cards", 
        "Job Opportunities", "Events & Tickets", "Travel & Tourism", 
        "Agriculture & Farm", "Education & Scholarships", "Food & Groceries", 
        "Interior Design", "Photography & Video", "Others"
    ]

    categories_to_create = [
        Category(name=name, slug=slugify(name)) 
        for name in category_names
    ]
    
    Category.objects.bulk_create(categories_to_create, ignore_conflicts=True)
    return HttpResponse(f"<h1>Success!</h1><p>Successfully added {len(category_names)} categories to Vouchly.</p>")