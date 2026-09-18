from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        instance.profile
    except ObjectDoesNotExist:
        Profile.objects.create(
            user=instance,
            name=instance.first_name or instance.username,
            phone="",
        )
