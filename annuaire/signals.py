from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from .models import Account, Person, Relation


@receiver(post_save, sender=Account)
def link_account_to_person(sender, instance, created, **kwargs):
    if created:
        try:
            person = Person.objects.get(email=instance.email)
            person.account = instance
            person.save()
        except Person.DoesNotExist:
            pass


@receiver(post_save, sender=Relation)
def create_inverse_relation(sender, instance: Relation, created, **kwargs):
    person1 = instance.person1
    person2 = instance.person2
    relationship_type = instance.relationship_type
    inverse_type = relationship_type if relationship_type in [0, 1] else 5 - relationship_type
    inverse_start_date = instance.start_date if relationship_type in [0, 1] else None
    try:
        inverse = Relation.objects.get(person1=person2, person2=person1)
        if inverse.relationship_type != inverse_type or inverse.start_date != inverse_start_date:
            inverse.relationship_type = inverse_type
            inverse.start_date = inverse_start_date
            inverse.save()
    except Relation.DoesNotExist:
        inverse = Relation.objects.create(
            person1=person2,
            person2=person1,
            relationship_type=inverse_type,
            start_date=inverse_start_date,
        )
        inverse.save()


@receiver(post_delete, sender=Relation)
def delete_inverse_relation(sender, instance: Relation, **kwargs):
    Relation.objects.filter(
        person1=instance.person2, person2=instance.person1
    ).delete()
