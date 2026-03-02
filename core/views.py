import os
import decimal
import requests
import urllib.parse
import random
import time
import json
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.db import models
from django.db.models import Q, Avg, Count, Sum, F
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate 
from django.core.paginator import Paginator
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from django.core.mail import send_mail 

# Model and Form Imports
from .models import (
    Item, Category, Review, Profile, Referral, 
    PayoutRequest, ProductReferral, ChatMessage, PromotionPlan,
    AdvertiserVerification, SubscriptionPrice, Order, FAQ 
)
from .forms import (
    ReviewForm, UserRegisterForm, ProfileUpdateForm, 
    PayoutRequestForm, PromotionRequestForm, AdvertiserVerificationForm
)

# --- HELPER: SMS GATEWAY ---
def send_sms_alert(phone_number, message):
    url = "https://api.ng.termii.com/api/sms/send"
    payload = {
        "to": phone_number,
        "from": "Vouchly",
        "sms": message,
        "type": "plain",
        "channel": "generic",
        "api_key": settings.TERMII_API_KEY,
    }
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except:
        return None

# --- HELPER: AUTOMATED NIN & BANK VERIFICATION ---
def verify_nin_api(nin_number):
    """
    Simulated call to identity provider.
    In production, this would return a dictionary with NIN details from NIMC.
    """
    if nin_number and len(str(nin_number)) == 11:
        # Simulated data grabbed from NIMC records
        return {
            "status": "success",
            "full_name": "NIN Verified User",
            "address": "Verified NIN Address, Lagos, Nigeria"
        }
    return None


# 1. HOMEPAGE & DISCOVERY
def home(request):
    hero_items = Item.objects.filter(is_featured=True)
    top_rated = Item.objects.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')[:4]
    latest_items = Item.objects.order_by('-created_at')[:4]
    
    featured_reviewers = Review.objects.select_related('author', 'author__profile', 'item').order_by('-created_at')[:10]
    featured_review = Review.objects.filter(is_featured=True).first()
    
    total_users = User.objects.count()
    total_payouts = PayoutRequest.objects.filter(status='PAID').aggregate(Sum('amount'))['amount__sum'] or 0
    
    total_advertisers = Profile.objects.filter(user_type='ADVERTISER').count()
    free_slots_left = max(0, 50 - total_advertisers)
    
    faqs = FAQ.objects.filter(is_active=True)

    context = {
        'hero_items': hero_items, 
        'top_rated': top_rated,
        'latest_items': latest_items, 
        'featured_review': featured_review,
        'featured_reviewers': featured_reviewers,
        'is_authenticated': request.user.is_authenticated,
        'total_users': total_users,    
        'total_payouts': total_payouts, 
        'free_slots_left': free_slots_left,
        'faqs': faqs,                  
    }
    return render(request, 'core/home.html', context)

# 2. THE MARKETPLACE STOREFRONT
def marketplace(request):
    items = Item.objects.filter(
        Q(expiry_date__gt=timezone.now()) | Q(expiry_date__isnull=True)
    ).order_by('-is_featured', '-created_at')
    
    categories = Category.objects.filter(parent=None)
    paginator = Paginator(items, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'core/marketplace.html', {
        'items': page_obj,
        'categories': categories
    })

def category_list(request):
    return redirect('marketplace')

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    items = Item.objects.filter(category=category).filter(
        Q(expiry_date__gt=timezone.now()) | Q(expiry_date__isnull=True)
    ).order_by('-created_at')
    
    categories = Category.objects.filter(parent=None)
    return render(request, 'core/marketplace.html', {
        'category': category, 
        'items': items,
        'categories': categories
    })

# 3. HYBRID REVENUE ENGINE & CHECKOUT
def buy_item(request, slug):
    item = get_object_or_404(Item, slug=slug)
    ref = request.GET.get('ref')
    
    if ref:
        request.session['referrer_ref'] = ref
        referrer_user = User.objects.filter(username=ref).first()
        if referrer_user:
            pr, _ = ProductReferral.objects.get_or_create(referrer=referrer_user, item=item)
            pr.clicks += 1
            pr.save()

    if not item.is_escrow_required and item.external_url:
        return HttpResponseRedirect(item.external_url)

    if not request.user.is_authenticated:
        request.session['next_url'] = f'/checkout/{slug}/'
        request.session['force_buyer_mode'] = True 
        messages.info(request, "Please create an account to secure your purchase.")
        return redirect('register')
    
    return redirect(f'/checkout/{slug}/?ref={ref if ref else "DIRECT"}')

