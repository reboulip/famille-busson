from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission


class AccountManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('L\'adresse email est obligatoire')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)


class Account(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name='Adresse email')
    is_active = models.BooleanField(default=True, verbose_name='Actif')
    is_staff = models.BooleanField(default=False, verbose_name='Membre du personnel')
    must_change_password = models.BooleanField(default=False, verbose_name='Doit changer le mot de passe')
    groups = models.ManyToManyField(Group, related_name='account_set', blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name='account_set', blank=True)
    objects = AccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class Person(models.Model):
    last_name = models.CharField(max_length=100, verbose_name='Nom')
    account = models.OneToOneField(Account, related_name='profile', on_delete=models.SET_NULL, blank=True, null=True, verbose_name='Compte')
    first_name = models.CharField(max_length=100, verbose_name='Prénom')
    email = models.EmailField(blank=True, null=True, verbose_name='Adresse électronique')
    profile_photo = models.ImageField(upload_to='photos/', blank=True, null=True, verbose_name='Photo de profil')
    postal_address = models.CharField(max_length=255, blank=True, null=True, verbose_name='Adresse postale')
    phone_number = models.CharField(max_length=25, blank=True, null=True, verbose_name='Numéro de téléphone')
    birth_date = models.DateField(blank=True, null=True, verbose_name='Date de naissance')
    description = models.TextField(blank=True, null=True, verbose_name='Infos utiles')

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Relation(models.Model):
    RELATION_CHOICES = [
        (0, 'mariage'),
        (1, 'conjoint'),
        (2, 'parent'),
        (3, 'enfant'),
    ]

    person1 = models.ForeignKey('Person', related_name='ascending_relations', on_delete=models.CASCADE, verbose_name='Personne')
    person2 = models.ForeignKey('Person', related_name='descending_relations', on_delete=models.CASCADE, verbose_name='En relation avec')
    relationship_type = models.IntegerField(choices=RELATION_CHOICES, verbose_name='Type de relation')
    start_date = models.DateField(blank=True, null=True, verbose_name='Date de début')

    def __str__(self):
        return f"{self.person1} -> {self.get_relationship_type_display()} -> {self.person2}"


class Chalet(models.Model):
    name = models.CharField(max_length=100, verbose_name='Nom')
    address = models.CharField(max_length=255, verbose_name='Adresse')
    gps_coordinates = models.CharField(max_length=100, blank=True, null=True, verbose_name='Coordonnées GPS')
    photo = models.ImageField(upload_to='photos/', blank=True, null=True, verbose_name='Photo')
    owners = models.ManyToManyField(
        'Person', related_name='owned_chalets', blank=True, verbose_name='Propriétaires'
    )

    def __str__(self):
        return self.name


class PresencePSV(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE, verbose_name='Personne')
    chalet = models.ForeignKey(Chalet, on_delete=models.CASCADE, verbose_name='Chalet')
    start_date = models.DateField(verbose_name="Date d'arrivée")
    end_date = models.DateField(verbose_name='Date de départ')

    def __str__(self):
        return f"{self.person} - {self.chalet} du {self.start_date} au {self.end_date}"
