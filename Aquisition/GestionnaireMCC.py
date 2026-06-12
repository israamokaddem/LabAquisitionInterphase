"""
================================================================================
GestionnaireMCC.py  —  version mcculw (Windows uniquement)
================================================================================

Rôle :
    Contrôle un ou plusieurs boîtiers MCC USB-1808X branchés en USB.
    Implémente la classe abstraite GestionnaireAquisition pour s'intégrer
    dans l'architecture WaveLab (GestionnairePrincipal + AcquisitionThread).

Bibliothèque utilisée :
    mcculw  —  MCC Universal Library pour Windows.
    C'est le wrapper Python officiel de la Universal Library (UL) de
    Measurement Computing. Elle communique avec les drivers installés
    par le MCC DAQ Software (InstaCal).

    DIFFÉRENCE CLEF avec uldaq (version Linux) :
        - uldaq  : objets Python (DaqDevice, AiDevice…)
        - mcculw : numéros de boîtiers entiers (board_num = 0, 1, 2…)
          Chaque carte branchée reçoit un numéro, et toutes les fonctions
          ul.xxx() prennent ce numéro en premier argument.

Mode simulation :
    Si mode_simulation=True (ou si mcculw n'est pas installé), toutes les
    opérations matérielles sont remplacées par des classes Python internes
    (_MockUL, _MockEnums, _SimBuffer) qui génèrent des signaux sinusoïdaux
    réalistes. L'interface publique est IDENTIQUE — le reste du code
    (GestionnairePrincipal, UI) ne sait pas si c'est réel ou simulé.

Prérequis pour le mode réel :
    1. Installer MCC DAQ Software (InstaCal + Universal Library) :
       https://digilent.com/reference/software/mccdaq-cd/start
    2. pip install mcculw
================================================================================
"""
import ctypes
import os       # construction des chemins de fichiers
import csv      # écriture des données en CSV
import math     # fonctions sin, pi pour la simulation
import time     # non utilisé directement mais importé pour extensions futures
import random   # bruit gaussien pour la simulation
from GestionnaireAquisition import GestionnaireAquisition  # classe abstraite parente


# ================================================================================
# SECTION 1 — COUCHE DE SIMULATION
# ================================================================================
# Ces classes imitent exactement l'API de mcculw.ul et mcculw.enums.
# Elles sont utilisées quand :
#   - mode_simulation=True est demandé explicitement
#   - mcculw n'est pas installé sur le poste
#
# Le principe : chaque méthode de _MockUL a la même signature que la vraie.
# Ainsi le code de GestionnaireMCC n'a AUCUNE branche if/else pour choisir
# entre réel et simulé — il appelle toujours self._ul.xxx() et c'est
# le binding (_MockUL ou le vrai ul) qui décide quoi faire.
# ================================================================================

class _SimBuffer:
    """
    Remplace un "handle mémoire Windows" (objet ctypes retourné par
    ul.scaled_win_buf_alloc en mode réel) par une simple liste Python.

    En mode réel, mcculw alloue un buffer dans la RAM Windows partagée
    entre le driver et Python. Ici on simule ça avec une liste de floats.

    Attribut :
        _data : liste de floats de longueur 'taille', initialisée à 0.0
    """
    def __init__(self, taille):
        # Initialise le buffer à zéro — sera rempli par a_in_scan
        self._data = [0.0] * taille

    def __len__(self):
        return len(self._data)