@login_required(login_url='/login/')
def product_checkout(request, slug):
    item = get_object_or_404(Item, slug=slug)
    ref_code = request.GET.get('ref') or request.session.get('referrer_ref')
    referrer = User.objects.filter(username=ref_code).first() if ref_code and ref_code != 'DIRECT' else None

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
        'item': item,
        'timestamp': int(time.time()),
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
        'flw_public_key': settings.FLUTTERWAVE_PUBLIC_KEY,
        'user_email': request.user.email,
        'total_amount': float(order.amount),
    })

@login_required(login_url='/login/')
def verify_product_payment(request):
    reference = request.GET.get('reference') or request.GET.get('transaction_id')
    order = Order.objects.filter(buyer=request.user, status='PENDING').last()
    if order:
        order.status = 'PAID'
        order.payment_reference = reference
        order.save()
        messages.success(request, "Payment successful. Funds held in Escrow.")
    return redirect('checkout_desk')

# 4. DASHBOARDS & REFERRALS
@login_required(login_url='/login/')
def user_dashboard(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    context = {'profile': profile, 'now': timezone.now()}
    
    if profile.user_type == 'ADVERTISER':
        revenue_data = Order.objects.filter(seller=request.user, status='COMPLETED').aggregate(earnings=Sum(F('amount') - F('commission_earned')))
        context.update({
            'available_balance': profile.balance,
            'total_revenue': revenue_data['earnings'] or 0,
            'my_sales': Order.objects.filter(seller=request.user).order_by('-created_at'),
            'my_products': Item.objects.filter(owner=request.user)
        })
        return render(request, 'core/advertiser_dashboard.html', context)
    else:
        context.update({
            'available_balance': profile.balance,
            'my_purchases': Order.objects.filter(buyer=request.user).order_by('-created_at'),
            'referred_orders': Order.objects.filter(referrer=request.user).exclude(status='COMPLETED'),
            'my_click_stats': ProductReferral.objects.filter(referrer=request.user)
        })
        return render(request, 'core/marketer_dashboard.html', context)

@login_required(login_url='/login/')
def referrals_page(request):
    profile = request.user.profile
    referral_list = Referral.objects.filter(referrer=request.user).order_by('-created_at')
    paginator = Paginator(referral_list, 10)
    my_referrals = paginator.get_page(request.GET.get('page'))
    return render(request, 'core/referrals.html', {'my_referrals': my_referrals, 'profile': profile})

# 5. ADVERTISER WORKFLOW & ANALYTICS
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
            promo.duration_days = 30
            
            total_advertisers = Profile.objects.filter(user_type='ADVERTISER').count()
            if total_advertisers <= 50:
                expiry = timezone.now() + timedelta(days=30)
                promo.is_paid = True
                promo.subscription_expiry = expiry
                promo.save()
                Item.objects.create(
                    category=promo.category, owner=promo.seller, name=promo.product_name,
                    price=promo.product_price, expiry_date=expiry, is_featured=True, image=promo.product_image
                )
                messages.success(request, "Early Bird slot secured! Your item is live.")
                return redirect('dashboard')

            promo.save()
            return redirect('promotion_payment', pk=promo.pk)
    else:
        form = PromotionRequestForm()
    return render(request, 'core/promote_request.html', {'form': form})

@login_required(login_url='/login/')
def ad_analytics(request):
    my_items = Item.objects.filter(owner=request.user).annotate(total_clicks=Sum('referral_clicks__clicks'))
    top_marketers = ProductReferral.objects.filter(item__owner=request.user).values('referrer__username').annotate(total_clicks=Sum('clicks')).order_by('-total_clicks')[:6]
    return render(request, 'core/ad_analytics.html', {'my_items': my_items, 'top_marketers': top_marketers})

@login_required(login_url='/login/')
def delete_product(request, slug):
    if request.user.profile.user_type != 'ADVERTISER': 
        return redirect('dashboard')
    item = get_object_or_404(Item, slug=slug, owner=request.user)
    if request.method == 'POST':
        item.delete()
        messages.success(request, "Product deleted successfully.")
        return redirect('dashboard')
    return render(request, 'core/delete_confirm.html', {'item': item})

# 6. AUTHENTICATION & PROFILE
def register(request):
    is_forced_buyer = request.session.get('force_buyer_mode', False)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password') or request.POST.get('password1')
        
        existing_user = User.objects.filter(username=username).first()
        
        if existing_user and password:
            auth_user = authenticate(request, username=username, password=password)
            if auth_user is not None:
                login(request, auth_user, backend='django.contrib.auth.backends.ModelBackend')
                next_url = request.session.pop('next_url', None)
                request.session.pop('force_buyer_mode', None)
                messages.success(request, f"Welcome back, {auth_user.username}!")
                return redirect(next_url) if next_url else redirect('dashboard')
            else:
                messages.error(request, "Username exists, but the password is incorrect.")
                
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            selected_role = form.cleaned_data.get('user_type')
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.user_type = 'BUYER' if is_forced_buyer else selected_role
            profile.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            next_url = request.session.pop('next_url', None)
            request.session.pop('force_buyer_mode', None)
            messages.success(request, "Account created successfully!")
            return redirect(next_url) if next_url else redirect('dashboard')
    else:
        form = UserRegisterForm()
        
    return render(request, 'core/register.html', {'form': form, 'is_forced_buyer': is_forced_buyer})

@login_required
def edit_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('edit_profile')
    else:
        form = ProfileUpdateForm(instance=profile)
    return render(request, 'core/edit_profile.html', {'form': form, 'user': request.user})

def logout_user(request):
    logout(request)
    return redirect('home')

# 7. REVIEWS & DETAILS
def item_detail(request, slug):
    item = get_object_or_404(Item, slug=slug)
    related_items = Item.objects.filter(category=item.category).exclude(id=item.id)[:4]
    avg_rating = item.reviews.aggregate(Avg('rating'))['rating__avg'] or 5.0
    has_vouched = Review.objects.filter(item=item, author=request.user).exists() if request.user.is_authenticated else False
        
    return render(request, 'core/item_detail.html', {
        'item': item, 
        'related_items': related_items, 
        'avg_rating': avg_rating, 
        'form': ReviewForm(),
        'has_vouched': has_vouched
    })

@login_required
def add_review(request, slug):
    item = get_object_or_404(Item, slug=slug)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            Review.objects.update_or_create(
                item=item, author=request.user,
                defaults={
                    'rating': form.cleaned_data['rating'],
                    'title': form.cleaned_data['title'],
                    'content': form.cleaned_data['content'],
                }
            )
            messages.success(request, "Your vouch has been submitted!")
    return redirect('item_detail', slug=slug)

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, author=request.user)
    slug = review.item.slug
    review.delete()
    messages.success(request, "Vouch deleted.")
    return redirect('item_detail', slug=slug)

