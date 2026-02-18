# Inventaire AV — Guide de Déploiement USB

## Vue d'ensemble

Ce package permet d'installer **Inventaire AV** sur n'importe quel PC Windows
**sans connexion Internet** et **sans droits administrateur**.

---

## 📦 Contenu du Package USB

```
USB_Package/
├── INSTALLER.bat            ← Installation permanente sur le PC
├── LANCER_DEPUIS_USB.bat    ← Exécution directe depuis la clé USB
├── python_embed/            ← Python 3.11 embarqué (portable)
│   └── python/
└── inventaire-app/          ← Application complète
    ├── app/                 ← Code source
    ├── wheels/              ← Packages Python pré-téléchargés
    ├── Lanceur.bat          ← Lanceur autonome
    ├── lanceur.py           ← Lanceur Python cross-platform
    └── requirements.txt
```

---

## 🚀 Mode 1 : Installation permanente sur le PC

**Idéal pour** : utilisation quotidienne sur un poste fixe.

1. Branchez la clé USB sur le PC cible
2. Ouvrez le dossier `USB_Package\`
3. **Double-cliquez sur `INSTALLER.bat`**
4. Confirmez l'installation en tapant `O`
5. L'installation se fait dans `%USERPROFILE%\InventaireAV\`
6. Un **raccourci « Inventaire AV »** est créé sur le Bureau

### Après installation :
- Double-cliquez sur le **raccourci Bureau** pour lancer l'application
- Ou lancez `%USERPROFILE%\InventaireAV\Lancer InventaireAV.bat`
- La clé USB peut être retirée

### Désinstallation :
Supprimez simplement le dossier `%USERPROFILE%\InventaireAV\` et le raccourci Bureau.

---

## 🔌 Mode 2 : Exécution directe depuis la clé USB (portable)

**Idéal pour** : dépannage, utilisation ponctuelle, PC partagés.

1. Branchez la clé USB
2. Ouvrez le dossier `USB_Package\`
3. **Double-cliquez sur `LANCER_DEPUIS_USB.bat`**
4. L'application se lance directement depuis la clé

> **Note** : La première exécution installe les dépendances dans le Python
> embarqué de la clé. Les lancements suivants seront plus rapides.

> **Important** : La base de données est stockée sur la clé USB.
> Ne retirez pas la clé pendant l'utilisation.

---

## 🛠 Préparer le Package USB (pour l'administrateur)

### Prérequis :
- Un PC avec **Python 3.10+** installé
- Une **connexion Internet**
- Au moins **1 Go d'espace libre**

### Option A : Script batch (Windows uniquement)
```batch
cd build\
preparer_package_usb.bat
```

### Option B : Script Python (cross-platform)
```bash
cd build/
python preparer_package_usb.py
```

### Résultat :
Un dossier `USB_Package/` est créé à la racine du projet.
Copiez-le tel quel sur la clé USB.

---

## 📋 Configuration requise (PC cible)

| Composant       | Minimum                     |
|----------------|-----------------------------|
| **OS**         | Windows 10 / 11 (64-bit)   |
| **RAM**        | 4 Go                        |
| **Espace**     | 500 Mo (installation)       |
| **Écran**      | 1280 × 720 minimum         |
| **Droits**     | Utilisateur standard        |
| **Internet**   | Non requis                  |

---

## ❓ Résolution de problèmes

### « Windows a protégé votre ordinateur » (SmartScreen)
→ Cliquez sur **« Informations complémentaires »** puis **« Exécuter quand même »**

### « python n'est pas reconnu... »
→ En mode USB, ce message ne devrait pas apparaître (Python embarqué).
→ En mode classique (`Lanceur.bat`), installez Python 3.10+ et cochez
  « Add Python to PATH » lors de l'installation.

### L'application ne démarre pas
1. Vérifiez que le dossier `wheels/` contient bien des fichiers `.whl`
2. Essayez de lancer manuellement :
   ```batch
   python_embed\python\python.exe -m pip install --no-index --find-links=inventaire-app\wheels -r inventaire-app\requirements.txt
   ```
3. Puis :
   ```batch
   cd inventaire-app
   ..\python_embed\python\python.exe -m app.main
   ```

### Erreur « No module named PySide6 »
→ Les dépendances ne sont pas installées. Relancez `INSTALLER.bat` ou `LANCER_DEPUIS_USB.bat`.

---

## 📝 Architecture du lanceur

```
Lanceur.bat / lanceur.py
    │
    ├─ 1. Détecte Python (embarqué local → système)
    ├─ 2. Crée un venv si absent
    ├─ 3. Installe les dépendances
    │      ├─ Mode offline : wheels/ (USB)
    │      └─ Mode online : PyPI (Internet)
    └─ 4. Lance python -m app.main
```

Le lanceur est **idempotent** : il peut être relancé à tout moment sans risque.
Il détecte automatiquement si les étapes ont déjà été effectuées.

---

*Inventaire AV © 2024 — Gestion des consommables audiovisuels*
