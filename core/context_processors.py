from .models import Order

def pending_orders_count(request):
    if request.user.is_authenticated:
        count = Order.objects.filter(buyer=request.user, status='PENDING').count()
        return {'pending_count': count}
    return {'pending_count': 0}