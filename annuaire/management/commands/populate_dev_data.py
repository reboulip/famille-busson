"""Populate the database with realistic fake data for local development.

Usage (from the repo root):
    uv run python manage.py populate_dev_data

By default the command wipes existing data from the affected models before
recreating it. Pass --no-clear to append instead.

Every created Account uses the password "dev" (must_change_password=False),
plus a superuser admin@example.com / admin for the Django admin.
"""

from __future__ import annotations

import datetime
import random
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from annuaire.models import Account, Chalet, Person, PresencePSV, Relation
from publications.models import Attachment, BlogPost, Comment


FIRST_NAMES = [
    "Alice", "Antoine", "Baptiste", "Camille", "Claire", "Élise", "Émile",
    "Étienne", "Fanny", "Gabriel", "Hugo", "Inès", "Julien", "Laura",
    "Lucas", "Manon", "Margaux", "Mathieu", "Nina", "Olivier", "Paul",
    "Pauline", "Quentin", "Romain", "Sophie", "Théo", "Valentine",
    "Victor", "Yann", "Zoé",
]

LAST_NAMES = [
    "Busson", "Bernard", "Dubois", "Lefevre", "Martin", "Moreau",
    "Petit", "Robert", "Roux", "Simon",
]

CHALET_NAMES = [
    "Chalet des Cimes", "Chalet du Lac", "Chalet des Mélèzes",
    "Chalet Edelweiss", "Chalet du Vieux Pont", "Chalet Belle Vue",
    "Chalet des Aiguilles",
]

CHALET_ADDRESSES = [
    "Route des Alpes, Verbier", "Chemin du Lac 7, Annecy",
    "Rue des Mélèzes 3, Megève", "Place de la Mairie, Chamonix",
    "Route du Col 12, Tignes", "Avenue du Mont-Blanc, Courchevel",
    "Sentier des Cascades, Méribel",
]

POST_TITLES = [
    "Bonne année à tous !",
    "Photos du week-end au chalet",
    "Mariage de Camille et Paul",
    "Naissance de la petite Inès",
    "Réunion de famille de septembre",
    "Rénovation du chalet du Lac",
    "Anniversaire surprise pour Mamie",
    "Recette du gratin dauphinois de tante Sophie",
    "Compte-rendu de l'AG de novembre",
    "Souvenirs d'enfance à la mer",
    "Préparatifs de Noël",
    "Le grand ménage de printemps",
    "Voyage en Italie l'été dernier",
    "Hommage à Pierre",
    "Album photo : vacances à la montagne",
    "Quelques nouvelles de la cousine Margaux",
    "Réservation des chalets pour l'hiver",
    "Recette : tarte tatin façon grand-mère",
    "Petits travaux d'entretien du chalet",
    "Le coin lecture : ce qu'on a aimé cet été",
    "Mariage de Théo et Pauline",
    "Préparation du dîner du 31 décembre",
    "Réunion BC : ordre du jour",
    "Photos de la randonnée du Mont-Blanc",
    "Brunch du dimanche en famille",
    "Petit mot pour les nouveaux arrivés",
    "Astuces de jardinage pour le printemps",
    "Souvenirs de la Saint-Sylvestre 2024",
    "Calendrier des vacances scolaires",
    "On cherche des photos d'archive !",
]

POST_BODIES = [
    "Voici quelques nouvelles à partager avec toute la famille. "
    "L'année commence sous les meilleurs auspices et nous espérons "
    "vous voir nombreux aux prochains événements.",
    "Petite mise à jour rapide depuis le chalet : tout va bien, "
    "le temps est magnifique et la neige abondante. Venez quand vous voulez !",
    "Un grand merci à tous ceux qui sont venus partager ce moment. "
    "Vos petits mots et vos cadeaux ont fait chaud au cœur.",
    "Comme promis, voici quelques photos de cette belle journée. "
    "N'hésitez pas à en ajouter dans les commentaires si vous en avez d'autres.",
    "Je profite de cette publication pour vous tenir au courant des "
    "derniers développements et recueillir vos avis sur la suite.",
    "Vous trouverez ci-joint un document avec tous les détails. "
    "Merci de me faire signe si vous avez la moindre question.",
]


# A 1×1 transparent PNG (smallest valid PNG) — used for image attachments.
TINY_PNG = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
    "0000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE426082"
)

# Minimal PDF marker — enough for our extension-based is_image detection.
TINY_PDF = b"%PDF-1.4\n%fake pdf payload\n%%EOF\n"


