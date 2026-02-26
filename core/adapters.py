from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User
from allauth.account.utils import perform_login
from .models import Profile  # Import Profile to update the role

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

    def save_user(self, request, sociallogin, form=None):
        """
        Invoked when a NEW user is being created via Google.
        We intercept this to assign the 'Advertiser' or 'Marketer' role
        based on what they clicked on the signup page.
        """
        # 1. Let allauth create the User object first
        user = super().save_user(request, sociallogin, form)

        # 2. Retrieve the role from the session (set by your JS fetch call)
        selected_role = request.session.get('pre_selected_role')

        # 3. Update the Profile
        # Note: Your post_save signal in models.py creates the profile automatically.
        # We just need to update the user_type.
        if selected_role in ['MARKETER', 'ADVERTISER']:
            if hasattr(user, 'profile'):
                user.profile.user_type = selected_role
                user.profile.save()
            else:
                # Fallback: Create profile if signal failed for some reason
                Profile.objects.create(user=user, user_type=selected_role)
        
        return user