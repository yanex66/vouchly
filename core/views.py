import os
import decimal
import requests
import urllib.parse
import random
import time
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.db import models
from django.db.models import Q, Avg, Count, Sum, F
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import login 
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

# 3. HYBRID REVENUE ENGINE
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
        messages.info(request, "Please create a quick account to secure your purchase.")
        return redirect('register')
    
    return redirect(f'/checkout/{slug}/?ref={ref if ref else "DIRECT"}')

@login_required(login_url='/login/')
def product_checkout(request, slug):
    item = get_object_or_404(Item, slug=slug)
    
    ref_code = request.GET.get('ref')
    if not ref_code and 'referrer_ref' in request.session:
        ref_code = request.session['referrer_ref']
    
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
    gateway = request.GET.get('gateway')
    is_success = False
    
    if not reference:
        messages.error(request, "Transaction reference missing.")
        return redirect('dashboard')
    
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
            messages.success(request, "Funds Frozen in Escrow. Seller will now ship.")
            return redirect('checkout_desk')
    
    messages.error(request, "Payment failed verification.")
    return redirect('dashboard')

# --- 4. DELIVERY, SMS & REFUND LOGIC ---

@login_required
def verify_delivery(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(Order, id=order_id, seller=request.user)
        input_pin = request.POST.get('pin')
        
        if order.status == 'COMPLETED':
            messages.warning(request, "Order already completed!")
            return redirect('checkout_desk')

        if input_pin == order.delivery_pin:
            order.status = 'COMPLETED'
            order.is_delivered = True
            order.save()
            
            seller_prof = order.seller.profile
            seller_net_earnings = order.amount - order.commission_earned
            seller_prof.balance += seller_net_earnings
            seller_prof.save()
            
            if order.referrer:
                marketer_prof = order.referrer.profile
                marketer_prof.balance += order.commission_earned
                marketer_prof.save()
            
            messages.success(request, "Success! Funds released to your wallet.")
        else:
            messages.error(request, "Incorrect Code! Please verify with the courier.")
            
    return redirect('checkout_desk')

@login_required
def mark_as_shipped(request, order_id):
    order = get_object_or_404(Order, id=order_id, seller=request.user)
    
    if order.status != 'PAID':
        messages.warning(request, "Order not ready for shipping.")
        return redirect('checkout_desk')

    if not order.delivery_pin:
        order.delivery_pin = str(random.randint(1000, 9999))
    
    order.status = 'SHIPPED'
    order.save()
    
    buyer_phone = order.buyer.profile.whatsapp_number or "0000000000"
    msg = f"Vouchly: Order '{order.item.name}' is on the way! Code: {order.delivery_pin}. Give this to the courier ONLY after receiving the item."
    send_sms_alert(buyer_phone, msg)
    
    messages.success(request, f"Order Shipped! SMS sent to buyer with PIN: {order.delivery_pin}")
    return redirect('checkout_desk')

@login_required
def request_refund(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    
    if order.status not in ['PAID', 'SHIPPED']:
        messages.error(request, "This order cannot be refunded yet.")
        return redirect('checkout_desk')

    if order.refund_deadline and timezone.now() < order.refund_deadline:
        time_left = order.refund_deadline - timezone.now()
        hours = int(time_left.total_seconds() / 3600)
        messages.warning(request, f"Please wait {hours} more hours for delivery before requesting a refund.")
        return redirect('checkout_desk')
    
    order.status = 'REFUNDED'
    order.save()
    
    request.user.profile.balance += order.amount
    request.user.profile.save()
    
    messages.success(request, "Refund Successful! Funds returned to your wallet.")
    return redirect('dashboard')

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user, status='PENDING')
    if request.method == "POST":
        order.delete()
        messages.success(request, "Order request cancelled successfully.")
        return redirect('checkout_desk')
    return redirect('checkout_desk')

# 5. DASHBOARDS
@login_required(login_url='/login/')
def user_dashboard(request):
    profile = request.user.profile
    context = {'profile': profile, 'now': timezone.now()}
    
    if profile.user_type == 'ADVERTISER':
        context['available_balance'] = profile.balance 
        context['balance_label'] = "WALLET BALANCE"
        revenue_data = Order.objects.filter(seller=request.user, status='COMPLETED').aggregate(earnings=Sum(F('amount') - F('commission_earned')))
        context['total_revenue'] = revenue_data['earnings'] or 0
        context['my_sales'] = Order.objects.filter(seller=request.user).order_by('-created_at')
        context['my_products'] = Item.objects.filter(owner=request.user)
        return render(request, 'core/advertiser_dashboard.html', context)
    else:
        context['available_balance'] = profile.balance
        context['balance_label'] = "AVAILABLE BALANCE"
        context['my_purchases'] = Order.objects.filter(buyer=request.user).order_by('-created_at')
        context['referred_orders'] = Order.objects.filter(referrer=request.user).exclude(status='COMPLETED')
        context['my_click_stats'] = ProductReferral.objects.filter(referrer=request.user)
        return render(request, 'core/marketer_dashboard.html', context)

@login_required(login_url='/login/')
def referrals_page(request):
    profile = request.user.profile
    referral_list = Referral.objects.filter(referrer=request.user).order_by('-created_at')
    paginator = Paginator(referral_list, 10)
    my_referrals = paginator.get_page(request.GET.get('page'))
    return render(request, 'core/referrals.html', {'my_referrals': my_referrals, 'profile': profile})

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
    balance = profile.balance 
    if request.method == 'POST':
        form = PayoutRequestForm(request.POST, user_balance=balance)
        if form.is_valid():
            payout = form.save(commit=False)
            payout.user = request.user
            profile.balance -= payout.amount
            profile.save()
            payout.save()
            messages.success(request, "Withdrawal request submitted.")
            return redirect('dashboard')
    else:
        form = PayoutRequestForm(user_balance=balance)
    return render(request, 'core/request_payout.html', {'form': form, 'available_balance': balance})

# 7. AUTHENTICATION & PROFILE
def register(request):
    is_forced_buyer = request.session.get('force_buyer_mode', False)
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save() 
            if is_forced_buyer:
                if hasattr(user, 'profile'):
                    user.profile.user_type = 'BUYER'
                    user.profile.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            next_url = request.session.pop('next_url', None)
            request.session.pop('force_buyer_mode', None)
            if next_url: return redirect(next_url) 
            messages.success(request, 'Account created! Welcome.')
            return redirect('dashboard')
    else:
        form = UserRegisterForm()
    return render(request, 'core/register.html', {'form': form, 'is_forced_buyer': is_forced_buyer})

def set_role_session(request):
    role = request.GET.get('role')
    if role in ['MARKETER', 'ADVERTISER']:
        request.session['pre_selected_role'] = role
        return JsonResponse({'status': 'success', 'role': role})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        post_data = request.POST.copy()
        if post_data.get('whatsapp_number') == 'None':
            post_data['whatsapp_number'] = ''
        form = ProfileUpdateForm(post_data, request.FILES, instance=profile)
        new_email = request.POST.get('email')
        if form.is_valid():
            if new_email:
                request.user.email = new_email
                request.user.save()
            verified_name = request.POST.get('account_name')
            if verified_name: profile.account_name = verified_name
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('edit_profile')
        else:
            for field, errors in form.errors.items():
                for error in errors: messages.error(request, f"{field.replace('_', ' ').upper()}: {error}")
    else:
        form = ProfileUpdateForm(instance=profile)
    return render(request, 'core/edit_profile.html', {'form': form, 'user': request.user})

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
            promo.duration_days = 30
            promo.save()
            return redirect('promotion_payment', pk=promo.pk)
    else:
        form = PromotionRequestForm()
    return render(request, 'core/promote_request.html', {'form': form})

def promotion_payment(request, pk):
    promo = get_object_or_404(PromotionPlan, pk=pk)
    price_setting = SubscriptionPrice.objects.filter(duration_days=promo.duration_days).first()
    return render(request, 'core/promotion_payment.html', {
        'promotion': promo, 
        'amount': float(price_setting.price if price_setting else 500),
        'timestamp': int(time.time()),
        'flw_public_key': settings.FLUTTERWAVE_PUBLIC_KEY, 
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
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
            Item.objects.create(category=promo.category, owner=promo.seller, name=promo.product_name, description=promo.description, image=promo.product_image, price=promo.product_price, commission_naira=(promo.product_price * promo.commission_percentage) / 100, expiry_date=expiry, is_featured=True)
            return redirect('dashboard')
    return redirect('dashboard')

@login_required(login_url='/login/')
def ad_analytics(request):
    my_items = Item.objects.filter(owner=request.user).annotate(total_clicks=Sum('referral_clicks__clicks')).filter(total_clicks__gt=0)
    top_marketers = ProductReferral.objects.filter(item__owner=request.user).values('referrer__username').annotate(total_clicks=Sum('clicks')).order_by('-total_clicks')[:6]
    return render(request, 'core/ad_analytics.html', {'my_items': my_items, 'top_marketers': top_marketers})

# 9. REVIEWS & DETAILS
def item_detail(request, slug):
    item = get_object_or_404(Item, slug=slug)
    related_items = Item.objects.filter(category=item.category).exclude(id=item.id)[:4]
    if item.is_escrow_required:
        ref_link = f"{request.build_absolute_uri('/')[:-1]}/checkout/{item.slug}/?ref={request.user.username}" if request.user.is_authenticated else ""
    else:
        ref_link = f"{request.build_absolute_uri('/')[:-1]}/buy/{item.slug}/?ref={request.user.username}" if request.user.is_authenticated else ""
    avg_rating = item.reviews.aggregate(Avg('rating'))['rating__avg'] or 5.0
    return render(request, 'core/item_detail.html', {'item': item, 'related_items': related_items, 'referral_link': ref_link, 'avg_rating': avg_rating, 'form': ReviewForm()})

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
    num = request.GET.get('account_number')
    bank_code = request.GET.get('bank_code') 
    if not num or not bank_code: return JsonResponse({'status': False, 'message': 'Missing parameters'})
    url = f"https://api.paystack.co/bank/resolve?account_number={num}&bank_code={bank_code}"
    try:
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
        res = requests.get(url, headers=headers, timeout=10).json()
        if res.get('status'): return JsonResponse({'status': True, 'account_name': res['data']['account_name']})
    except: pass
    return JsonResponse({'status': False})

@login_required
def verify_identity(request):
    if request.method == 'POST':
        form = AdvertiserVerificationForm(request.POST, request.FILES)
        if form.is_valid():
            v = form.save(commit=False)
            v.user = request.user
            v.save()
            request.user.profile.verification_status = 'PENDING'
            request.user.profile.save()
            return redirect('dashboard')
    else: form = AdvertiserVerificationForm()
    return render(request, 'core/verify_identity.html', {'form': form})

def search(request):
    q = request.GET.get('query', '')
    results = Item.objects.filter(Q(name__icontains=q) | Q(description__icontains=q))
    return render(request, 'core/marketplace.html', {'items': results, 'query': q})

# --- 11. CHECKOUT DESK ---
@login_required(login_url='/login/')
def checkout_desk(request):
    my_orders = Order.objects.filter(buyer=request.user).order_by('-created_at')
    incoming_orders = Order.objects.filter(seller=request.user).exclude(status='PENDING').annotate(seller_earning=F('amount') - F('commission_earned')).order_by('-created_at')
    return render(request, 'core/checkout_desk.html', {'my_orders': my_orders, 'incoming_orders': incoming_orders})

def payment_success(request, pk): return render(request, 'core/payment_success.html', {'pk': pk})
def about(request): return render(request, 'core/about.html', {'is_authenticated': request.user.is_authenticated})
def contact(request): return render(request, 'core/contact.html')
def privacy(request): return render(request, 'core/privacy.html')
def terms(request): return render(request, 'core/terms.html')

# --- 12. BULK CATEGORY UPLOAD ---
def bulk_add_categories(request):
    if not request.user.is_superuser: return HttpResponse("Unauthorized", status=401)
    category_names = ["Digital Courses", "AI & Automation Tools", "E-books & Guides", "Software & Subscriptions", "Smartphones & Tablets", "Computers & Laptops", "Gadgets & Wearables", "Gaming & Consoles", "Men's Fashion", "Women's Fashion", "Health & Wellness", "Beauty & Skincare", "Marketing & Advertising", "Freelance Services", "Business Consulting", "Real Estate & Housing", "Home & Kitchen", "Automobiles & Parts", "Crypto & Finance", "Data & Airtime", "Gift Cards", "Job Opportunities", "Events & Tickets", "Travel & Tourism", "Agriculture & Farm", "Education & Scholarships", "Food & Groceries", "Interior Design", "Photography & Video", "Others"]
    categories_to_create = [Category(name=name, slug=slugify(name)) for name in category_names]
    Category.objects.bulk_create(categories_to_create, ignore_conflicts=True)
    return HttpResponse(f"<h1>Success!</h1><p>Successfully added {len(category_names)} categories to Vouchly.</p>")