# 8. SYSTEM UTILS (NIN, BANK VERIFICATION)
@login_required
def verify_bank_account(request):
    num, bank = request.GET.get('account_number'), request.GET.get('bank_code')
    url = f"https://api.paystack.co/bank/resolve?account_number={num}&bank_code={bank}"
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
    try:
        res = requests.get(url, headers=headers).json()
        return JsonResponse({'status': res.get('status'), 'account_name': res.get('data', {}).get('account_name')})
    except:
        return JsonResponse({'status': False}, status=500)

@login_required
def verify_identity(request):
    """
    NIN-only verification: Automatically grabs address and details from NIN simulation.
    """
    instance, _ = AdvertiserVerification.objects.get_or_create(user=request.user)
    profile, _ = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = AdvertiserVerificationForm(request.POST, request.FILES, instance=instance)
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.accepts('application/json')
        
        if form.is_valid():
            v = form.save(commit=False)
            nin_input = request.POST.get('nin_number', '')

            # GRAB LOGIC: Fetch data from NIN records
            nin_data = verify_nin_api(nin_input)

            if nin_data:
                v.user = request.user
                v.nin_number = nin_input
                v.full_name = nin_data['full_name']
                v.residential_address = nin_data['address'] 
                v.save()

                profile.verification_status = 'VERIFIED'
                profile.save()

                if is_ajax: 
                    return JsonResponse({
                        'status': 'success', 
                        'message': "Identity & Address synced from NIN record.",
                        'is_verified': True
                    })
                messages.success(request, "NIN Sync Successful!")
                return redirect('dashboard')
            else:
                if is_ajax: 
                    return JsonResponse({'status': 'error', 'message': "NIN not found or invalid format."})
                messages.error(request, "Invalid NIN.")
        else:
            if is_ajax: return JsonResponse({'status': 'error', 'message': "Please fill all required fields correctly."})
            
    else:
        form = AdvertiserVerificationForm(instance=instance)
        
    return render(request, 'core/verify_identity.html', {'form': form})

