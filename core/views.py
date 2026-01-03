from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Avg, F, Count
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from .models import Item, Category, Review, Profile, Referral, PayoutRequest
from .forms import ReviewForm, UserRegisterForm, ProfileUpdateForm, PayoutRequestForm

# 1. Homepage (UPDATED with Featured Review)
def home(request):
    hero_items = Item.objects.filter(is_featured=True)
    
    top_rated = Item.objects.annotate(
        avg_rating=Avg('reviews__rating')
    ).order_by('-avg_rating')[:4]
    
    latest_items = Item.objects.order_by('-created_at')[:4]

    featured_reviewers = User.objects.annotate(
        num_reviews=Count('reviews')
    ).filter(num_reviews__gt=0).order_by('-num_reviews')[:4]

    # LOGIC FOR REVIEW OF THE WEEK
    featured_review = Review.objects.filter(is_featured=True).first()
    
    context = {
        'hero_items': hero_items,
        'top_rated': top_rated,
        'latest_items': latest_items,
        'featured_reviewers': featured_reviewers,
        'featured_review': featured_review, # Added this
    }
    return render(request, 'core/home.html', context)

# 2. Item Detail Page
def item_detail(request, slug):
    item = get_object_or_404(Item, slug=slug)
    reviews = item.reviews.all().order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
    form = ReviewForm() 
    
    referral_link = None
    if request.user.is_authenticated:
        referral_link = request.build_absolute_uri(f"/buy/{item.slug}/?ref={request.user.username}")
    
    context = {
        'item': item,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'form': form,
        'referral_link': referral_link,
    }
    return render(request, 'core/item_detail.html', context)

# 3. Add Review Logic
@login_required(login_url='/login/')
def add_review(request, slug):
    item = get_object_or_404(Item, slug=slug)
    already_reviewed = Review.objects.filter(item=item, author=request.user).exists()
    
    if already_reviewed:
        messages.warning(request, "You have already reviewed this product!")
        return redirect('item_detail', slug=slug)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.item = item
            review.author = request.user
            review.save()
            messages.success(request, "Review submitted successfully!") 
            return redirect('item_detail', slug=slug)
            
    return redirect('item_detail', slug=slug)

# 4. Search Logic
def search(request):
    query = request.GET.get('query', '')
    results = Item.objects.filter(
        Q(name__icontains=query) | 
        Q(description__icontains=query) |
        Q(category__name__icontains=query)
    ) if query else []
    
    return render(request, 'core/search_results.html', {'query': query, 'results': results})

# 5. User Dashboard
@login_required(login_url='/login/')
def user_dashboard(request):
    user_reviews = Review.objects.filter(author=request.user).order_by('-created_at')
    my_referrals = Referral.objects.filter(referrer=request.user)
    my_payouts = PayoutRequest.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'user_reviews': user_reviews,
        'my_referrals': my_referrals,
        'my_payouts': my_payouts, 
    }
    return render(request, 'core/dashboard.html', context)

# 6. Delete Review Logic
@login_required(login_url='/login/')
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, author=request.user)
    if request.method == "POST":
        review.delete()
        messages.success(request, "Review deleted successfully.")
    return redirect('dashboard')

# 7. Category List
def category_list(request):
    categories = Category.objects.filter(parent=None)
    return render(request, 'core/category_list.html', {'categories': categories})

# 8. Category Detail
def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    items = Item.objects.filter(category=category)
    return render(request, 'core/category_detail.html', {'category': category, 'items': items})

# 9. Register Logic
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now login.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'core/register.html', {'form': form})

# 10. Edit Profile Logic
@login_required(login_url='/login/')
def edit_profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('dashboard')
    else:
        form = ProfileUpdateForm(instance=request.user.profile)
    return render(request, 'core/edit_profile.html', {'form': form})

# 11. Buy Item Redirect
def buy_item(request, slug):
    item = get_object_or_404(Item, slug=slug)
    ref_username = request.GET.get('ref')
    if ref_username:
        try:
            referrer_user = User.objects.get(username=ref_username)
            if referrer_user != request.user:
                referral, created = Referral.objects.get_or_create(referrer=referrer_user, item=item)
                referral.clicks = F('clicks') + 1
                referral.save()
        except User.DoesNotExist:
            pass
    destination = item.affiliate_link if item.affiliate_link else '/'
    return HttpResponseRedirect(destination)

# 12. Request Payout Logic
@login_required(login_url='/login/')
def request_payout(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = PayoutRequestForm(request.POST, user_balance=profile.earnings)
        if form.is_valid():
            payout = form.save(commit=False)
            payout.user = request.user
            profile.earnings -= payout.amount
            profile.saved_bank_name = payout.bank_name
            profile.saved_account_name = payout.account_name
            profile.saved_account_number = payout.account_number
            profile.save() 
            payout.save()
            messages.success(request, "Payout request submitted! Your details have been saved.")
            return redirect('dashboard')
    else:
        initial_data = {
            'bank_name': profile.saved_bank_name,
            'account_name': profile.saved_account_name,
            'account_number': profile.saved_account_number,
        }
        form = PayoutRequestForm(user_balance=profile.earnings, initial=initial_data)
    return render(request, 'core/request_payout.html', {'form': form})

# 13. Static Pages
def about(request):
    return render(request, 'core/about.html')

def contact(request):
    return render(request, 'core/contact.html')

def privacy(request):
    return render(request, 'core/privacy.html')

def terms(request):
    return render(request, 'core/terms.html')