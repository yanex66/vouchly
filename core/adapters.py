from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User
from allauth.account.utils import perform_login

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a social provider, 
        but before the login is actually processed.
        """
        # 1. Skip if the social account is already connected to a user
        if sociallogin.is_existing:
            return

        # 2. Check if we have an existing user with the same email
        email = sociallogin.account.extra_data.get('email')
        if not email:
            return

        try:
            # 3. Find the existing user
            user = User.objects.get(email=email)
            
            # 4. Link the social account to the existing user
            sociallogin.connect(request, user)
            
            # 5. Log the user in
            return perform_login(request, user, email_verification='none')
            
        except User.DoesNotExist:
            # No existing user found, allow standard signup flow to continue
            pass