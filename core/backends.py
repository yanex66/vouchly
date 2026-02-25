from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # We use filter().first() instead of get() to prevent the MultipleObjectsReturned error
            user = User.objects.filter(Q(username=username) | Q(email=username)).first()
        except User.DoesNotExist:
            return None

        if user and user.check_password(password):
            return user
        return None