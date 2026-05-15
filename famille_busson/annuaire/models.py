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
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    groups = models.ManyToManyField(Group, related_name='account_set', blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name='account_set', blank=True)
    objects = AccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class Person(models.Model):
    last_name = models.CharField(max_length=100, verbose_name='Nom')
    account = models.OneToOneField(Account, related_name='profile', on_delete=models.SET_NULL, blank=True, null=True)
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

    person1 = models.ForeignKey('Person', related_name='ascending_relations', on_delete=models.CASCADE)
    person2 = models.ForeignKey('Person', related_name='descending_relations', on_delete=models.CASCADE)
    relationship_type = models.IntegerField(choices=RELATION_CHOICES)
    start_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.person1} -> {self.get_relationship_type_display()} -> {self.person2}"


class Chalet(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    gps_coordinates = models.CharField(max_length=100, blank=True, null=True)
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)

    def __str__(self):
        return self.name


class PresencePSV(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    chalet = models.ForeignKey(Chalet, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.person} - {self.chalet} du {self.start_date} au {self.end_date}"
