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

## ~~Management of static files~~ ✅

- `STATICFILES_DIRS` pointait sur `static/images/` (dossier inexistant) → supprimé. Les fichiers statiques de l'app `annuaire` sont découverts automatiquement via `AppDirectoriesFinder`.
- La balise `<script src="js/bootstrap.min.js">` chargeait un fichier inexistant → retirée. Aucun composant Bootstrap 5 JS (`data-bs-*`) n'est utilisé dans les templates.

---

## ~~Tests (priorité basse)~~ ✅

Suite de tests complète en place dans `famille_busson/annuaire/tests/` :
- `test_views_auth.py` — création de compte, authentification
- `test_views_profile.py` — édition de profil restreinte au propriétaire
- `test_views_chalets.py` — chalets, présences, recherche AJAX de personnes
- `test_views_staff.py` — création en masse de comptes
- `test_views_password.py` — middleware de changement forcé de mot de passe
Fixtures partagées dans `conftest.py`. CI sur push via `.github/workflows/tests.yml`.
