from PyQt6.QtCore import QThread, pyqtSignal


class AcquisitionThread(QThread):
    # AJOUT : Un troisième paramètre 'list' pour transmettre les numéros des courbes
    maj_graphique = pyqtSignal(list, list, list)
    acquisition_terminee = pyqtSignal(bool)

    def __init__(self, gestionnaire, dico_voies):
        super().__init__()
        self.gestionnaire = gestionnaire
        self.dico_voies = dico_voies
        self.arret_demande = False

    def run(self):
        # Le callback accepte maintenant les indices envoyés par le Chef d'Orchestre
        def callback(temps, donnees, indices=None):
            if indices is None:
                indices = list(range(len(donnees)))
            self.maj_graphique.emit(temps, donnees, indices)

        def check_arret():
            return self.arret_demande

        succes = self.gestionnaire.lancer_acquisition(
            self.dico_voies,
            callback_maj=callback,
            verifier_arret=check_arret
        )
        self.acquisition_terminee.emit(succes)

    def stop(self):
        self.arret_demande = True