from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission


# Compte utilisateur
class CompteManager(BaseUserManager):
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

class Compte(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    groups = models.ManyToManyField(Group, related_name='compte_set', blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name='compte_set', blank=True)
    objects = CompteManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


# Profil de personne
class Personne(models.Model):
    nom = models.CharField(max_length=100, verbose_name='Nom')
    compte = models.OneToOneField(Compte, related_name='profil', on_delete=models.DO_NOTHING, blank=True, null=True)
    prenom = models.CharField(max_length=100, verbose_name='Prénom')
    email = models.EmailField(blank=True, null=True, verbose_name='Adresse électronique')
    photo_profil = models.ImageField(upload_to='photos/', blank=True, null=True, verbose_name='Photo de profil')
    adresse_postale = models.CharField(max_length=255, blank=True, null=True, verbose_name='Adresse postale')
    numero_telephone = models.CharField(max_length=25, blank=True, null=True, verbose_name='Numéro de téléphone')
    date_naissance = models.DateField(blank=True, null=True, verbose_name='Date de naissance')
    description = models.TextField(blank=True, null=True, verbose_name='Infos utiles')

    def __str__(self):
        return f"{self.prenom} {self.nom}"


class Relation(models.Model):
    RELATION_CHOICES = [
        (0, 'mariage'),
        (1, 'conjoint'),
        (2, 'parent'),
        (3, 'enfant'),
    ]

    personne1 = models.ForeignKey('Personne', related_name='relations_montantes', on_delete=models.CASCADE)
    personne2 = models.ForeignKey('Personne', related_name='relations_descendantes', on_delete=models.CASCADE)
    nature_relation = models.IntegerField(choices=RELATION_CHOICES)
    date_debut = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.personne1} -> {self.get_nature_relation_display()} -> {self.personne2}"
    
    


class Chalet(models.Model):
    nom = models.CharField(max_length=100)
    adresse = models.CharField(max_length=255)
    coordonnees_gps = models.CharField(max_length=100, blank=True, null=True)
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)

    def __str__(self):
        return self.nom


class PresencePSV(models.Model):
    personne = models.ForeignKey(Personne, on_delete=models.CASCADE)
    chalet = models.ForeignKey(Chalet, on_delete=models.CASCADE)
    date_debut = models.DateField()
    date_fin = models.DateField()

    def __str__(self):
        return f"{self.personne} - {self.chalet} du {self.date_debut} au {self.date_fin}"