class _MockUL:
    """
    Imite le module mcculw.ul (Universal Library) pour la simulation.

    mcculw.ul est un module-objet singleton — toutes ses fonctions sont
    des fonctions du module, pas des méthodes d'instance. C'est pourquoi
    on utilise @staticmethod partout : même comportement que le vrai ul.

    Registre de classe :
        _boards : dict {board_num (int) -> product_name (str)}
        Garde trace des boîtiers "enregistrés" pendant la session simulée.
    """

    _boards = {}   # registre des boards simulés (équivalent du registre interne UL)

    @staticmethod
    def ignore_instacal():
        """
        En mode réel : dit à la UL d'ignorer la configuration d'InstaCal
        et de détecter les boîtiers automatiquement par USB.
        En simulation : no-op (rien à faire).
        """
        pass

    @staticmethod
    def get_daq_device_inventory(interface_type):
        """
        En mode réel : scanne le bus USB et retourne la liste des
        descripteurs (DaqDeviceDescriptor) de tous les boîtiers trouvés.
        En simulation : retourne deux descripteurs fictifs représentant
        deux USB-1808X simulés avec des numéros de série distincts.

        Retourne : liste de descripteurs (objets avec .product_name et .unique_id)
        """
        class D1:
            product_name = "USB-1808X"   # modèle du boîtier
            unique_id    = "SIM-0001"    # numéro de série fictif boîtier 1
        class D2:
            product_name = "USB-1808X"
            unique_id    = "SIM-0002"    # numéro de série fictif boîtier 2
        return [D1(), D2()]

    @staticmethod
    def create_daq_device(board_num, descriptor):
        """
        En mode réel : enregistre le descripteur sous le numéro board_num
        dans le registre interne de la Universal Library. Après cet appel,
        toutes les fonctions ul.xxx(board_num, ...) savent quelle carte
        physique utiliser.
        En simulation : enregistre juste dans le dict de classe _boards.

        Args :
            board_num  : entier (0, 1, 2…) qu'on attribue à cette carte
            descriptor : objet descripteur retourné par get_daq_device_inventory
        """
        _MockUL._boards[board_num] = descriptor.product_name

    @staticmethod
    def release_daq_device(board_num):
        """
        En mode réel : libère les ressources driver associées à board_num.
        À appeler obligatoirement en fin de programme pour éviter les
        conflits si une autre application veut utiliser la même carte.
        En simulation : supprime juste l'entrée du dict.
        """
        _MockUL._boards.pop(board_num, None)

    @staticmethod
    def scaled_win_buf_alloc(count):
        """
        En mode réel : alloue un buffer ctypes en mémoire Windows partagée
        entre le driver MCC et Python. Retourne un handle (objet ctypes).
        Le "scaled" signifie que les données seront déjà converties en volts
        (pas en raw counts 18-bit) — c'est ce qu'on veut.

        En simulation : retourne un _SimBuffer (liste Python).

        Args :
            count : nombre TOTAL de points à stocker
                    = nb_canaux * points_par_lecture

        Retourne : handle mémoire (réel) ou _SimBuffer (simulation)
        """
        return _SimBuffer(count)

    @staticmethod
    def win_buf_free(handle):
        """
        En mode réel : libère la mémoire Windows allouée par scaled_win_buf_alloc.
        OBLIGATOIRE après chaque lecture pour éviter les fuites mémoire.
        En simulation : no-op (le garbage collector Python s'en charge).
        """
        pass

    @staticmethod
    def scaled_win_buf_to_array(handle, dest_array, offset, count):
        """
        En mode réel : copie 'count' valeurs du handle ctypes vers dest_array,
        en commençant à la position 'offset' dans le handle.
        Nécessaire car on ne peut pas accéder directement à un buffer ctypes
        comme à une liste Python.

        En simulation : copie simplement handle._data[offset:offset+count]
        dans dest_array.

        Args :
            handle     : buffer source (handle ctypes ou _SimBuffer)
            dest_array : liste Python destination (déjà allouée)
            offset     : index de départ dans le buffer source
            count      : nombre de valeurs à copier
        """
        for i in range(count):
            dest_array[i] = handle._data[offset + i]

    @staticmethod
    def a_in_scan(board_num, low_chan, high_chan,
                  count, rate, ul_range, mem_handle, options):
        """
        Cœur de l'acquisition — remplit mem_handle avec des données simulées.

        En mode réel, cette fonction déclenche une acquisition hardware :
        la carte échantillonne physiquement les voies de low_chan à high_chan
        à la fréquence 'rate', pour un total de 'count' points entrelacés,
        et remplit le buffer mémoire Windows.

        Format d'entrelacement mcculw (identique au hardware réel) :
            [ch0_t0, ch1_t0, ch2_t0, ch0_t1, ch1_t1, ch2_t1, ...]
            Les canaux tournent en boucle pour chaque instant t.

        En simulation : génère des sinus multi-fréquences avec bruit gaussien.
            - Canal 0 (low_chan+0) : sinus à 10 Hz, amplitude 2.0 V
            - Canal 1 (low_chan+1) : sinus à 20 Hz, amplitude 1.0 V
            - Canal 2 (low_chan+2) : sinus à 30 Hz, amplitude 0.67 V
            - etc. (fréquence *= (c+1), amplitude /= (c+1))
            Cela permet de distinguer visuellement les voies sur le graphique.

        Args :
            board_num  : numéro de la carte (0, 1, 2…)
            low_chan   : premier canal à lire (ex: 0 pour ai0)
            high_chan  : dernier canal à lire  (ex: 3 pour ai3)
            count      : nb total de points = nb_canaux * points_par_canal
            rate       : fréquence d'échantillonnage en Hz
            ul_range   : plage de tension (ex: BIP10VOLTS = ±10 V)
            mem_handle : buffer de destination (handle ctypes ou _SimBuffer)
            options    : flags binaires (DEFAULTIO, SCALEDATA…)

        Retourne : fréquence réelle utilisée (float) — peut différer de
                   'rate' si la carte arrondit à une valeur supportée.
        """
        nb_canaux     = high_chan - low_chan + 1  # nombre de voies scannées
        pts_par_canal = count // nb_canaux        # points par voie

        for j in range(pts_par_canal):
            t = j / rate   # temps absolu du point j (en secondes)
            for c in range(nb_canaux):
                # Signal sinusoïdal unique par canal pour différenciation visuelle
                freq_sig = 10.0 * (c + low_chan + 1)   # fréquence croissante par canal
                amp      = 2.0  / (c + low_chan + 1)   # amplitude décroissante
                # Ajout d'un bruit blanc gaussien (écart-type 0.02 V) pour réalisme
                val = amp * math.sin(2 * math.pi * freq_sig * t) + random.gauss(0, 0.02)
                # Stockage en format entrelacé : index = j * nb_canaux + c
                mem_handle._data[j * nb_canaux + c] = val

        return rate   # en simulation, on respecte exactement la fréquence demandée

    @staticmethod
    def stop_background(board_num, function_type):
        """
        En mode réel : arrête un scan lancé en mode BACKGROUND (asynchrone).
        En simulation : no-op (nos scans sont synchrones/bloquants).
        """
        pass


