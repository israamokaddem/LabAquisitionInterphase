import os
from abc import ABC, abstractmethod


class GestionnaireAquisition(ABC):

    @abstractmethod
    def initialiser_systeme(self):
        """Détecte le matériel et remplit la liste des boîtiers détectés."""
        pass

    @abstractmethod
    def configurer_voies(self):
        """Gère la sélection et le typage des voies de capteurs."""
        pass

    @abstractmethod
    def definir_parametres(self, duree, frequence, nom_fichier="donnees.csv", dossier="."):
        """Enregistre les paramètres de configuration de l'essai."""
        pass

    @abstractmethod
    def lancer_acquisition(self, dictionnaire_voies, callback_maj=None, verifier_arret=None):
        """Lance la boucle d'acquisition en temps réel."""
        pass

    @abstractmethod
    def appliquer_traitement(self, voie, valeur_brute):
        """Applique les formules de conversion selon le type de sonde."""
        pass

    @abstractmethod
    def sauvegarder_brut_csv(self):
        """Sauvegarde d'urgence ou de secours des données en mémoire."""
        pass