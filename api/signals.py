from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone

@receiver(user_logged_in)
def update_last_login(sender, user, **kwargs):
    """
    A signal receiver that updates the last_login field for a user when they log in.
    """
    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])