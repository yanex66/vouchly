import os
import decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Avg, Count
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.conf import settings
from .models import Item, Category, Review, Profile, Referral, PayoutRequest
from .forms import ReviewForm, UserRegisterForm, ProfileUpdateForm, PayoutRequestForm

# --- 1. Homepage ---
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

# --- 2. Registration & Referrals ---
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

# --- 3. User Dashboard ---
@login_required(login_url='/login/')
def user_dashboard(request):
    profile = request.user.profile
    referral_list = Referral.objects.filter(referrer=request.user).order_by('-created_at')
    ref_paginator = Paginator(referral_list, 5) 
    ref_page_num = request.GET.get('ref_page')
    my_referrals = ref_paginator.get_page(ref_page_num)
    
    payout_list = PayoutRequest.objects.filter(user=request.user).order_by('-created_at')
    pay_paginator = Paginator(payout_list, 5) 
    pay_page_num = request.GET.get('pay_page')
    my_payouts = pay_paginator.get_page(pay_page_num)
    
    vocoin_balance = profile.token_rewards if profile.token_rewards else 0
    lifetime_total = profile.token_rewards + profile.balance
    
    context = {
        'profile': profile,
        'my_referrals': my_referrals, 
        'my_payouts': my_payouts, 
        'vocoin_balance': vocoin_balance,
        'lifetime_total': lifetime_total,
    }
    return render(request, 'core/dashboard.html', context)

# --- 4. Token Redemption ---
@login_required(login_url='/login/')
def redeem_tokens(request):
    profile = request.user.profile
    vocoin_balance = profile.token_rewards if profile.token_rewards else 0
    naira_value = profile.token_rewards 
    
    if request.method == 'POST':
        try:
            amount_str = request.POST.get('amount')
            amount = decimal.Decimal(amount_str) if amount_str else decimal.Decimal(0)
            
            if 0 < amount <= profile.token_rewards:
                profile.token_rewards -= amount
                profile.balance += amount
                profile.save()
                
                PayoutRequest.objects.create(
                    user=request.user, 
                    amount=amount, 
                    status='PAID'
                )
                messages.success(request, f"₦{amount} successfully moved to wallet!")
                return redirect('dashboard')
            else:
                messages.error(request, "Insufficient tokens or invalid amount.")
        except (decimal.InvalidOperation, ValueError):
            messages.error(request, "Invalid input. Please enter a valid amount.")
            
    return render(request, 'core/redeem_tokens.html', {
        'vocoin_balance': vocoin_balance,
        'naira_value': naira_value,
        'form': PayoutRequestForm()
    })

# --- 5. Bank Payout ---
@login_required(login_url='/login/')
def request_payout(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = PayoutRequestForm(request.POST, user_balance=profile.balance)
        if form.is_valid():
            payout = form.save(commit=False)
            payout.user = request.user
            payout.status = 'PENDING'
            
            profile.balance -= payout.amount
            profile.save()
            
            payout.save()
            messages.success(request, "Payout request submitted! Please allow 24-48hrs for processing.")
            return redirect('dashboard')
    else:
        form = PayoutRequestForm(user_balance=profile.balance)
            
    return render(request, 'core/request_payout.html', {'form': form})

# --- 6. Referrals List ---
@login_required(login_url='/login/')
def referrals_page(request):
    profile = request.user.profile
    referral_list = Referral.objects.filter(referrer=request.user).order_by('-created_at')
    paginator = Paginator(referral_list, 5) 
    page_number = request.GET.get('page')
    my_referrals = paginator.get_page(page_number)
    
    context = {
        'my_referrals': my_referrals,
        'vocoin_balance': profile.token_rewards if profile.token_rewards else 0,
        'lifetime_total': profile.token_rewards + profile.balance,
    }
    return render(request, 'core/referrals.html', context)

# --- 7. Items & Reviews ---
def item_detail(request, slug):
    item = get_object_or_404(Item, slug=slug)
    reviews = item.reviews.all().order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
    
    referral_link = ""
    if request.user.is_authenticated:
        base_url = request.build_absolute_uri().split('?')[0]
        referral_link = f"{base_url}?ref={request.user.username}"

    return render(request, 'core/item_detail.html', {
        'item': item, 
        'reviews': reviews, 
        'avg_rating': avg_rating, 
        'form': ReviewForm(),
        'referral_link': referral_link 
    })

@login_required(login_url='/login/')
def add_review(request, slug):
    item = get_object_or_404(Item, slug=slug)
    if Review.objects.filter(item=item, author=request.user).exists():
        messages.warning(request, "Already reviewed!")
        return redirect('item_detail', slug=slug)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.item, review.author = item, request.user
            review.save()
            messages.success(request, "Review submitted!")
    return redirect('item_detail', slug=slug)

# --- 8. Helper Views ---
def search(request):
    query = request.GET.get('query', '')
    results = Item.objects.filter(Q(name__icontains=query) | Q(description__icontains=query)) if query else []
    return render(request, 'core/search_results.html', {'query': query, 'results': results})

def category_list(request):
    return render(request, 'core/category_list.html', {'categories': Category.objects.filter(parent=None)})

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    return render(request, 'core/category_detail.html', {'category': category, 'items': Item.objects.filter(category=category)})

@login_required(login_url='/login/')
def edit_profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated!')
            return redirect('dashboard')
    else:
        form = ProfileUpdateForm(instance=request.user.profile)
    return render(request, 'core/edit_profile.html', {'form': form})

def buy_item(request, slug):
    item = get_object_or_404(Item, slug=slug)
    return HttpResponseRedirect(item.affiliate_link if item.affiliate_link else '/')

@login_required(login_url='/login/')
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, author=request.user)
    if request.method == "POST":
        review.delete()
        messages.success(request, "Review deleted.")
    return redirect('dashboard')

# --- 9. Static Pages ---
def about(request): return render(request, 'core/about.html')
def contact(request): return render(request, 'core/contact.html')
def privacy(request): return render(request, 'core/privacy.html')
def terms(request): return render(request, 'core/terms.html')