class Command(BaseCommand):
    help = "Populate the database with fake data for local development."

    # Per-model counts requested by the project owner.
    N_PERSONS = 20
    N_CHALETS = 5
    N_PRESENCES = 50
    N_RELATIONS = 30
    N_POSTS = 30
    N_ATTACHMENTS = 15
    N_COMMENTS = 100

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-clear', action='store_true',
            help="Don't wipe existing data before populating.",
        )
        parser.add_argument(
            '--seed', type=int, default=42,
            help="Random seed (default: 42) for reproducible runs.",
        )

    @transaction.atomic
    def handle(self, *args, no_clear: bool, seed: int, **options):
        random.seed(seed)

        if not no_clear:
            self._clear()

        admin = self._create_admin()
        staff = self._create_staff()
        persons = self._create_persons()
        chalets = self._create_chalets()
        self._create_presences(persons, chalets)
        self._create_relations(persons)
        posts = self._create_posts(persons)
        self._create_attachments(posts)
        self._create_comments(posts, persons)

        regular = persons[0].account
        self.stdout.write(self.style.SUCCESS(
            "\nDone. Test credentials:"
            f"\n  · Admin (superuser):     {admin.email} / admin"
            f"\n  · Staff (non-superuser): {staff.email} / staff"
            f"\n  · Regular user:          {regular.email} / dev"
            "\n(All other regular accounts also use password 'dev'.)"
        ))

    # ------------------------------------------------------------------ helpers

    def _clear(self):
        self.stdout.write("Clearing existing data…")
        Comment.objects.all().delete()
        Attachment.objects.all().delete()
        BlogPost.objects.all().delete()
        PresencePSV.objects.all().delete()
        Relation.objects.all().delete()
        Person.objects.all().delete()
        Chalet.objects.all().delete()
        Account.objects.all().delete()

    def _create_admin(self) -> Account:
        admin = Account.objects.create_superuser(
            email="admin@example.com", password="admin",
        )
        admin.must_change_password = False
        admin.save()
        self.stdout.write(f"  · created superuser {admin.email}")
        return admin

    def _create_staff(self) -> Account:
        """Non-superuser staff account — exercises StaffRequiredMixin paths
        without the superuser shortcut around permission checks."""
        staff = Account.objects.create_user(
            email="staff@example.com", password="staff", is_staff=True,
        )
        staff.must_change_password = False
        staff.save()
        # Give the staff member a Person profile too, so they can author posts
        # and comments like a normal member.
        Person.objects.create(
            first_name="Sandrine", last_name="Staff",
            email="staff@example.com",
            description="Membre du personnel (compte de test, non-superuser).",
        )
        # Re-link via signal (Person was created after Account, so trigger by save).
        person = Person.objects.get(email="staff@example.com")
        person.account = staff
        person.save()
        self.stdout.write(f"  · created staff {staff.email}")
        return staff

    def _create_persons(self) -> list[Person]:
        """Persons first (with email), then matching Accounts so the post-save
        signal links them automatically."""
        self.stdout.write(f"Creating {self.N_PERSONS} persons + accounts…")
        used_emails: set[str] = set()
        persons: list[Person] = []
        for i in range(self.N_PERSONS):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            email = f"{first.lower()}.{last.lower()}.{i}@example.com"
            while email in used_emails:
                i += 1
                email = f"{first.lower()}.{last.lower()}.{i}@example.com"
            used_emails.add(email)

            birth_year = random.randint(1940, 2015)
            birth_date = datetime.date(
                birth_year,
                random.randint(1, 12),
                random.randint(1, 28),
            )
            person = Person.objects.create(
                first_name=first, last_name=last, email=email,
                phone_number=f"+33 6 {random.randint(10, 99)} {random.randint(10, 99)} "
                             f"{random.randint(10, 99)} {random.randint(10, 99)}",
                postal_address=f"{random.randint(1, 99)} rue de la République, "
                               f"{random.choice(['Lyon', 'Paris', 'Annecy', 'Grenoble'])}",
                birth_date=birth_date,
                description=random.choice([
                    "Passionné de randonnée et de bonne cuisine.",
                    "Adore les longues soirées au coin du feu.",
                    "Skieur du dimanche, lecteur tous les jours.",
                    "",
                ]),
            )
            # Create the account separately so the signal links it to the person.
            account = Account.objects.create_user(email=email, password="dev")
            account.must_change_password = False
            account.save()
            person.refresh_from_db()
            persons.append(person)
        return persons

    def _create_chalets(self) -> list[Chalet]:
        self.stdout.write(f"Creating {self.N_CHALETS} chalets…")
        names = random.sample(CHALET_NAMES, k=self.N_CHALETS)
        addresses = random.sample(CHALET_ADDRESSES, k=self.N_CHALETS)
        return [
            Chalet.objects.create(name=name, address=address)
            for name, address in zip(names, addresses)
        ]

    def _create_presences(self, persons: list[Person], chalets: list[Chalet]):
        self.stdout.write(f"Creating {self.N_PRESENCES} presences…")
        for _ in range(self.N_PRESENCES):
            start = datetime.date(2026, random.randint(1, 11), random.randint(1, 25))
            length = random.randint(2, 14)
            end = start + datetime.timedelta(days=length)
            PresencePSV.objects.create(
                person=random.choice(persons),
                chalet=random.choice(chalets),
                start_date=start,
                end_date=end,
            )

    def _create_relations(self, persons: list[Person]):
        """Create directional Relations; the post-save signal auto-creates the
        inverse, so DB row count is roughly doubled."""
        self.stdout.write(
            f"Creating {self.N_RELATIONS} directional relations "
            f"(signal will mirror them)…"
        )
        seen_pairs: set[tuple[int, int]] = set()
        created = 0
        attempts = 0
        # 0=mariage, 1=conjoint, 2=parent, 3=enfant
        while created < self.N_RELATIONS and attempts < self.N_RELATIONS * 10:
            attempts += 1
            p1, p2 = random.sample(persons, 2)
            pair_key = tuple(sorted([p1.pk, p2.pk]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            rel_type = random.choice([0, 1, 2])  # we never seed enfant; signal handles
            start_date = None
            if rel_type in (0, 1):
                start_date = datetime.date(
                    random.randint(1980, 2020), random.randint(1, 12),
                    random.randint(1, 28),
                )
            Relation.objects.create(
                person1=p1, person2=p2,
                relationship_type=rel_type, start_date=start_date,
            )
            created += 1

    def _create_posts(self, persons: list[Person]) -> list[BlogPost]:
        self.stdout.write(f"Creating {self.N_POSTS} blog posts…")
        posts: list[BlogPost] = []
        titles = random.sample(POST_TITLES, k=min(self.N_POSTS, len(POST_TITLES)))
        # If we want more posts than unique titles, top up by suffixing.
        while len(titles) < self.N_POSTS:
            titles.append(f"{random.choice(POST_TITLES)} (suite)")
        for i, title in enumerate(titles):
            body_parts = random.sample(POST_BODIES, k=random.randint(1, 3))
            post = BlogPost.objects.create(
                title=title,
                body="\n\n".join(body_parts),
                post_type=random.choices(['NORMAL', 'BC'], weights=[3, 1])[0],
            )
            n_authors = random.choices([1, 2, 3], weights=[6, 3, 1])[0]
            post.authors.set(random.sample(persons, k=n_authors))
            posts.append(post)
        return posts

    def _create_attachments(self, posts: list[BlogPost]):
        self.stdout.write(f"Creating {self.N_ATTACHMENTS} attachments…")
        # ~2/3 images, ~1/3 non-image files.
        n_images = (self.N_ATTACHMENTS * 2) // 3
        n_files = self.N_ATTACHMENTS - n_images
        targets = (
            [('image', i) for i in range(n_images)]
            + [('file', i) for i in range(n_files)]
        )
        random.shuffle(targets)
        for kind, idx in targets:
            post = random.choice(posts)
            if kind == 'image':
                name = f"photo_{post.pk}_{idx}.png"
                content = ContentFile(TINY_PNG, name=name)
                caption = random.choice(["", "Vue depuis le balcon", "Souvenir", "Tous ensemble"])
            else:
                name = f"document_{post.pk}_{idx}.pdf"
                content = ContentFile(TINY_PDF, name=name)
                caption = random.choice(["Document à signer", "Compte-rendu", "Récapitulatif", ""])
            Attachment.objects.create(post=post, file=content, caption=caption)

    def _create_comments(self, posts: list[BlogPost], persons: list[Person]):
        self.stdout.write(f"Creating {self.N_COMMENTS} comments…")
        snippets = [
            "Merci pour le partage !",
            "Super photos, on se croirait sur place.",
            "Vivement la prochaine fois !",
            "Je note pour cet été.",
            "Quelle bonne idée, bravo.",
            "On compte les jours.",
            "Trop drôle, je me souviens très bien.",
            "Merci pour l'info, c'est noté.",
            "Magnifique, à refaire !",
            "Bisous à toute la famille.",
        ]
        for _ in range(self.N_COMMENTS):
            Comment.objects.create(
                post=random.choice(posts),
                author=random.choice(persons),
                body=random.choice(snippets),
            )
