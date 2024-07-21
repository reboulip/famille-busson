from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Compte, Personne

@receiver(post_save, sender=Compte)
def associer_personne(sender, instance, created, **kwargs):
    if created:
        try:
            personne = Personne.objects.get(email=instance.email)
            personne.compte = instance
            personne.save()
        except Personne.DoesNotExist:
            pass
