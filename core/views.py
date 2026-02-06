import os
import decimal
import requests
import urllib.parse
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.db import models
from django.db.models import Q, Avg, Count, Sum, F
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.conf import settings
from django.utils import timezone

# Model and Form Imports
from .models import (
    Item, Category, Review, Profile, Referral, 
    PayoutRequest, ProductReferral, ChatMessage, PromotionPlan,
    AdvertiserVerification, SubscriptionPrice
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
        'featured_reviewers': featured_reviewers,
        'featured_review': featured_review,
    }
    return render(request, 'core/home.html', context)

# 2. AUTHENTICATION & PROFILE MANAGEMENT
def set_role_session(request):
    role = request.GET.get('role')
    if role in ['MARKETER', 'ADVERTISER']:
        request.session['pre_selected_role'] = role
        return JsonResponse({'status': 'success', 'role': role})
    return JsonResponse({'status': 'error'}, status=400)

def register(request):
    ref_username = request.GET.get('ref')
    if ref_username:
        request.session['referrer'] = ref_username
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            referrer_name = request.session.get('referrer')
            if referrer_name:
                try:
                    referrer = User.objects.get(username=referrer_name)
                    Referral.objects.create(referrer=referrer, referred_user=new_user)
                    profile = referrer.profile
                    profile.token_rewards += 100
                    profile.save()
                    del request.session['referrer']
                except User.DoesNotExist:
                    pass
            messages.success(request, 'Account created! Please login.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'core/register.html', {'form': form})

@login_required(login_url='/login/')
def edit_profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile settings have been updated!')
            return redirect('edit_profile')
    else:
        form = ProfileUpdateForm(instance=request.user.profile)
    return render(request, 'core/edit_profile.html', {'form': form})

# 3. REVENUE ENGINE: REDIRECTION & TRACKING
@login_required(login_url='/login/')
def buy_item(request, slug):
    item = get_object_or_404(Item, slug=slug)
    ref_code = request.GET.get('ref', 'DIRECT')
    if ref_code != 'DIRECT':
        try:
            referrer = User.objects.get(username=ref_code)
            pr, _ = ProductReferral.objects.get_or_create(referrer=referrer, item=item)
            pr.clicks += 1
            pr.save()
            referrer.profile.token_rewards += item.commission_naira
            referrer.profile.save()
        except User.DoesNotExist:
            pass
    if item.whatsapp_number:
        base_msg = f"Hello! I am interested in buying '{item.name}'.\n\nReferral Code: {ref_code}"
        encoded_msg = urllib.parse.quote(base_msg)
        target_url = f"https://wa.me/{item.whatsapp_number}?text={encoded_msg}"
    elif item.website:
        target_url = item.website
    else:
        messages.warning(request, "No contact destination set.")
        target_url = '/'
    return HttpResponseRedirect(target_url)

# 4. ADVERTISER WORKFLOW & SUBSCRIPTIONS
@login_required(login_url='/login/')
def promote_request(request):
    if request.user.profile.user_type != 'ADVERTISER':
        return redirect('dashboard')
    
    if request.user.profile.verification_status != 'VERIFIED':
        messages.warning(request, "Please verify your identity before listing products.")
        return redirect('verify_identity')

    active_sub = PromotionPlan.objects.filter(seller=request.user, is_paid=True, subscription_expiry__gt=timezone.now()).last()
    if request.method == 'POST':
        form = PromotionRequestForm(request.POST, request.FILES)
        if form.is_valid():
            promo = form.save(commit=False)
            promo.seller = request.user
            dest_type = request.POST.get('destination_type', 'whatsapp')
            website_url = request.POST.get('website_url', '')
            
            # Use 0 if commission percentage is not provided
            commission_perc = form.cleaned_data.get('commission_percentage', 0)
            
            if active_sub:
                promo.is_paid, promo.subscription_expiry = True, active_sub.subscription_expiry
                promo.save()
                Item.objects.create(
                    category=promo.category, owner=promo.seller, name=promo.product_name,
                    description=promo.description, image=promo.product_image, price=promo.product_price,
                    commission_naira=(promo.product_price * commission_perc) / 100,
                    expiry_date=active_sub.subscription_expiry, is_featured=True,
                    whatsapp_number=request.user.profile.whatsapp_number if dest_type == 'whatsapp' else None,
                    website=website_url if dest_type == 'website' else None
                )
                return redirect('dashboard')
            else:
                promo.save()
                request.session['pending_dest_type'], request.session['pending_website'] = dest_type, website_url
                return redirect('promotion_payment', pk=promo.pk)
    else:
        form = PromotionRequestForm(initial={'commission_percentage': 0})
    return render(request, 'core/promote_request.html', {'form': form, 'active_sub': active_sub})

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
            
            # Referral Bonus logic
            try:
                referral = Referral.objects.get(referred_user=promo.seller)
                referrer_profile = referral.referrer.profile
                price_setting = SubscriptionPrice.objects.filter(duration_days=promo.duration_days).first()
                sub_price = price_setting.price if price_setting else 0
                reward = (sub_price * 10) / 100 
                referrer_profile.token_rewards += reward
                referrer_profile.save()
            except Referral.DoesNotExist:
                pass
            
            # Listing activation
            Item.objects.create(
                category=promo.category, owner=promo.seller, name=promo.product_name,
                description=promo.description, image=promo.product_image, price=promo.product_price,
                commission_naira=(promo.product_price * promo.commission_percentage) / 100,
                expiry_date=expiry, is_featured=True,
                whatsapp_number=promo.seller.profile.whatsapp_number if request.session.get('pending_dest_type') == 'whatsapp' else None,
                website=request.session.get('pending_website') if request.session.get('pending_dest_type') == 'website' else None
            )
            messages.success(request, "Payment Verified! Ad is now live.")
            return redirect('dashboard')
    
    messages.error(request, "Payment verification failed.")
    return redirect('dashboard')

# 5. DASHBOARDS & ANALYTICS
@login_required(login_url='/login/')
def user_dashboard(request):
    profile = request.user.profile
    payout_list = PayoutRequest.objects.filter(user=request.user).order_by('-created_at')
    my_payouts = Paginator(payout_list, 5).get_page(request.GET.get('pay_page'))
    
    available_balance = profile.token_rewards if profile.user_type == 'ADVERTISER' else profile.balance
    balance_label = "VOCOIN REWARDS" if profile.user_type == 'ADVERTISER' else "AVAILABLE BALANCE"

    context = {
        'profile': profile, 'my_payouts': my_payouts, 
        'available_balance': available_balance, 
        'balance_label': balance_label,
        'vocoin_balance': profile.token_rewards or 0,
        'lifetime_total': (profile.token_rewards or 0) + (profile.balance or 0),
        'now': timezone.now(),
    }
    
    if profile.user_type == 'ADVERTISER':
        my_products = Item.objects.filter(owner=request.user).annotate(
            total_clicks=Sum('referral_clicks__clicks'),
            total_spent=Sum(F('referral_clicks__clicks') * F('commission_naira'))
        ).order_by('-created_at')
        context.update({'my_products': my_products})
        return render(request, 'core/advertiser_dashboard.html', context)
    else:
        my_click_stats = ProductReferral.objects.filter(referrer=request.user).order_by('-last_click')
        context.update({'my_click_stats': my_click_stats})
        return render(request, 'core/marketer_dashboard.html', context)

@login_required(login_url='/login/')
def referrals_page(request):
    profile = request.user.profile
    referral_list = Referral.objects.filter(referrer=request.user).order_by('-created_at')
    my_referrals = Paginator(referral_list, 10).get_page(request.GET.get('page'))
    
    context = {
        'my_referrals': my_referrals,
        'vocoin_balance': profile.token_rewards or 0,
        'lifetime_total': (profile.token_rewards or 0) + (profile.balance or 0),
        'profile': profile
    }
    return render(request, 'core/referrals.html', context)

@login_required(login_url='/login/')
def ad_analytics(request):
    my_items = Item.objects.filter(owner=request.user).annotate(
        total_clicks=Sum('referral_clicks__clicks')
    ).filter(total_clicks__gt=0)
    
    top_marketers = ProductReferral.objects.filter(item__owner=request.user).values(
        'referrer__username'
    ).annotate(total_clicks=Sum('clicks')).order_by('-total_clicks')[:6]
    
    return render(request, 'core/ad_analytics.html', {
        'my_items': my_items, 
        'top_marketers': top_marketers
    })

# 6. WALLET & PAYOUTS
@login_required(login_url='/login/')
def redeem_tokens(request):
    profile = request.user.profile
    if request.method == 'POST':
        raw_amount = request.POST.get('amount', '').strip()
        if not raw_amount:
            messages.error(request, "PLEASE ENTER A VALID AMOUNT.")
            return redirect('redeem_tokens')
            
        try:
            amount = decimal.Decimal(raw_amount)
            if 0 < amount <= profile.token_rewards:
                profile.token_rewards -= amount
                profile.balance += amount
                profile.save()
                PayoutRequest.objects.create(user=request.user, amount=amount, status='PAID')
                messages.success(request, f"₦{amount:,.2f} HAS BEEN REDEEMED TO YOUR WALLET!")
                return redirect('dashboard')
            else:
                messages.error(request, "INSUFFICIENT VOCOIN BALANCE OR INVALID AMOUNT.")
        except decimal.InvalidOperation:
            messages.error(request, "INVALID NUMERIC VALUE PROVIDED.")
            
    return render(request, 'core/redeem_tokens.html', {'vocoin_balance': profile.token_rewards})

@login_required(login_url='/login/')
def request_payout(request):
    profile = request.user.profile
    available_balance = profile.token_rewards if profile.user_type == 'ADVERTISER' else profile.balance
    balance_label = "VOCOIN REWARDS" if profile.user_type == 'ADVERTISER' else "AVAILABLE BALANCE"

    if request.method == 'POST':
        form = PayoutRequestForm(request.POST, user_balance=available_balance)
        if form.is_valid():
            payout = form.save(commit=False)
            payout.user = request.user
            if profile.user_type == 'ADVERTISER':
                profile.token_rewards -= payout.amount
            else:
                profile.balance -= payout.amount
            profile.save()
            payout.save()
            messages.success(request, "Request sent! Expect withdrawal within 24hrs.")
            return redirect('dashboard')
    else:
        form = PayoutRequestForm(user_balance=available_balance)
        
    return render(request, 'core/request_payout.html', {
        'form': form, 'available_balance': available_balance, 'balance_label': balance_label
    })

# 7. REVIEWS & NAVIGATION
@login_required
def add_review(request, slug):
    item = get_object_or_404(Item, slug=slug)
    if not Review.objects.filter(item=item, author=request.user).exists() and request.method == 'POST':
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

def item_detail(request, slug):
    item = get_object_or_404(Item, slug=slug)
    referral_link = f"{request.build_absolute_uri('/')[:-1]}/buy/{item.slug}/?ref={request.user.username}" if request.user.is_authenticated else ""
    return render(request, 'core/item_detail.html', {'item': item, 'referral_link': referral_link, 'form': ReviewForm()})

def category_list(request):
    return render(request, 'core/category_list.html', {'categories': Category.objects.filter(parent=None)})

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    return render(request, 'core/category_detail.html', {'category': category, 'items': Item.objects.filter(category=category)})

# 8. BANK VERIFICATION & SYSTEM UTILS
@login_required
def verify_bank_account(request):
    num = request.GET.get('account_number')
    slug = request.GET.get('bank_slug')
    mapping = {
        'access': '044', 'ecobank': '050', 'fidelity': '070', 'firstbank': '011',
        'fcmb': '214', 'gtbank': '058', 'heritage': '030', 'keystone': '082',
        'kuda': '999109', 'moniepoint': '50515', 'opay': '999992', 'palmpay': '999991',
        'uba': '033', 'unity': '011', 'wema': '035', 'zenith': '057',
    }
    url = f"https://api.paystack.co/bank/resolve?account_number={num}&bank_code={mapping.get(slug)}"
    try:
        res = requests.get(url, headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}).json()
        if res.get('status'): return JsonResponse({'status': True, 'account_name': res['data']['account_name']})
        return JsonResponse({'status': False, 'message': res.get('message')})
    except: return JsonResponse({'status': False, 'message': 'Error'})

