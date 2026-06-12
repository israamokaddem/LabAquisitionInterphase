# WaveLab — Guide d'installation

Ce guide est destiné aux chercheurs qui installent WaveLab sur un nouveau poste.
Suivre les étapes **dans l'ordre**.

---

## Prérequis système

| Élément | Minimum |
|---|---|
| OS | Windows 10 / 11 (64 bits) |
| RAM | 8 Go |
| USB | Port USB 2.0 ou 3.0 libre par carte |
| Python | 3.9 ou supérieur |

---

## Étape 1 — Installer Python

1. Aller sur **https://www.python.org/downloads/**
2. Télécharger Python 3.11 ou 3.12 (64 bits)
3. Lancer l'installeur et **cocher impérativement** `Add Python to PATH`
4. Vérifier l'installation :

```bash
python --version
pip --version
```

---

## Étape 2 — Installer les dépendances Python

Ouvrir un terminal (cmd ou PowerShell) dans le dossier du projet et lancer :

```bash
pip install -r requirements.txt
```

Le fichier `requirements.txt` installe automatiquement :
- **PyQt6** — interface graphique
- **pyqtgraph** — graphiques temps réel
- **pandas** — fusion et export des données
- **numpy** — calculs numériques
- **scipy** — calculs FFT et relation de dispersion (méthodes Zelt, Liu & Huang)
- **opencv-python** — traitement d'image (calibration, homographie, détection surface libre)
- **matplotlib** — visualisation des résultats d'imagerie
- **tqdm** — barre de progression lors du traitement par lot d'images
---

## Étape 3 — Drivers et bibliothèques selon le matériel

### 3a. Boîtier MCC USB-1808X

**⚠️ Obligatoire même si vous n'avez pas la carte sous la main.**

#### Installation des drivers (MCC DAQ Software)

1. Aller sur : **https://digilent.com/reference/software/mccdaq-cd/start**
2. Télécharger **MCC DAQ Software** (contient InstaCal + Universal Library)
3. **Débrancher les cartes MCC avant de lancer l'installeur**
4. Lancer le `.exe` → tout laisser coché par défaut → Finish
5. **Rebrancher les cartes** après l'installation
6. Ouvrir **InstaCal** (Menu Démarrer → Measurement Computing → InstaCal)
7. Vérifier que vos cartes apparaissent (ex: `Board 0 — USB-1808X`)

#### Installation de la bibliothèque Python

```bash
pip install mcculw
```

> `mcculw` nécessite que le MCC DAQ Software soit installé au préalable.

---

### 3b. Boîtier National Instruments (NI)

#### Installation des drivers NI-DAQmx

1. Aller sur : **https://www.ni.com/fr-fr/support/downloads/drivers/download.ni-daq-mx.html**
2. Télécharger **NI-DAQmx** (version 2023 ou supérieure)
3. Lancer l'installeur → suivre les étapes
4. Redémarrer le PC à la fin
5. Ouvrir **NI MAX** (Menu Démarrer → National Instruments → NI MAX)
6. Vérifier que vos boîtiers apparaissent sous "Périphériques et interfaces"

#### Installation de la bibliothèque Python

```bash
pip install nidaqmx
```

---

### 3c. Boîtier Kistler LabAmp (réseau TCP/IP)

Aucun driver à installer. La carte doit être :
- Connectée au même réseau local (câble Ethernet ou switch)
- Son adresse IP notée (ex: `169.254.77.238`)
- Saisir cette IP dans l'interface WaveLab au moment du scan
 
---
## Étape 3bis — Configuration du répertoire de travail pour interphase de traitement

Le fichier `style.qss` (feuille de style de l'interface) doit se trouver
à la **racine du projet**, au même niveau que le dossier `Interpretation/`

## Étape 4 — Vérification finale

Brancher les cartes et lancer ce script de vérification :

```bash
python verifier_installation.py
```

Ce script vérifie automatiquement :
- La version Python
- Chaque bibliothèque installée
- La détection des cartes branchées

---

## Résumé — Ce qu'il faut installer selon le matériel

| Matériel utilisé | Logiciel à installer | Bibliothèque Python |
|---|---|---|
| MCC USB-1808X | MCC DAQ Software (InstaCal) | `pip install mcculw` |
| NI (tout modèle) | NI-DAQmx | `pip install nidaqmx` |
| Kistler LabAmp | Rien | (inclus dans le projet) |
| Aucun (simulation) | Rien | Rien |

---

## Problèmes fréquents

**"0 carte détectée" pour MCC**
→ Vérifier qu'InstaCal est installé et que la carte apparaît dedans avant de lancer WaveLab.

**"ModuleNotFoundError: nidaqmx"**
→ `pip install nidaqmx` puis vérifier que NI-DAQmx est bien installé sur le PC.

**"ModuleNotFoundError: mcculw"**
→ `pip install mcculw` puis vérifier que MCC DAQ Software est installé.

**L'interface ne se lance pas**
→ `pip install PyQt6 pyqtgraph` et relancer.

**Carte MCC détectée dans InstaCal mais pas dans WaveLab**
→ Lancer WaveLab en tant qu'administrateur (clic droit → Exécuter en tant qu'administrateur).

**"FileNotFoundError: style.qss"**
→ Vérifier que `style.qss` est bien dans le dossier racine du projet
  et que le Working Directory de PyCharm pointe sur ce même dossier.

**"ModuleNotFoundError: cv2"**
→ `pip install opencv-python`

**"ModuleNotFoundError: scipy"**
→ `pip install scipy`
---

## Support

Pour toute question, contacter l'équipe projet ou consulter :
- MCC / Digilent : https://forum.digilent.com
- NI : https://forums.ni.com