class _MockEnums:
    """
    Imite le module mcculw.enums qui contient toutes les constantes
    numériques utilisées par la Universal Library.

    En mode réel, ces constantes sont envoyées directement au driver
    Windows (ce sont des codes entiers définis par MCC).
    En simulation, leurs valeurs exactes n'ont pas d'importance —
    elles sont juste ignorées par _MockUL.
    """

    class InterfaceType:
        """Type d'interface physique pour le scan des périphériques."""
        USB = 1   # scan uniquement les périphériques USB (suffisant pour le 1808X)

    class ULRange:
        """Plage de tension analogique en entrée."""
        BIP10VOLTS = 1   # ±10 V — plage par défaut du USB-1808X en différentiel

    class ScanOptions:
        """
        Flags binaires combinables avec | pour configurer le scan.
        En mode réel, ces valeurs modifient le comportement du driver.
        """
        DEFAULTIO = 0      # mode par défaut : scan bloquant (attend la fin)
        SCALEDATA = 2048   # retourne directement des volts (float) plutôt
                           # que des counts bruts 18-bit — IMPORTANT pour nous

    class FunctionType:
        """Type de fonction hardware à arrêter (pour stop_background)."""
        AIFUNCTION = 1   # Analog Input — c'est notre cas (lecture de tension)


# ================================================================================
# SECTION 2 — GESTIONNAIRE MCC
# ================================================================================
# Classe principale. Hérite de GestionnaireAquisition (classe abstraite) et
# implémente toutes ses méthodes abstraites.
#
# Cycle de vie typique (appelé par GestionnairePrincipal) :
#   1. __init__()              → création + chargement mcculw
#   2. initialiser_systeme()   → détection des cartes USB
#   3. definir_parametres()    → réglages fréquence, durée, fichier
#   4. lancer_acquisition()    → boucle d'acquisition + écriture CSV
#   5. liberer()               → nettoyage à la fermeture de l'app
# ================================================================================

