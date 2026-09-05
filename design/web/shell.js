/* =========================================================================
   Famille Busson — mockup shell injector
   =========================================================================

   MOCKUP SCAFFOLDING ONLY. Nothing in this file is meant to ship. It exists
   so the six mockups can each show one archetype without every file carrying
   its own copy of the sidebar markup.

   In the real app the equivalent markup lives in annuaire/base.html and is
   rendered server-side; the theme toggle at the bottom becomes the inline
   <head> script described in SPEC.md §9.

   Usage in a mockup:
       <div class="fb-layout" data-fb-shell data-active="annuaire"> … </div>
       <script src="shell.js"></script>
   ========================================================================= */

/* The ridge. Three uneven peaks — real skylines are not symmetric — layered
   slate-mist behind / spruce in front, a zigzag snowcap on the tallest, and
   the two pines carried over from favicon.svg, the only brand asset that
   existed before this pass. */
const RIDGE = `
<svg class="fb-ridge" viewBox="0 0 240 76" preserveAspectRatio="none" role="img" aria-label="Crête de montagne">
  <path class="fb-ridge__far"  d="M0,76 L26,42 L52,58 L82,30 L108,56 L140,36 L172,60 L200,44 L240,62 L240,76 Z"/>
  <path class="fb-ridge__near" d="M0,76 L38,26 L66,54 L100,10 L136,50 L168,30 L206,58 L240,38 L240,76 Z"/>
  <path class="fb-ridge__snow" d="M100,10 L112,24 L106,21 L100,28 L94,21 L88,24 Z"/>
  <g class="fb-ridge__pine">
    <path d="M18,50 L25,62 L11,62 Z"/><path d="M18,58 L26,72 L10,72 Z"/><rect x="16.6" y="71" width="2.8" height="5"/>
    <path d="M222,52 L229,64 L215,64 Z"/><path d="M222,60 L230,73 L214,73 Z"/><rect x="220.6" y="72" width="2.8" height="4"/>
  </g>
</svg>`;

const NAV = [
    { label: null, items: [{ key: 'accueil', text: 'Accueil', href: '01-accueil.html' }] },
    {
        label: 'Les Busson', items: [
            { key: 'annuaire', text: 'Annuaire', href: '02-collections.html' },
            { key: 'genealogie', text: 'Généalogie', href: '04-outils.html' },
            { key: 'carte', text: 'Carte', href: '04-outils.html' },
            { key: 'chalets', text: 'Chalets', href: '02-collections.html#chalets' },
        ]
    },
    {
        label: 'Publications', items: [
            { key: 'publications', text: 'Toutes les publications', href: '02-collections.html#publications' },
            { key: 'publication-new', text: 'Nouvelle publication', href: '05-formulaires.html' },
        ]
    },
    {
        label: 'Documents', items: [
            { key: 'documents', text: 'Tous les documents', href: '02-collections.html#documents' },
            { key: 'categories', text: 'Catégories', href: '02-collections.html#categories' },
            { key: 'document-new', text: 'Nouveau document', href: '05-formulaires.html' },
        ]
    },
    {
        label: 'Administration', items: [
            { key: 'comptes', text: 'Créer des comptes', href: '05-formulaires.html#tableaux' },
            { key: 'groupes', text: 'Groupes', href: '05-formulaires.html#tableaux' },
            { key: 'admin', text: "Console d'admin", href: '#' },
        ]
    },
    {
        label: 'Aide', items: [
            { key: 'aide', text: 'La connexion par lien', href: '03-details.html#aide' },
            { key: 'bug', text: 'Signaler un bug', href: '#' },
        ]
    },
];

const AVATAR = 'data:image/svg+xml,' + encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
     <rect width="64" height="64" fill="#EFE3D0"/>
     <circle cx="32" cy="25" r="12" fill="#C9B49A"/>
     <path d="M8,64 C8,46 20,40 32,40 C44,40 56,46 56,64 Z" fill="#C9B49A"/></svg>`);

function sidebar(active) {
    const groups = NAV.map(g => `
        <div class="fb-nav__group">
          ${g.label ? `<p class="fb-eyebrow fb-nav__label">${g.label}</p>` : ''}
          <ul>${g.items.map(i => `
            <li><a href="${i.href}"${i.key === active ? ' aria-current="page"' : ''}>${i.text}</a></li>`).join('')}
          </ul>
        </div>`).join('');

    return `
    <aside class="fb-sidebar">
      <div class="fb-brand">
        <div class="fb-brand__name"><span class="fb-wordmark">Famille Busson</span></div>
        <div style="height:34px"></div>
        ${RIDGE}
      </div>
      <div class="fb-eaves"></div>

      <a class="fb-identity" href="03-details.html">
        <img src="${AVATAR}" alt="">
        <span>
          <span class="fb-identity__name">Camille Busson</span><br>
          <span class="fb-identity__role">Mon profil</span>
        </span>
      </a>

      <nav class="fb-nav" aria-label="Navigation principale">${groups}
        <div class="fb-nav__foot">
          <button type="button" class="fb-btn fb-btn--ghost fb-btn--sm" data-fb-theme-toggle>◐ Nightfall</button>
          <button type="button" class="fb-nav__logout fb-btn fb-btn--ghost fb-btn--sm" style="width:auto">Déconnexion</button>
        </div>
      </nav>
    </aside>`;
}

/* Placeholder imagery, so the mockups need no binary assets. */
const PLACEHOLDERS = {
    avatar: AVATAR,
    chalet: 'data:image/svg+xml,' + encodeURIComponent(
        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80">
         <rect width="120" height="80" fill="#F3D9B1"/>
         <path d="M0,80 L28,44 L52,62 L80,34 L104,58 L120,46 L120,80 Z" fill="#9FB0AE"/>
         <path d="M0,80 L34,50 L58,68 L86,42 L120,66 L120,80 Z" fill="#4B5D3F"/>
         <path d="M44,80 L60,58 L76,80 Z" fill="#7A4A2A"/>
         <rect x="52" y="68" width="8" height="12" fill="#3A2C1E"/></svg>`),
    photo: 'data:image/svg+xml,' + encodeURIComponent(
        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 120">
         <rect width="160" height="120" fill="#EFE3D0"/>
         <path d="M0,120 L40,58 L72,88 L104,44 L140,84 L160,66 L160,120 Z" fill="#9FB0AE"/>
         <circle cx="128" cy="28" r="12" fill="#D9A441"/></svg>`),
};

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-ph]').forEach(img => {
        img.src = PLACEHOLDERS[img.dataset.ph] || AVATAR;
    });
    document.querySelectorAll('[data-fb-shell]').forEach(el => {
        el.insertAdjacentHTML('afterbegin', sidebar(el.dataset.active));
    });
    document.querySelectorAll('[data-fb-theme-toggle]').forEach(btn => {
        btn.addEventListener('click', () => {
            const root = document.documentElement;
            const dark = root.getAttribute('data-bs-theme') === 'dark';
            root.setAttribute('data-bs-theme', dark ? 'light' : 'dark');
            btn.textContent = dark ? '◐ Nightfall' : '◑ Alpenglow';
        });
    });
});
