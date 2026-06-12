import os
import time
import csv
import nidaqmx
from nidaqmx.constants import AcquisitionType
from GestionnaireAquisition import GestionnaireAquisition

class GestionnaireNI(GestionnaireAquisition):
    def __init__(self):
        super().__init__()
        self.boitier = None
        self.voies_disponibles = []
        self.voies_selectionnees = []
        self.config_sondes = {}
        self.parametres = {
            "frequence": 1000,
            "duree": 0,
            "nom_fichier": "donnees.csv",
            "dossier_sortie": "."
        }
        self.donnees_brutes = []

        # NOUVEAU : Liste pour stocker tous les boîtiers trouvés pour l'interface
        self.boitiers_detectes = []
        self.chemins_voies_actives = []
#===========================================
# ÉTAPE 1 : DÉTECTION
# ==========================================
    def initialiser_systeme(self):
        """
        Détecte tous les périphériques NI connectés ayant des voies analogiques.
        Retourne True si au moins un appareil est trouvé, sinon False.
        """
        self.boitiers_detectes.clear()  # On vide la liste avant de scanner
        self.boitiers_detectes = []
        try:
            import nidaqmx
            from nidaqmx.constants import TaskMode
            system = nidaqmx.system.System.local()

            if not system.devices:
                return False

            # On parcourt TOUS les appareils
            for appareil in system.devices:
                voies = [ch.name for ch in appareil.ai_physical_chans]

                if len(voies) > 0:
                    try:
                        # LE VRAI TEST INFAILLIBLE :
                        # On simule la création d'une tâche sur la première voie trouvée
                        with nidaqmx.Task() as test_task:
                            test_task.ai_channels.add_ai_voltage_chan(voies[0])

                            # On force NI-DAQmx à vérifier physiquement le matériel
                            test_task.control(TaskMode.TASK_VERIFY)

                        # Si on arrive ici sans erreur, le boîtier est vraiment en ligne !
                        self.boitiers_detectes.append({
                            "nom": appareil.name,
                            "modele": appareil.product_type,
                            "total_voies": len(voies),
                            "voies_dispos": voies
                        })

                        if not self.voies_disponibles:
                            self.voies_disponibles = voies

                    except nidaqmx.errors.DaqError:
                        # La vérification a échoué : le boîtier est mémorisé par NI MAX mais injoignable physiquement
                        continue

            # S'il n'y a aucun boîtier valide dans la liste
            if len(self.boitiers_detectes) == 0:
                return False

            return True

        except Exception as e:
            print(f"Erreur de détection matérielle : {e}")
            return False


# ==========================================
# ÉTAPE 3 : SÉLECTION ET TYPAGE DES VOIES
# ==========================================

    def configurer_voies(self):
        print("\n--- ÉTAPE 2 & 3 : SÉLECTION DES SONDES ---")
        print("Voies physiques disponibles :")
        for i, voie in enumerate(self.voies_disponibles):
            print(f"  [{i}] {voie}")

        choix = input("\nEntrez les numéros des voies à utiliser séparés par des virgules (ex: 0,1,3) : ")
        index_choisis = [int(x.strip()) for x in choix.split(',')]

        # Dictionnaire d'unités simples pour générer l'en-tête CSV
        unites = {"Tension": "v", "Pression": "p", "Frequence": "hrtz", "Temperature": "c"}

        for idx in index_choisis:
            voie = self.voies_disponibles[idx]
            self.voies_selectionnees.append(voie)

            print(f"\nConfiguration de la sonde sur {voie} :")
            print("Types disponibles : 1. Tension | 2. Pression | 3. Frequence | 4. Temperature")
            choix_type = input("Choisissez le type de mesure (1-4) : ")

            type_mesure = list(unites.keys())[int(choix_type) - 1]
            unite = unites[type_mesure]

            self.config_sondes[voie] = {"type": type_mesure, "unite": unite}