class GestionnaireMCC(GestionnaireAquisition):

    def __init__(self, mode_simulation: bool = False):
        """
        Initialise le gestionnaire MCC.

        Args :
            mode_simulation : si True, aucun matériel réel n'est nécessaire.
                              Les données sont générées synthétiquement.
                              Utile pour développer sans boîtier disponible.
        """
        super().__init__()   # initialise la classe abstraite parente

        # ----- Paramètre principal -----
        self.mode_simulation = mode_simulation
        # True  → utilise _MockUL, génère des sinus
        # False → utilise mcculw réel, lit les vraies tensions

        # ----- Listes et dicts d'état -----

        self.boitiers_detectes = []
        # Liste de dicts, un par boîtier trouvé. Format imposé par l'UI :
        # { "nom": "MCC-USB1808X-SIM-0001",
        #   "modele": "USB-1808X",
        #   "total_voies": 8,
        #   "voies_dispos": ["MCC-.../ai0", ..., "MCC-.../ai7"],
        #   "backend": "MCC",
        #   "simule": True/False }

        self.voies_disponibles = []
        # Liste plate de tous les chemins de voies du premier boîtier détecté.
        # Format : ["MCC-USB1808X-SIM-0001/ai0", ..., "MCC-USB1808X-SIM-0001/ai7"]
        # Utilisée par la page "Sélection voies" de l'UI pour peupler les boutons.

        self.voies_selectionnees = []
        # Sous-ensemble de voies_disponibles choisi par l'utilisateur.
        # Rempli en mode CLI par configurer_voies().
        # En mode UI, c'est dictionnaire_voies dans lancer_acquisition() qui prime.

        self.config_sondes = {}
        # Dict de configuration par voie :
        # { "MCC-.../ai0": {"type": "Pression", "unite": "pa"}, ... }
        # Permet à appliquer_traitement() de savoir quelle formule appliquer.

        self.chemins_voies_actives = []
        # Liste des voies effectivement utilisées lors du DERNIER lancer_acquisition().
        # Utilisée par la page Calibration de l'UI pour construire ses colonnes.

        self.donnees_brutes = []
        # Réservé pour une éventuelle sauvegarde de secours en mémoire.
        # Non utilisé en temps réel (les données vont directement en CSV).

        self.temps_array = []
        # Idem — tableau temporel pour sauvegarde de secours.

        self._board_map = {}
        # Correspondance nom_boitier → board_num mcculw.
        # Ex: {"MCC-USB1808X-SIM-0001": 0, "MCC-USB1808X-SIM-0002": 1}
        # CRUCIAL : mcculw identifie les cartes par ces entiers, pas par des objets.
        # On doit donc retrouver le board_num à partir du nom lors de l'acquisition.

        # ----- Paramètres d'acquisition (valeurs par défaut) -----
        self.parametres = {
            "frequence"    : 1000,          # Hz — fréquence d'échantillonnage
            "duree"        : 10,            # secondes — durée totale d'acquisition
            "nom_fichier"  : "donnees_mcc.csv",  # nom du fichier de sortie
            "dossier_sortie": "."           # dossier de sauvegarde (. = répertoire courant)
        }

        # ----- Chargement de la bibliothèque -----
        # Retourne (ul, enums) : soit les vrais modules mcculw, soit les mocks.
        self._ul, self._enums = self._charger_mcculw()

    # ============================================================
    def _charger_mcculw(self):
        """
        Tente de charger mcculw réel ou retourne les mocks selon le mode.

        Logique de décision :
            mode_simulation=True  → retourne (_MockUL, _MockEnums) directement
            mode_simulation=False → tente "from mcculw import ul"
                                    → si ImportError : retourne (ULVide, _MockEnums)
                                      ULVide = ul avec inventaire VIDE (pas de
                                      simulation forcée — aucun boîtier affiché)

        Retourne :
            tuple (ul_object, enums_object) utilisé dans toutes les méthodes.
        """
        if not self.mode_simulation:
            try:
                from mcculw import ul           # module Universal Library
                import mcculw.enums as enums    # constantes (ULRange, ScanOptions…)
                return ul, enums

            except ImportError:
                # mcculw absent — on ne force PAS la simulation.
                # On retourne un ul avec inventaire vide pour que
                # initialiser_systeme() retourne False proprement.
                print("[MCC] mcculw non installé — aucun boîtier détectable.")
                print("[MCC] Installer : pip install mcculw")
                print("[MCC] (+ MCC DAQ Software depuis digilent.com)")

                class ULVide:
                    """ul fictif avec get_daq_device_inventory qui retourne []."""
                    ignore_instacal          = staticmethod(lambda: None)
                    get_daq_device_inventory = staticmethod(lambda _: [])
                    create_daq_device        = staticmethod(lambda b, d: None)
                    release_daq_device       = staticmethod(lambda b: None)
                    scaled_win_buf_alloc     = staticmethod(lambda n: _SimBuffer(n))
                    win_buf_free             = staticmethod(lambda h: None)
                    scaled_win_buf_to_array  = staticmethod(lambda h, d, o, c: None)
                    a_in_scan                = staticmethod(lambda *a, **k: 0)
                    stop_background          = staticmethod(lambda b, f: None)

                return ULVide(), _MockEnums()

        # mode_simulation=True : on utilise les mocks directement
        return _MockUL(), _MockEnums()

    # ============================================================
    # ÉTAPE 1 : DÉTECTION DES BOÎTIERS
    # ============================================================
    def initialiser_systeme(self) -> bool:
        """
        Scanne le bus USB à la recherche de boîtiers MCC.
        Peuple self.boitiers_detectes et self._board_map.

        Protocole mcculw en mode réel :
            1. ul.ignore_instacal() : court-circuite la configuration
               d'InstaCal pour utiliser la détection automatique USB.
            2. ul.get_daq_device_inventory(USB) : liste les boîtiers branchés.
            3. ul.create_daq_device(board_num, desc) : associe un numéro entier
               à chaque boîtier. Après ça, board_num=0 désigne la 1ère carte, etc.
            4. Test rapide (a_in_scan de 8 points à 100 Hz) pour confirmer
               que la carte répond vraiment (elle peut être listée mais débranchée).

        En simulation : chemin direct sans aucun appel matériel.

        Retourne : True si au moins un boîtier est détecté, False sinon.
        """
        # Réinitialisation avant chaque scan (l'utilisateur peut scanner plusieurs fois)
        self.boitiers_detectes.clear()
        self._board_map.clear()
        ul    = self._ul
        enums = self._enums
        self.voies_disponibles = []

        try:
            # Étape 1 : contournement InstaCal pour détection automatique USB
            ul.ignore_instacal()

            # Étape 2 : inventaire des boîtiers sur le bus USB
            descripteurs = ul.get_daq_device_inventory(enums.InterfaceType.USB)

            if not descripteurs:
                # Aucun boîtier trouvé sur le bus
                return False

            # Étape 3 : enregistrement de chaque boîtier avec son numéro
            for board_num, desc in enumerate(descripteurs):
                # board_num : 0 pour le 1er boîtier, 1 pour le 2ème, etc.
                # desc      : descripteur avec .product_name et .unique_id
                try:
                    # Lie ce descripteur au numéro board_num dans la UL
                    ul.create_daq_device(board_num, desc)

                    # Étape 4 (mode réel uniquement) : test de communication
                    # On lit 8 points sur ai0 à 100 Hz — si ça ne plante pas,
                    # la carte est vraiment accessible.
                    if not self.mode_simulation:
                        buf = ul.scaled_win_buf_alloc(8)   # buffer test minimal
                        ul.a_in_scan(
                            board_num,
                            0, 0,                          # low_chan=0, high_chan=0 → ai0 seulement
                            8,                             # 8 points au total
                            100,                           # 100 Hz (test rapide)
                            enums.ULRange.BIP10VOLTS,
                            buf,
                            enums.ScanOptions.DEFAULTIO | enums.ScanOptions.SCALEDATA
                        )
                        ul.win_buf_free(buf)   # libération obligatoire du buffer test

                    # Construction du nom unique de boîtier pour l'UI
                    # Format : "MCC-USB1808X-SIM-0001"
                    nb_voies = 8   # le USB-1808X a toujours 8 voies analogiques
                    nom      = f"MCC-{desc.product_name}-{desc.unique_id}"

                    # Génération des chemins de voies
                    # Format imposé : "NOM_BOITIER/aiN"
                    # Le /aiN permet d'extraire l'index par split("ai")[-1]
                    voies = [f"{nom}/ai{i}" for i in range(nb_voies)]

                    # Mémorisation de la correspondance nom ↔ board_num
                    self._board_map[nom] = board_num

                    # Ajout au registre des boîtiers (format attendu par l'UI)
                    self.boitiers_detectes.append({
                        "nom"         : nom,
                        "modele"      : desc.product_name,
                        "total_voies" : nb_voies,
                        "voies_dispos": voies,
                        "backend"     : "MCC",        # identifiant pour GestionnairePrincipal
                        "simule"      : self.mode_simulation
                    })

                    # Premier boîtier détecté → alimente voies_disponibles
                    # (utilisé par la page Sélection voies de l'UI)
                    if not self.voies_disponibles:
                        self.voies_disponibles = voies

                except Exception as e:
                    # Ce boîtier a été listé mais n'est pas accessible
                    # (câble débranché entre l'inventaire et le test, par ex.)
                    print(f"[MCC] Board {board_num} ({desc.product_name}) inaccessible : {e}")
                    try:
                        # Nettoyage : on libère le slot board_num qu'on vient d'allouer
                        ul.release_daq_device(board_num)
                    except Exception:
                        pass   # si release échoue aussi, on continue quand même

            # True si au moins 1 boîtier valide a été enregistré
            return len(self.boitiers_detectes) > 0

        except Exception as e:
            # Erreur fatale lors du scan (driver absent, conflit…)
            print(f"[MCC] Erreur détection : {e}")
            return False

    # ============================================================
    # ÉTAPE 2 : SÉLECTION DES VOIES  (mode CLI uniquement)
    # ============================================================
    def configurer_voies(self):
        """
        Interaction texte pour choisir les voies et leur type de capteur.
        Utilisée uniquement si on lance le script directement (if __name__…).
        En mode UI, c'est la page "Sélection voies" qui gère ça graphiquement,
        et dictionnaire_voies est passé directement à lancer_acquisition().
        """
        print("\n--- MCC : SÉLECTION DES VOIES ---")
        for i, v in enumerate(self.voies_disponibles):
            print(f"  [{i}] {v}")

        choix  = input("Numéros de voies à utiliser (ex: 0,1,3) : ")
        unites = {
            "Tension"    : "v",
            "Pression"   : "pa",
            "Frequence"  : "hz",
            "Temperature": "c"
        }

        for idx in [int(x.strip()) for x in choix.split(',')]:
            voie = self.voies_disponibles[idx]
            self.voies_selectionnees.append(voie)

            print(f"\nType de capteur sur {voie} :")
            print("  1. Tension  2. Pression  3. Frequence  4. Temperature")
            t           = input("Choix (1-4) : ")
            type_mesure = list(unites.keys())[int(t) - 1]
            # On stocke le type pour que appliquer_traitement() sache quoi faire
            self.config_sondes[voie] = {
                "type" : type_mesure,
                "unite": unites[type_mesure]
            }

    # ============================================================
    # ÉTAPE 3 : DÉFINITION DES PARAMÈTRES
    # ============================================================
    def definir_parametres(self, duree, frequence,
                           nom_fichier="donnees_mcc.csv", dossier="."):
        """
        Enregistre les paramètres d'acquisition.
        Appelé par GestionnairePrincipal.definir_parametres() avant le lancement.

        Args :
            duree       : durée totale en secondes
            frequence   : fréquence d'échantillonnage en Hz
                          Le USB-1808X supporte jusqu'à 200 000 Hz par voie.
            nom_fichier : nom du fichier CSV de sortie
            dossier     : chemin du dossier de sauvegarde
        """
        self.parametres.update({
            "duree"         : duree,
            "frequence"     : frequence,
            "nom_fichier"   : nom_fichier,
            "dossier_sortie": dossier
        })

    # ============================================================
    # ÉTAPE 4 : ACQUISITION TEMPS RÉEL
    # ============================================================
    def lancer_acquisition(self, dictionnaire_voies,
                           callback_maj=None, verifier_arret=None) -> bool:
        """
        Lance l'acquisition et écrit les données dans un fichier CSV.

        Stratégie par blocs :
            Au lieu de lire toute la durée d'un coup (qui nécessiterait un
            énorme buffer mémoire), on découpe en blocs de 0.1 s (ou 0.5 s
            si fréquence > 10 kHz). Pour chaque bloc :
                1. Allouer un buffer mcculw
                2. Lancer un scan bloquant (a_in_scan sans BACKGROUND)
                3. Copier les données depuis le buffer
                4. Libérer le buffer
                5. Écrire dans le CSV + appeler le callback UI

        Entrelacement mcculw :
            mcculw retourne les données entrelacées par canal :
            [ch0_t0, ch1_t0, ch0_t1, ch1_t1, ch0_t2, ch1_t2, ...]
            On doit démultiplexer avant d'utiliser les données.

        Multi-boîtiers :
            dictionnaire_voies peut contenir plusieurs boîtiers.
            On itère sur chacun et on concatène les voies dans chunk_global.

        Args :
            dictionnaire_voies : dict {nom_boitier: [liste de chemins de voies]}
                Ex: {"MCC-USB1808X-SIM-0001": ["MCC-.../ai0", "MCC-.../ai2"],
                     "MCC-USB1808X-SIM-0002": ["MCC-.../ai0"]}
            callback_maj       : fonction(temps: list, donnees: list[list])
                                 appelée après chaque bloc pour mettre à jour
                                 le graphique en temps réel dans l'UI.
            verifier_arret     : fonction() → bool, retourne True si l'utilisateur
                                 a cliqué sur "Arrêter" dans l'UI.

        Retourne : True si l'acquisition s'est terminée normalement.
        """
        ul    = self._ul
        enums = self._enums

        # Aplatissement : on construit la liste ordonnée de TOUTES les voies actives
        # (tous boîtiers confondus) pour l'en-tête CSV et le callback.
        self.chemins_voies_actives = []
        for voies in dictionnaire_voies.values():
            self.chemins_voies_actives.extend(voies)

        if not self.chemins_voies_actives:
            return False   # rien à faire

        frequence = self.parametres["frequence"]
        duree     = self.parametres["duree"]

        # Calcul de la taille des blocs de lecture
        # → 0.5 s si haute fréquence (réduction du nombre d'appels système)
        # → 0.1 s sinon (latence graphique acceptable)
        taille_bloc_sec = 0.5 if frequence > 10_000 else 0.1
        points_par_bloc = max(1, int(frequence * taille_bloc_sec))
        # Nombre total d'itérations = durée totale / durée d'un bloc
        iterations = max(1, int((duree * frequence) / points_par_bloc))

        # En-tête CSV : "temps(s)", "ai0(v)", "ai1(v)", ...
        # On extrait le nom court de la voie (ex: "ai0") depuis le chemin complet
        en_tetes = ["temps(s)"] + [
            v.split("/")[-1] + "(v)" for v in self.chemins_voies_actives
        ]
        chemin_complet = os.path.join(self.parametres["dossier_sortie"],
            self.parametres["nom_fichier"] )
        temps_ecoule = 0.0   # compteur temps absolu depuis le début de l'acquisition

        try:
            # Ouverture du CSV en écriture (écrase si déjà existant)
            with open(chemin_complet, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(en_tetes)   # première ligne = en-têtes

                # Boucle principale — une itération = un bloc temporel
                for _ in range(iterations):

                    # Vérification si l'utilisateur a demandé l'arrêt
                    if verifier_arret and verifier_arret():
                        break   # on sort proprement de la boucle

                    chunk_global = []   # données de ce bloc, toutes voies confondues

                    # ---- Lecture bloc par bloc pour chaque boîtier ----
                    for nom_boitier, voies in dictionnaire_voies.items():

                        # Récupération du numéro mcculw de ce boîtier
                        board_num = self._board_map.get(nom_boitier)
                        if board_num is None:
                            # Ce boîtier n'a pas été détecté — on saute
                            continue

                        # Calcul des bornes des canaux pour ce boîtier
                        # On extrait le numéro de voie depuis le chemin ("ai3" → 3)
                        indices   = [int(v.split("ai")[-1]) for v in voies]
                        low_chan  = min(indices)   # canal le plus bas (ex: 0)
                        high_chan = max(indices)   # canal le plus haut (ex: 3)
                        # mcculw scan toujours un range CONTIGU low→high
                        nb_canaux = high_chan - low_chan + 1
                        # Total de points dans le buffer = canaux × points/canal
                        count     = nb_canaux * points_par_bloc

                        # Allocation du buffer mémoire pour ce bloc
                        mem = ul.scaled_win_buf_alloc(count)

                        if self.mode_simulation:
                            # En simulation, on remplit le buffer avec des sinus
                            # cohérents dans le temps (on passe t_offset pour
                            # que les sinus ne reprennent pas à 0 à chaque bloc)
                            self._remplir_simulation(
                                mem, low_chan, high_chan,
                                points_par_bloc, frequence, temps_ecoule
                            )
                            # Sleep fractionné : on vérifie l'arrêt toutes les 50 ms
                            # au lieu de bloquer tout le taille_bloc_sec d'un coup
                            temps_restant = taille_bloc_sec
                            while temps_restant > 0:
                                if verifier_arret and verifier_arret():
                                    break
                                tranche = min(0.05, temps_restant)
                                time.sleep(tranche)
                                temps_restant -= tranche
                        else:
                            # En mode réel : la carte effectue le scan et remplit
                            # le buffer hardware. Appel BLOQUANT : la fonction ne
                            # revient qu'une fois tous les points_par_bloc acquis.
                            ul.a_in_scan(
                                board_num,
                                low_chan, high_chan,
                                count,
                                frequence,
                                enums.ULRange.BIP10VOLTS,
                                mem,
                                # DEFAULTIO = scan bloquant (attend la fin)
                                # SCALEDATA = convertit en volts automatiquement
                                enums.ScanOptions.DEFAULTIO |
                                enums.ScanOptions.SCALEDATA
                            )

                        # Copie du buffer (handle ctypes ou _SimBuffer) vers une
                        # liste Python standard pour pouvoir l'indexer normalement
                        flat = (ctypes.c_double * count)()  # tableau ctypes → OK
                        ul.scaled_win_buf_to_array(mem, flat, 0, count)

                        # Libération OBLIGATOIRE du buffer après chaque lecture
                        # pour éviter les fuites mémoire (surtout en mode réel)
                        ul.win_buf_free(mem)

                        # Démultiplexage : flat = [ch0_t0, ch1_t0, ch0_t1, ch1_t1, ...]
                        # On veut : canaux[0] = [v_t0, v_t1, ...], canaux[1] = [v_t0, ...]
                        canaux = [[] for _ in range(nb_canaux)]
                        for i, val in enumerate(flat):
                            # i % nb_canaux donne l'index du canal pour ce point
                            canaux[i % nb_canaux].append(val)

                        # On n'ajoute QUE les voies demandées par l'utilisateur
                        # (pas forcément toutes les voies du range low→high)
                        for voie in voies:
                            # Position relative dans le range scanné
                            idx_rel = int(voie.split("ai")[-1]) - low_chan
                            chunk_global.append(canaux[idx_rel])

                    # Construction du vecteur temps pour ce bloc
                    nouveaux_temps = [
                        temps_ecoule + j / frequence
                        for j in range(points_par_bloc)
                    ]
                    temps_ecoule += taille_bloc_sec   # avance le compteur temps

                    # Écriture CSV — toutes les colonnes en même temps via zip
                    # zip(temps, voie0, voie1, ...) génère les lignes automatiquement
                    writer.writerows(zip(nouveaux_temps, *chunk_global))

                    # Mise à jour du graphique temps réel dans l'UI
                    if callback_maj and chunk_global:
                        # Décimation : si fréquence > 5000 Hz, on n'envoie qu'1
                        # point sur 100 à l'UI (le CSV garde 100% des points).
                        # Évite de surcharger le rendu PyQtGraph.
                        pas = 100 if frequence > 5_000 else 1
                        callback_maj(
                            nouveaux_temps[::pas],            # temps décimé
                            [c[::pas] for c in chunk_global]  # données décimées
                        )

            # Réinitialisation des buffers mémoire en fin d'acquisition
            self.donnees_brutes = []
            self.temps_array    = []
            return True

        except Exception as e:
            print(f"[MCC] Erreur pendant l'acquisition : {e}")
            return False

        finally:
            # Bloc finally = exécuté même si une exception a été levée.
            # On arrête proprement les scans hardware si nécessaire.
            if not self.mode_simulation:
                for nom_boitier in dictionnaire_voies:
                    board_num = self._board_map.get(nom_boitier)
                    if board_num is not None:
                        try:
                            # stop_background : utile si un scan BACKGROUND était
                            # actif (ici nos scans sont DEFAULTIO donc déjà finis,
                            # mais on l'appelle par sécurité)
                            ul.stop_background(board_num,
                                               enums.FunctionType.AIFUNCTION)
                        except Exception:
                            pass   # si déjà arrêté, l'erreur est ignorée

    # ----------------------------------------------------------------
    def _remplir_simulation(self, mem, low_chan, high_chan,
                             pts, frequence, t_offset):
        """
        Génère des signaux simulés dans le buffer 'mem' en format entrelacé.

        Contrairement à _MockUL.a_in_scan (qui repart toujours à t=0),
        cette méthode prend t_offset en paramètre pour que les sinusoïdes
        soient continues d'un bloc à l'autre — les courbes du graphique
        ne "redémarrent" pas à chaque itération.

        Signaux générés :
            Canal low_chan+c  :  amp/(c+1) * sin(2π * (c+1)*10 * t)  + bruit
            → amplitude décroissante, fréquence croissante par canal

        Args :
            mem       : _SimBuffer à remplir
            low_chan  : indice du premier canal (pour le calcul de fréquence)
            high_chan : indice du dernier canal
            pts       : points par canal pour ce bloc
            frequence : fréquence d'échantillonnage (pour calculer t)
            t_offset  : temps absolu du début de ce bloc (en secondes)
        """
        nb_canaux = high_chan - low_chan + 1
        for j in range(pts):
            # Temps absolu du point j, en continuité avec les blocs précédents
            t = t_offset + j / frequence
            for c in range(nb_canaux):
                freq_sig = 10.0 * (c + low_chan + 1)   # fréquence unique par canal
                amp      = 2.0  / (c + low_chan + 1)   # amplitude décroissante
                val = (amp * math.sin(2 * math.pi * freq_sig * t)
                       + random.gauss(0, 0.02))          # + bruit blanc gaussien
                # Stockage entrelacé — même format que le hardware réel
                mem._data[j * nb_canaux + c] = val

    # ============================================================
    # TRAITEMENT DES DONNÉES (formules de conversion)
    # ============================================================
    def appliquer_traitement(self, voie, valeur_brute):
        """
        Applique une formule de conversion selon le type de capteur.
        La carte retourne des tensions (0–10 V ou ±10 V).
        Cette méthode convertit en unité physique (bar, °C, Hz…).

        Les formules ci-dessous sont des EXEMPLES à adapter selon
        les fiches techniques des capteurs utilisés dans le laboratoire.

        Args :
            voie         : chemin complet de la voie (ex: "MCC-.../ai0")
            valeur_brute : tension en volts retournée par la carte

        Retourne : valeur convertie en unité physique (float)
        """
        # Récupération du type de capteur configuré pour cette voie
        t = self.config_sondes.get(voie, {}).get("type", "Tension")

        if t == "Pression":
            # Exemple : capteur 4-20 mA ou 0-10 V → 0-25 bar
            # À remplacer par la formule de votre capteur
            return valeur_brute * 2.5

        if t == "Temperature":
            # Exemple : thermocouple amplifié 0-1 V → 0-100 °C
            return valeur_brute * 100.0

        if t == "Frequence":
            # Exemple : sortie fréquence 0-10 V → 0-100 Hz
            return abs(valeur_brute) * 10.0

        # Par défaut (Tension) : pas de conversion, on retourne les volts
        return valeur_brute

    # ============================================================
    # SAUVEGARDE DE SECOURS (données en mémoire → CSV)
    # ============================================================
    def sauvegarder_brut_csv(self) -> bool:
        """
        Sauvegarde de secours si les données n'ont pas été écrites en temps réel.
        En pratique, lancer_acquisition() écrit directement en CSV donc ce cas
        ne devrait pas arriver, mais on le garde comme filet de sécurité.

        Retourne : True si la sauvegarde a réussi.
        """
        if not self.donnees_brutes or not self.temps_array:
            print("[MCC] Aucune donnée en mémoire à sauvegarder.")
            return False

        chemin   = os.path.join(self.parametres["dossier_sortie"],
                                self.parametres["nom_fichier"])
        en_tetes = ["temps(s)"] + [
            v.split("/")[-1] + "(v)" for v in self.chemins_voies_actives
        ]
        try:
            with open(chemin, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(en_tetes)
                for i, t in enumerate(self.temps_array):
                    # round() pour limiter la taille du fichier CSV
                    ligne = [round(t, 4)] + [
                        round(self.donnees_brutes[c][i], 6)
                        for c in range(len(self.chemins_voies_actives))
                    ]
                    writer.writerow(ligne)
            return True
        except Exception as e:
            print(f"[MCC] Erreur sauvegarde : {e}")
            return False

    # ============================================================
    # TEST DE CONNEXION (appelé avant l'acquisition)
    # ============================================================
    def tester_connexions(self, dictionnaire_voies) -> list:
        """
        Vérifie que chaque voie demandée est réellement lisible.
        Appelé par GestionnairePrincipal.tester_connexions() juste avant
        de lancer l'acquisition pour détecter les problèmes tôt.

        En simulation : toujours OK (retourne liste vide).
        En mode réel  : tente un mini-scan de 10 points sur chaque voie.

        Args :
            dictionnaire_voies : même format que lancer_acquisition()

        Retourne :
            liste de tuples (nom_boitier, nom_voie) pour les voies en échec.
            Liste vide = tout est OK.
        """
        if self.mode_simulation:
            return []   # en simulation, toutes les voies fonctionnent toujours

        ul    = self._ul
        enums = self._enums
        voies_en_echec = []

        for nom_boitier, voies in dictionnaire_voies.items():
            board_num = self._board_map.get(nom_boitier)
            if board_num is None:
                # Boîtier non enregistré (pas détecté lors du scan)
                voies_en_echec += [(nom_boitier, v) for v in voies]
                continue

            for voie in voies:
                try:
                    # Test minimal : scan de 10 points à 100 Hz sur cette voie seule
                    idx = int(voie.split("ai")[-1])
                    buf = ul.scaled_win_buf_alloc(10)
                    ul.a_in_scan(
                        board_num, idx, idx,   # une seule voie
                        10, 100,               # 10 points à 100 Hz
                        enums.ULRange.BIP10VOLTS,
                        buf,
                        enums.ScanOptions.DEFAULTIO | enums.ScanOptions.SCALEDATA
                    )
                    ul.win_buf_free(buf)
                    # Si on arrive ici sans exception → voie OK

                except Exception as e:
                    print(f"[MCC] Échec sur la voie {voie} : {e}")
                    voies_en_echec.append((nom_boitier, voie))

        return voies_en_echec

    # ============================================================
    # LIBÉRATION DES RESSOURCES
    # ============================================================
    def liberer(self):
        """
        Libère toutes les ressources driver MCC.
        À appeler dans closeEvent() de la fenêtre principale WaveLab.

        En mode réel : ul.release_daq_device() libère le slot board_num
        dans la Universal Library et permet à d'autres applications
        (InstaCal, DAQami…) d'accéder aux cartes sans conflit.

        En simulation : juste nettoyage du dict interne.
        """
        if not self.mode_simulation:
            for nom, board_num in self._board_map.items():
                try:
                    self._ul.release_daq_device(board_num)
                    print(f"[MCC] Board {board_num} ({nom}) libéré.")
                except Exception as e:
                    print(f"[MCC] Erreur libération board {board_num} : {e}")

        # Nettoyage du registre dans tous les cas
        self._board_map.clear()


# ================================================================================
# TEST EN LIGNE DE COMMANDE
# Lancé avec : python GestionnaireMCC.py
# Permet de tester le gestionnaire sans lancer toute l'interface PyQt.
# ================================================================================
if __name__ == "__main__":
    print("=" * 50)
    print("  Test GestionnaireMCC (mcculw)")
    print("=" * 50)

    # Change mode_simulation=False pour tester avec le vrai matériel
    mcc = GestionnaireMCC(mode_simulation=True)

    if mcc.initialiser_systeme():
        print(f"\nBoîtiers détectés :")
        for b in mcc.boitiers_detectes:
            print(f"  → {b['nom']} ({b['total_voies']} voies)"
                  f"  {'[SIMULÉ]' if b['simule'] else '[RÉEL]'}")

        # Test sur les 2 premières voies du premier boîtier
        boitier_nom = mcc.boitiers_detectes[0]["nom"]
        voies_test  = {boitier_nom: mcc.voies_disponibles[:2]}

        mcc.definir_parametres(
            duree=3, frequence=500, nom_fichier="test_mcc.csv"
        )

        def cb(temps, donnees):
            # Affiche le premier point de chaque bloc pour vérification
            print(f"  t={temps[0]:.3f}s | "
                  f"ai0={donnees[0][0]:.4f} V | ai1={donnees[1][0]:.4f} V")

        print(f"\nAcquisition 3 s à 500 Hz sur {boitier_nom} :")
        ok = mcc.lancer_acquisition(voies_test, callback_maj=cb)

        print(f"\n→ Acquisition {'réussie — fichier test_mcc.csv créé' if ok else 'ÉCHOUÉE'}")

        # Nettoyage
        mcc.liberer()

    else:
        print("\nAucun boîtier MCC détecté.")
        print("Vérifier :")
        print("  1. MCC DAQ Software installé (InstaCal)")
        print("  2. pip install mcculw")
        print("  3. Carte branchée en USB")