from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Compte, Personne, Relation

@receiver(post_save, sender=Compte)
def associer_personne(sender, instance, created, **kwargs):
    if created:
        try:
            personne = Personne.objects.get(email=instance.email)
            personne.compte = instance
            personne.save()
        except Personne.DoesNotExist:
            pass


@receiver(post_save, sender=Relation)
def relation_inverse(sender, instance: Relation, created, **kwargs):
    personne1 = instance.personne1
    personne2 = instance.personne2
    nature_relation = instance.nature_relation
    nature_relation_inverse = nature_relation if nature_relation in [0, 1] else 5 - nature_relation
    date_debut_relation_inverse = instance.date_debut if nature_relation in [0, 1] else None
    try:
        relation_inverse = Relation.objects.get(personne1=personne2, personne2=personne1)
        if relation_inverse.nature_relation != nature_relation_inverse or relation_inverse.date_debut != date_debut_relation_inverse:
            relation_inverse.nature_relation = nature_relation_inverse
            relation_inverse.date_debut = date_debut_relation_inverse
            relation_inverse.save()
    except Relation.DoesNotExist:
        relation_inverse = Relation.objects.create(
            personne1=personne2,
            personne2=personne1,
            nature_relation=nature_relation_inverse,
            date_debut=date_debut_relation_inverse
        )
        relation_inverse.save()