def promotion_payment(request, pk):
    promo = get_object_or_404(PromotionPlan, pk=pk)
    price_setting = SubscriptionPrice.objects.filter(duration_days=promo.duration_days).first()
    amount = price_setting.price if price_setting else 500
    
    # TERMINAL DEBUG
    print("\n" + "="*60)
    print("DEBUG: LOADING PROMOTION PAYMENT PAGE")
    print(f"Key in Context: {settings.FLUTTERWAVE_PUBLIC_KEY}")
    print("="*60 + "\n")
        
    return render(request, 'core/promotion_payment.html', {
        'promotion': promo, 
        'amount': amount,
        'flw_public_key': settings.FLUTTERWAVE_PUBLIC_KEY, 
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
        'user_email': request.user.email
    })

# 9. IDENTITY VERIFICATION
@login_required(login_url='/login/')
def verify_identity(request):
    profile = request.user.profile
    if profile.user_type != 'ADVERTISER' or profile.verification_status in ['PENDING', 'VERIFIED']:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AdvertiserVerificationForm(request.POST, request.FILES)
        if form.is_valid():
            verification = form.save(commit=False)
            verification.user = request.user
            verification.save()
            profile.verification_status = 'PENDING'
            profile.save()
            messages.success(request, "Documents submitted! Review pending.")
            return redirect('dashboard')
    else:
        existing = AdvertiserVerification.objects.filter(user=request.user).first()
        form = AdvertiserVerificationForm(instance=existing)

    return render(request, 'core/verify_identity.html', {'form': form})

# OTHERS
def search(request):
    q = request.GET.get('query', '')
    results = Item.objects.filter(Q(name__icontains=q) | Q(description__icontains=q))
    return render(request, 'core/search_results.html', {'results': results, 'query': q})

def payment_success(request, pk): return render(request, 'core/payment_success.html', {'item': get_object_or_404(Item, pk=pk)})
def about(request): return render(request, 'core/about.html')
def contact(request): return render(request, 'core/contact.html')
def privacy(request): return render(request, 'core/privacy.html')
def terms(request): return render(request, 'core/terms.html')