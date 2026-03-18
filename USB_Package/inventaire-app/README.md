# Inventaire AV — v2.0.0

**Application de gestion d'inventaire de consommables et pièces détachées audiovisuelles.**

Application professionnelle (Windows / macOS) avec tableau de bord, moteur intelligent de prix avec détection d'anomalies, exports multi-formats (PDF, CSV, XLSX) et déploiement USB portable.

---

## Nouveautés v2.0.0

- **Tableau de bord** — KPIs temps réel, graphiques horizontaux par catégorie / emplacement / fournisseur, alertes stock bas
- **Totaux par ligne** — Colonnes T.Bas, T.Moy., T.Haut calculées automatiquement (quantité × prix)
- **Moteur de totaux global** — Synthèse dynamique par catégorie, emplacement, fournisseur, mode de prix
- **Détection d'anomalies** — Filtrage IQR + σ des valeurs aberrantes, alertes automatiques
- **Score de confiance 0–100** — Évaluation continue basée sur volume, fraîcheur, dispersion, quantité
- **Filtres rapides** — Boutons Tous / Stock bas / Prix incohérent / Sans prix dans l'inventaire
- **Export CSV** — Séparateur point-virgule, UTF-8 BOM, ligne de totaux
- **Export XLSX** — 4 onglets stylisés (Inventaire, Par catégorie, Par emplacement, Par fournisseur)
- **Export PDF enrichi** — Totaux par fournisseur, pied de page, colonnes de totaux ligne
- **Intégrité SHA-256** — Manifeste de vérification des fichiers applicatifs
- **Mode portable USB** — Détection automatique, marqueur `.portable`, chemin DB configurable

---

## Fonctionnalités

- **Inventaire complet** — Articles avec références, catégories, emplacements, fournisseurs
- **Tableau de bord métier** — 6 KPIs, graphiques interactifs, alertes stock bas, mises à jour récentes
- **Moteur intelligent de prix** — Fusion multi-sources avec filtrage IQR, score de confiance 0–100
- **Détection d'anomalies** — Identification automatique des incohérences de prix
- **3 modes de prix** — Manuel, Automatique, Mixte
- **Totaux dynamiques** — Par ligne, par catégorie, par emplacement, par fournisseur
- **Export multi-formats** — PDF (A4 paysage), CSV (BOM UTF-8), XLSX (4 onglets stylisés)
- **Gestion des fournisseurs** — Profils économique / moyen / cher
- **Alertes stock bas** — Seuil minimum configurable, filtrage rapide
- **Intégrité & sécurité** — Vérification SHA-256 au démarrage, manifeste d'intégrité
- **Mode portable** — Exécution directe depuis clé USB sans installation
- **Thème sombre professionnel** — Interface métier moderne (anthracite + turquoise/violet)

---

## Technologies

| Composant       | Technologie         |
|----------------|---------------------|
| Langage        | Python 3.10+        |
| Interface      | PySide6 (Qt6)       |
| Base de données| SQLite (WAL)        |
| Export PDF     | ReportLab           |
| Export XLSX    | openpyxl            |
| Packaging EXE  | PyInstaller         |
| Installateur   | Inno Setup          |

---

## Structure du projet

```
inventaire-app/
├── app/
│   ├── main.py                          # Point d'entrée (mode portable + intégrité)
│   ├── ui/
│   │   ├── main_window.py               # Fenêtre principale (8 vues)
│   │   ├── styles_dark.qss              # Thème sombre QSS
│   │   ├── icons/                       # Icônes SVG + logo
│   │   ├── views/
│   │   │   ├── dashboard_view.py        # Tableau de bord KPIs + graphiques
│   │   │   ├── inventory_view.py        # Inventaire + filtres rapides + totaux
│   │   │   ├── categories_view.py       # Gestion des catégories
│   │   │   ├── locations_view.py        # Gestion des emplacements
│   │   │   ├── suppliers_view.py        # Gestion des fournisseurs
│   │   │   ├── price_settings_view.py   # Paramètres du moteur de prix
│   │   │   ├── export_view.py           # Export PDF / CSV / XLSX
│   │   │   └── about_view.py            # À propos
│   │   └── components/
│   │       ├── data_table.py            # Tableau avec coloration dynamique
│   │       ├── dialogs.py               # Boîtes de dialogue métier
│   │       └── sidebar.py               # Barre latérale de navigation
│   ├── core/
│   │   ├── database.py                  # SQLite + CRUD + migration auto
│   │   ├── models.py                    # Dataclasses (totaux calculés, confiance)
│   │   ├── price_engine.py              # Moteur de prix (IQR, confiance, anomalies)
│   │   ├── totals_engine.py             # Calcul global des totaux
│   │   ├── export_engine.py             # Export CSV + XLSX stylisé
│   │   ├── pdf_exporter.py              # Export PDF ReportLab enrichi
│   │   └── integrity.py                 # Vérification SHA-256
│   ├── data/
│   │   └── inventaire.db                # Base SQLite (auto-créée)
│   └── config/
│       ├── settings.json                # Configuration générale (v2.0.0)
│       └── defaults/                    # Données initiales (catégories, emplacements, règles)
├── build/
│   ├── pyinstaller.spec                 # PyInstaller Windows
│   ├── pyinstaller_macos.spec           # PyInstaller macOS (.app)
│   ├── setup.iss                        # Inno Setup (v2.0.0)
│   ├── generate_manifest.py             # Outil CLI intégrité SHA-256
│   ├── preparer_package_usb.bat         # Génère le package USB (Windows)
│   └── preparer_package_usb.py          # Génère le package USB (Python, 7 étapes)
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
# Windows
pip install pyinstaller
pyinstaller build/pyinstaller.spec
```

