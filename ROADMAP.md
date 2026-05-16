# Roadmap — Famille Busson

## Fonctionnalités manquantes (priorité haute)

### ~~Vue liste / recherche de l'annuaire~~ ✅
Implémentée : `VueListeAnnuaire`, template `annuaire_list.html`, URL `/annuaire/`, barre de recherche nom/prénom.

### ~~Navigation sidebar~~ ✅
Sidebar mise à jour avec les vraies URLs (Annuaire, Chalets PSV). Section Publications retirée.

### ~~Chalets~~ ✅
Implémentés : `VueListeChalets` + `VueDetailChalet`, templates `chalet_list.html` et `chalet_detail.html`, URLs `/chalets/` et `/chalets/<pk>/`.

### ~~Présences PSV~~ ✅
Implémentées : `VueAjouterPresence`, `VueModifierPresence`, `VueSupprimerPresence`, formulaire `FormPresencePSV`, template `presence_form.html`.

### ~~Page d'accueil~~ ✅
Page d'accueil refaite avec une grille de tuiles extensible : tuile annuaire (6 derniers profils ajoutés), tuile châlets. Structure prête pour ajouter de nouvelles tuiles.

---

## ~~Bugs à corriger (priorité haute)~~ ✅

### ~~`HttpResponseForbidden` mal utilisé~~ ✅
- `SignupView.form_valid()` : remplacé par `messages.error` + `form_invalid`
- `VueEditionProfil.get_object()` : remplacé par `raise PermissionDenied`

---

## ~~Migration Bootstrap 4 → Bootstrap 5~~ ✅

`crispy_forms` est actuellement configuré avec le pack `crispy_bootstrap4` (`CRISPY_TEMPLATE_PACK = 'bootstrap4'`), alors que le projet cible Bootstrap 5.

Étapes :
- Remplacer `crispy-bootstrap4` par `crispy-bootstrap5` (`uv add crispy-bootstrap5 && uv remove crispy-bootstrap4`)
- Mettre à jour `INSTALLED_APPS` : remplacer `crispy_bootstrap4` par `crispy_bootstrap5`
- Mettre à jour `CRISPY_TEMPLATE_PACK = 'bootstrap5'`
- Vérifier les templates pour les classes ou structures spécifiques à Bootstrap 4 (ex. `form-row` → `row`, `custom-select` → `form-select`, etc.)

---

## Nettoyage (priorité moyenne)

### ~~Print statements de debug~~ ✅
Les 5 `print()` ont été supprimés de `views.py`.

### ~~Import inutilisé~~ ✅
`from django.contrib.auth.models import User` supprimé de `forms.py`.

---

## Configuration production (priorité moyenne)

- Sortir `SECRET_KEY` du code source et la mettre dans une variable d'environnement
- Passer `DEBUG = False` et configurer `ALLOWED_HOSTS` pour la production
- Créer un fichier `.env.example` documentant les variables requises

---

## Tests (priorité basse)

`tests.py` est vide. Fonctionnalités à couvrir en priorité :
- Création de compte (vérification de l'email pré-existant)
- Authentification
- Édition de profil (accès restreint au propriétaire)
- Signaux de création des relations inverses