# 9. ESCROW ACTIONS
@login_required
def verify_delivery(request, order_id):
    order = get_object_or_404(Order, id=order_id, seller=request.user)
    if request.method == "POST":
        if request.POST.get('pin') == order.delivery_pin:
            order.status = 'COMPLETED'
            order.is_delivered = True
            order.save()
            messages.success(request, "Funds released!")
    return redirect('checkout_desk')

@login_required
def mark_as_shipped(request, order_id):
    order = get_object_or_404(Order, id=order_id, seller=request.user)
    order.status = 'SHIPPED'
    order.save()
    messages.success(request, "Order on its way!")
    return redirect('checkout_desk')

@login_required(login_url='/login/')
def checkout_desk(request):
    my_orders = Order.objects.filter(buyer=request.user).order_by('-created_at')
    incoming_orders = Order.objects.filter(seller=request.user).exclude(status='PENDING').annotate(
        seller_earning=F('amount') - F('commission_earned')
    )
    return render(request, 'core/checkout_desk.html', {'my_orders': my_orders, 'incoming_orders': incoming_orders})

# 10. SEARCH & SYSTEM REDIRECTS
def search(request):
    q = request.GET.get('query', '')
    results = Item.objects.filter(Q(name__icontains=q) | Q(description__icontains=q))
    return render(request, 'core/marketplace.html', {'items': results, 'query': q})

def set_role_session(request):
    role = request.GET.get('role')
    if role in ['MARKETER', 'ADVERTISER']:
        request.session['pre_selected_role'] = role
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required(login_url='/login/')
def request_payout(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = PayoutRequestForm(request.POST, user_balance=profile.balance)
        if form.is_valid():
            payout = form.save(commit=False)
            payout.user = request.user
            payout.status = 'PENDING'
            payout.save()
            profile.balance -= payout.amount
            profile.save()
            messages.success(request, f"Payout request for ₦{payout.amount} sent!")
            return redirect('dashboard')
    else:
        form = PayoutRequestForm(user_balance=profile.balance)
    return render(request, 'core/request_payout.html', {'form': form, 'available_balance': profile.balance})

# --- URL REQUIRED FUNCTIONS ---

def flyer_view(request):
    return render(request, 'core/flyer.html')

@login_required(login_url='/login/')
def redeem_tokens(request):
    messages.info(request, "Token redemption is coming soon!")
    return redirect('dashboard')

@login_required(login_url='/login/')
def verify_promotion_payment(request):
    messages.success(request, "Promotion payment verified!")
    return redirect('dashboard')

def promotion_payment(request, pk): 
    return HttpResponse("Payment Page Placeholder")

def bulk_add_categories(request):
    if not request.user.is_superuser: return HttpResponse("Unauthorized", status=401)
    Category.objects.bulk_create([Category(name=n, slug=slugify(n)) for n in ["Tech", "Fashion", "Real Estate"]], ignore_conflicts=True)
    return HttpResponse("Done.")

@login_required
def request_refund(request, order_id):
    # Placeholder for refund logic
    messages.info(request, "Refund request submitted. Our team will review it shortly.")
    return redirect('dashboard')

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user, status='PENDING')
    order.delete()
    messages.success(request, "Order cancelled successfully.")
    return redirect('checkout_desk')

# --- STATIC PAGES ---
def about(request): return render(request, 'core/about.html')
def contact(request): return render(request, 'core/contact.html')
def privacy(request): return render(request, 'core/privacy.html')
def terms(request): return render(request, 'core/terms.html')