L'exécutable sera généré dans `dist/InventaireAV.exe`.

```bash
# macOS
pip install pyinstaller
pyinstaller build/pyinstaller_macos.spec
```

Le bundle `.app` sera généré dans `dist/`.

---

## Création de l'installateur (Inno Setup)

### Prérequis

1. Installer [Inno Setup 6](https://jrsoftware.org/isinfo.php) sur Windows
2. Avoir généré l'EXE via PyInstaller (étape précédente)

### Compilation

1. Ouvrir `build/setup.iss` dans Inno Setup Compiler
2. `Build` → `Compile`
3. Le fichier `InventaireAV_Setup_2.0.0.exe` sera dans `dist/installer/`

### Installation silencieuse

```bash
InventaireAV_Setup_2.0.0.exe /SILENT
# ou
InventaireAV_Setup_2.0.0.exe /VERYSILENT
```

---

## Moteur de prix — Fonctionnement

Le moteur calcule un **prix moyen suggéré** en fusionnant jusqu'à 5 sources :

| Priorité | Source       | Description                                          |
|----------|-------------|------------------------------------------------------|
| 1        | Référence   | Prix fixé manuellement → priorité absolue            |
| 2        | Historique  | Moyenne pondérée (temps + volume), filtrage IQR + σ  |
| 3        | Fournisseur | Profil appliqué au défaut catégorie                  |
| 4        | Catégorie   | Médiane des prix des articles de même catégorie      |
| 5        | Défaut      | Prix par défaut de la catégorie                      |

### Détection d'anomalies

Le moteur identifie automatiquement les incohérences :
- Prix bas supérieur au prix moyen
- Prix moyen supérieur au prix haut
- Écart prix haut / prix bas > 5×
- Divergence > 50 % entre prix référence et prix calculé

### Score de confiance (0–100)

Chaque suggestion reçoit un score basé sur 4 facteurs :

| Facteur     | Poids  | Critère                                    |
|------------|--------|---------------------------------------------|
| Entrées    | 0–40   | Nombre de points de données disponibles     |
| Fraîcheur  | 0–30   | Ancienneté de la dernière mise à jour       |
| Dispersion | 0–20   | Coefficient de variation inverse            |
| Volume     | 0–10   | Quantité totale en stock                    |

Labels : **Fort** (≥ 70), **Moyen** (≥ 40), **Faible** (< 40)

**Fourchettes automatiques :**
- Prix Bas = Prix Moyen × 0.80
- Prix Haut = Prix Moyen × 1.25

**Modes :**
- `automatique` → le moteur calcule tout
- `manuel` → l'utilisateur fixe les 3 prix
- `mixte` → priorité : référence > catégorie > moteur

---

## Intégrité & Mode portable

### Vérification SHA-256

Au démarrage, l'application vérifie l'intégrité des fichiers via un manifeste SHA-256 :
```bash
# Générer le manifeste
python build/generate_manifest.py app/

# Vérifier le manifeste
python build/generate_manifest.py --verify app/
```

### Mode portable (USB)

L'application détecte automatiquement le mode portable si :
- Un fichier `.portable` existe à la racine
- Le dossier `python_embed` est présent dans le parent

En mode portable, la base de données est stockée dans le dossier applicatif et le titre de la fenêtre affiche « Mode portable ».

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
