# Inventaire AV

**Application de gestion d'inventaire de consommables et pièces détachées audiovisuelles.**

Application Windows professionnelle avec thème sombre, moteur intelligent de prix et export PDF.

---

## Fonctionnalités

- **Inventaire complet** — Articles avec références, catégories, emplacements, fournisseurs
- **Moteur intelligent de prix** — Fusion multi-sources (historique, référence, catégorie, fournisseur, défaut)
- **3 modes de prix** — Manuel, Automatique, Mixte
- **Indice de confiance** — Fort / Moyen / Faible sur chaque suggestion
- **Export PDF** — Rapport paysage A4 avec logo, totaux par catégorie/emplacement
- **Gestion des fournisseurs** — Profils économique / moyen / cher
- **Alertes stock bas** — Seuil minimum configurable par article
- **Thème sombre professionnel** — Interface métier moderne (anthracite + turquoise/violet)

---

## Technologies

| Composant       | Technologie         |
|----------------|---------------------|
| Langage        | Python 3.x          |
| Interface      | PySide6 (Qt6)       |
| Base de données| SQLite              |
| Export PDF     | ReportLab           |
| Packaging EXE  | PyInstaller         |
| Installateur   | Inno Setup          |

---

## Structure du projet

```
inventaire-app/
├── app/
│   ├── main.py                          # Point d'entrée
│   ├── ui/
│   │   ├── main_window.py               # Fenêtre principale
│   │   ├── styles_dark.qss              # Thème sombre QSS
│   │   ├── icons/                       # Icônes SVG + logo
│   │   ├── views/                       # Écrans (inventaire, catégories, etc.)
│   │   └── components/                  # Composants réutilisables
│   ├── core/
│   │   ├── database.py                  # Accès SQLite + CRUD
│   │   ├── models.py                    # Dataclasses métier
│   │   ├── price_engine.py              # Moteur intelligent de prix
│   │   └── pdf_exporter.py              # Export PDF ReportLab
│   ├── data/
│   │   └── inventaire.db                # Base SQLite (auto-créée)
│   └── config/
│       ├── settings.json                # Configuration générale
│       └── defaults/                    # Données initiales (catégories, emplacements, règles)
├── build/
│   ├── pyinstaller.spec                 # Script PyInstaller
│   ├── setup.iss                        # Script Inno Setup
│   ├── preparer_package_usb.bat         # Génère le package USB (Windows)
│   └── preparer_package_usb.py          # Génère le package USB (Python)
├── Lanceur.bat                          # Lanceur intégré Windows
├── lanceur.py                           # Lanceur cross-platform
├── GUIDE_USB.md                         # Documentation déploiement USB
├── requirements.txt
└── README.md
```

---

## Installation (développement)

### Prérequis

- Python 3.10+ installé
- pip à jour

### Lancement rapide (méthode recommandée)

**Windows** : Double-cliquez sur `Lanceur.bat` — tout est automatique (venv, dépendances, lancement).

**Tous OS** :
```bash
python lanceur.py
```

### Étapes manuelles

```bash
# 1. Cloner le projet
cd inventaire-app

# 2. Créer un environnement virtuel
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer l'application
python -m app.main
```

> La base de données `inventaire.db` sera automatiquement créée au premier lancement avec les données par défaut (catégories, emplacements, règles de prix).

---

## Déploiement USB (installation hors-ligne)

Pour déployer sur un PC **sans Internet** et **sans droits admin** :

1. Sur un PC connecté, lancez le script de préparation :
   ```bash
   # Windows
   build\preparer_package_usb.bat

   # Ou Python (cross-platform)
   python build/preparer_package_usb.py
   ```
2. Copiez le dossier `USB_Package/` sur une **clé USB**
3. Sur le PC cible :
   - **`INSTALLER.bat`** → installation permanente (raccourci Bureau)
   - **`LANCER_DEPUIS_USB.bat`** → exécution portable directe

📖 Voir **[GUIDE_USB.md](GUIDE_USB.md)** pour le guide complet.

---

## Compilation EXE (PyInstaller)

```bash
# Depuis la racine du projet
pip install pyinstaller
pyinstaller build/pyinstaller.spec
```

L'exécutable sera généré dans `dist/InventaireAV.exe`.

---

## Création de l'installateur (Inno Setup)

### Prérequis

1. Installer [Inno Setup 6](https://jrsoftware.org/isinfo.php) sur Windows
2. Avoir généré l'EXE via PyInstaller (étape précédente)

### Compilation

1. Ouvrir `build/setup.iss` dans Inno Setup Compiler
2. `Build` → `Compile`
3. Le fichier `InventaireAV_Setup_1.0.0.exe` sera dans `dist/installer/`

### Installation silencieuse

```bash
InventaireAV_Setup_1.0.0.exe /SILENT
# ou
InventaireAV_Setup_1.0.0.exe /VERYSILENT
```

---

## Moteur de prix — Fonctionnement

Le moteur calcule un **prix moyen suggéré** en fusionnant jusqu'à 5 sources :

| Priorité | Source       | Description                                          |
|----------|-------------|------------------------------------------------------|
| 1        | Référence   | Prix fixé manuellement → priorité absolue            |
| 2        | Historique  | Moyenne pondérée (temps + volume), exclusion σ       |
| 3        | Fournisseur | Profil appliqué au défaut catégorie                  |
| 4        | Catégorie   | Médiane des prix des articles de même catégorie      |
| 5        | Défaut      | Prix par défaut de la catégorie                      |

**Fourchettes automatiques :**
- Prix Bas = Prix Moyen × 0.80
- Prix Haut = Prix Moyen × 1.25

**Modes :**
- `automatique` → le moteur calcule tout
- `manuel` → l'utilisateur fixe les 3 prix
- `mixte` → priorité : référence > catégorie > moteur

---

## Configuration

Le fichier `config/settings.json` permet de modifier :
- Facteurs de fourchette (bas/haut)
- Décroissance temporelle de l'historique
- Seuil d'exclusion des aberrations (σ)
- Pondération des sources

Les paramètres sont aussi modifiables dans l'écran **Paramètres prix** de l'application.

---

## Licence

Projet interne — usage privé.