# ==========================================
# MÉTHODES DE TRAITEMENT ET SAUVEGARDE
# ==========================================
    # ==========================================
    # ÉTAPE 4 : PARAMÈTRES ET ACQUISITION TEMPS RÉEL
    # ==========================================
    def definir_parametres(self, duree, frequence, nom_fichier="donnees.csv", dossier="."):
        """
        Reçoit les paramètres directement depuis l'interface PyQt (sans input() bloquant).
        """
        self.parametres["duree"] = duree
        self.parametres["frequence"] = frequence
        self.parametres["nom_fichier"] = nom_fichier
        self.parametres["dossier_sortie"] = dossier

    def lancer_acquisition(self, dictionnaire_voies, callback_maj=None, verifier_arret=None):
        import os
        import csv
        import nidaqmx
        from nidaqmx.constants import AcquisitionType

        total_voies = sum(len(voies) for voies in dictionnaire_voies.values())
        if total_voies == 0: return False

        frequence = self.parametres["frequence"]
        duree = self.parametres["duree"]

        # Si on est à très haute fréquence (> 10 000 Hz), on lit par gros blocs de 0.5s
        # pour donner moins de travail de découpage au processeur. Sinon 0.1s.
        taille_bloc_sec = 0.5 if frequence > 10000 else 0.1
        points_par_paquet = int(frequence * taille_bloc_sec)
        if points_par_paquet == 0: points_par_paquet = 1

        iterations = int((duree * frequence) / points_par_paquet)

        self.chemins_voies_actives = []
        for nom_boitier, voies in dictionnaire_voies.items():
            for voie in voies:
                self.chemins_voies_actives.append(voie)

        en_tetes = ["temps(s)"] + [v.split('/')[-1] + "(v)" for v in self.chemins_voies_actives]
        chemin_complet = os.path.join(self.parametres["dossier_sortie"], self.parametres["nom_fichier"])
        temps_ecoule = 0.0

        try:
            with nidaqmx.Task() as task:
                for voie in self.chemins_voies_actives:
                    task.ai_channels.add_ai_voltage_chan(voie)

                task.timing.cfg_samp_clk_timing(
                    rate=frequence,
                    sample_mode=AcquisitionType.CONTINUOUS
                )

                # --- CORRECTION 1 : LE GRAND RÉSERVOIR ---
                # On force la carte à allouer un énorme buffer de 5 secondes dans la RAM
                task.in_stream.input_buf_size = int(frequence * 5)

                with open(chemin_complet, mode='w', newline='') as fichier:
                    writer = csv.writer(fichier)
                    writer.writerow(en_tetes)

                    task.start()

                    for _ in range(iterations):
                        if verifier_arret and verifier_arret():
                            break

                            # Lecture du paquet avec un délai (timeout) généreux
                        chunk = task.read(number_of_samples_per_channel=points_par_paquet, timeout=5.0)
                        if total_voies == 1: chunk = [chunk]

                        nouveaux_temps = [temps_ecoule + (i / frequence) for i in range(points_par_paquet)]
                        temps_ecoule += taille_bloc_sec

                        # On écrit 100% des points dans le CSV (Ultra rapide)
                        lignes = zip(nouveaux_temps, *chunk)
                        writer.writerows(lignes)

                        # --- CORRECTION 2 : ALLÉGER LE GRAPHIQUE ---
                        # Si la fréquence est énorme, on "triche" visuellement pour ne pas faire lagger l'UI
                        if callback_maj:
                            pas = 100 if frequence > 5000 else 1
                            # On ne prend qu'un point sur 'pas' (ex: 1 point sur 100)
                            temps_visu = nouveaux_temps[::pas]
                            chunk_visu = [donnees_voie[::pas] for donnees_voie in chunk]

                            callback_maj(temps_visu, chunk_visu)

            self.donnees_brutes = []
            self.temps_array = []
            return True

        except Exception as e:
            print(f"Erreur DAQ : {e}")
            return False





    def appliquer_traitement(self, voie, valeur_brute):
        """
        Ici, tu pourras ajouter tes formules mathématiques selon le type de capteur.
        Exemple : convertir un voltage (0-10V) en pression (0-5 bars).
        """
        type_sonde = self.config_sondes[voie]["type"]

        if type_sonde == "Pression":
            # Formule factice pour l'exemple
            return valeur_brute * 2.5
        elif type_sonde == "Frequence":
            # Formule factice pour l'exemple
            return valeur_brute * 10.0
        # Par défaut (Tension)
        return valeur_brute


    # ==========================================
    # ÉTAPE 5 : SAUVEGARDE DES DONNÉES
    # ==========================================
    def sauvegarder_brut_csv(self):
        """
        Sauvegarde les valeurs brutes (Volts) acquises en temps réel.
        """
        import os
        import csv

        # Sécurité : vérifier qu'il y a bien des données à sauvegarder
        if not hasattr(self, 'donnees_brutes') or not self.donnees_brutes or not self.temps_array:
            print("Erreur : Aucune donnée en mémoire à sauvegarder.")
            return False

        chemin_complet = os.path.join(self.parametres["dossier_sortie"], self.parametres["nom_fichier"])

        # 1. En-têtes (On utilise la bonne variable : chemins_voies_actives !)
        en_tetes = ["temps(s)"]
        for voie in self.chemins_voies_actives:
            # On extrait juste "ai0" de "cDAQ9184Mod1/ai0" pour faire un nom de colonne propre
            nom_court = voie.split('/')[-1]
            en_tetes.append(f"{nom_court}(v)")

        try:
            with open(chemin_complet, mode='w', newline='') as fichier:
                writer = csv.writer(fichier)
                writer.writerow(en_tetes)

                # 2. Écriture des lignes
                nb_points = len(self.temps_array)
                for i in range(nb_points):
                    # Colonne 1 : Le temps
                    ligne = [round(self.temps_array[i], 4)]

                    # Colonnes suivantes : Les données brutes pour chaque voie
                    for index_voie in range(len(self.chemins_voies_actives)):
                        valeur = self.donnees_brutes[index_voie][i]
                        ligne.append(round(valeur, 6))

                    writer.writerow(ligne)

            print(f"sauvegarde réussie : {chemin_complet}")
            return True

        except Exception as e:
            print(f"Erreur lors de la sauvegarde : {e}")
            return False

    def tester_connexions(self, dictionnaire_voies):
        """
        Teste si les voies sélectionnées sont réellement lisibles par le matériel.
        Retourne une liste de tuples (boitier, voie) qui ont échoué.
        """
        import nidaqmx
        from nidaqmx.constants import TaskMode

        voies_en_echec = []

        for boitier, voies in dictionnaire_voies.items():
            for voie in voies:
                try:
                    # On crée une micro-tâche jetable pour tester
                    with nidaqmx.Task() as task:
                        task.ai_channels.add_ai_voltage_chan(voie)
                        # TASK_VERIFY demande à la carte de valider la voie sans lancer la lecture
                        task.control(TaskMode.TASK_VERIFY)
                except Exception as e:
                    print(f"Erreur détectée sur la voie {voie} : {e}")
                    voies_en_echec.append((boitier, voie))

        return voies_en_echec
# ==========================================
# EXÉCUTION DU SCRIPT DE TEST
# ==========================================
if __name__ == "__main__":
    systeme_ni = GestionnaireNI()

    if systeme_ni.initialiser_systeme():
        systeme_ni.configurer_voies()

        # Correction des noms des méthodes de test pour correspondre à la classe
        systeme_ni.definir_parametres(duree=5, frequence=1000, nom_fichier="donnees_ni_test.csv")

        if len(systeme_ni.boitiers_detectes) > 0:
            boitier_nom = systeme_ni.boitiers_detectes[0]["nom"]
            # On prend la première voie disponible pour le test
            dict_voies_test = {boitier_nom: [systeme_ni.voies_disponibles[0]]}

            systeme_ni.lancer_acquisition(dictionnaire_voies=dict_voies_test)