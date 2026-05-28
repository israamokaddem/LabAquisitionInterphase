import os
import time
import csv
import nidaqmx
from nidaqmx.constants import AcquisitionType


class GestionnaireNI:
    def __init__(self):
        self.boitier = None
        self.voies_disponibles = []
        self.voies_selectionnees = []
        self.config_sondes = {}  # Format: {'Nom_Voie': {'type': 'Pression', 'unite': 'p'}}
        self.parametres = {
            "frequence": 1000,
            "duree": 0,
            "nom_fichier": "donnees.csv",
            "dossier_sortie": "."
        }
        self.donnees_brutes = []

    # ==========================================
    # ÉTAPE 1 & 2 : DÉTECTION
    # ==========================================
    def initialiser_systeme(self):
        print("\n--- ÉTAPE 1 : DÉTECTION DU MATÉRIEL ---")
        system = nidaqmx.system.System.local()

        if not system.devices:
            print("❌ Aucun périphérique NI détecté.")
            return False

        # On parcourt TOUS les appareils (châssis ET modules)
        for appareil in system.devices:
            # On vérifie si cet appareil possède des voies d'entrée analogique
            voies = [ch.name for ch in appareil.ai_physical_chans]
            if len(voies) > 0:
                self.boitier = appareil
                self.voies_disponibles = voies
                break# On a trouvé notre module, on arrête la recherche

        # Si après la boucle, on n'a rien trouvé
        if not self.boitier:
            print("❌ Le châssis est détecté, mais aucun module d'entrée analogique n'a été trouvé.")
            print("Astuce : Vérifiez dans NI MAX que le module simulé est bien inséré dans l'emplacement 1.")
            return False

        print(f"✅ Module d'acquisition détecté : {self.boitier.name} ({self.boitier.product_type})")
        return True

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
    # ÉTAPE 4 : PARAMÈTRES ET ACQUISITION
    # ==========================================
    def configurer_parametres(self):
        print("\n--- ÉTAPE 4 : PARAMÈTRES D'ACQUISITION ---")
        self.parametres["duree"] = float(input("Durée de l'acquisition (en secondes) : "))
        self.parametres["frequence"] = float(input("Fréquence d'échantillonnage (en Hz, ex: 1000) : "))
        self.parametres["nom_fichier"] = input("Nom du fichier de sortie (ex: test1.csv) : ")

        dossier = input("Chemin du dossier de sortie (Laissez vide pour le dossier courant) : ")
        if dossier.strip():
            self.parametres["dossier_sortie"] = dossier

    def lancer_acquisition(self):
        print("\n--- LANCEMENT DE L'ACQUISITION ---")
        nombre_points = int(self.parametres["frequence"] * self.parametres["duree"])

        try:
            with nidaqmx.Task() as task:
                # Ajout de TOUTES les voies sélectionnées à la tâche
                for voie in self.voies_selectionnees:
                    task.ai_channels.add_ai_voltage_chan(voie)

                # Configuration de l'horloge
                task.timing.cfg_samp_clk_timing(
                    rate=self.parametres["frequence"],
                    sample_mode=AcquisitionType.FINITE,
                    samps_per_chan=nombre_points
                )

                print(f"Acquisition en cours de {nombre_points} points sur {len(self.voies_selectionnees)} voies...")

                # Lecture des données.
                # Si 1 voie -> retourne une liste [v1, v2, v3...]
                # Si >1 voie -> retourne une liste de listes [[voie1_v1, voie1_v2...], [voie2_v1, voie2_v2...]]
                donnees = task.read(
                    number_of_samples_per_channel=nombre_points,
                    timeout=self.parametres["duree"] + 5.0
                )  #attendre la duree de l'aqiisition+ 5 secondes avant de tout recuperer

                # Formatage des données : on s'assure d'avoir toujours une liste de listes
                if len(self.voies_selectionnees) == 1:
                    self.donnees_brutes = [donnees]
                else:
                    self.donnees_brutes = donnees

            print("✅ Acquisition terminée !")
            return True

        except nidaqmx.errors.DaqError as e:
            print(f"❌ Erreur NI-DAQmx : {e}")
            return False
    # ==========================================
    # MÉTHODES DE TRAITEMENT ET SAUVEGARDE
    # ==========================================
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

    def sauvegarder_csv(self):
        chemin_complet = os.path.join(self.parametres["dossier_sortie"], self.parametres["nom_fichier"])

        # 1. Préparation de l'en-tête (ex: temps(s), ai0(v), ai1(p))
        en_tetes = ["temps(s)"]
        for voie in self.voies_selectionnees:
            # On extrait juste "ai0" de "cDAQ9184Mod1/ai0" pour faire plus propre
            nom_court = voie.split('/')[-1]
            unite = self.config_sondes[voie]["unite"]
            en_tetes.append(f"{nom_court}({unite})")

        # 2. Écriture du fichier
        with open(chemin_complet, mode='w', newline='') as fichier:
            writer = csv.writer(fichier)
            writer.writerow(en_tetes)

            # Utilisation de zip(*donnees) pour transposer les colonnes en lignes
            # Exemple : [[1,2], [3,4]] devient (1,3), (2,4)
            nb_points = len(self.donnees_brutes[0])
            for i in range(nb_points):
                temps_relatif = round(i / self.parametres["frequence"], 4)

                ligne = [temps_relatif]
                for index_voie, voie in enumerate(self.voies_selectionnees):
                    valeur_brute = self.donnees_brutes[index_voie][i]
                    valeur_traitee = self.appliquer_traitement(voie, valeur_brute)
                    ligne.append(round(valeur_traitee, 6))

                writer.writerow(ligne)

        print(f"\n✅ Fichier sauvegardé avec succès : {chemin_complet}")


# ==========================================
# EXÉCUTION DU SCRIPT DE TEST
# ==========================================
if __name__ == "__main__":
    systeme_ni = GestionnaireNI()

    if systeme_ni.initialiser_systeme():
        systeme_ni.configurer_voies()
        systeme_ni.configurer_parametres()
        systeme_ni.lancer_acquisition()
        systeme_ni.sauvegarder_csv()