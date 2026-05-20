import numpy as np
import scipy.fft
import pandas as pd


class DSP:
    def __init__(self, data, selected_columns=None, time_column_index=0):
        """
        Constructeur de la classe DSP.

        :param data: Le DataFrame Pandas contenant les signaux.
        :param selected_columns: Liste des noms de colonnes à analyser (ex: ['S1', 'S2']).
        :param time_column_index: Index de la colonne temps (par défaut 0).
        """
        self.data = data
        self.selected_columns = selected_columns if selected_columns else []
        self.time_column= time_column_index

        # Attributs de stockage des résultats après calcul
        self.frequencies = None
        self.results = {}  # Dictionnaire {nom_colonne: valeurs_dsp}

    def DSP_Standard(self, time, eta):
        '''
        Méthode 1 : Calcul avec facteur 2 (spectre unilatéral)
        '''
        N = len(eta)
        # Calcul de la fréquence d'échantillonnage
        Fs = 1 / (time[1] - time[0])

        # Transformée de Fourier
        tf = scipy.fft.fft(eta)

        # Calcul de la DSP : facteur 2 car on coupe le spectre en deux (fréquences positives)
        dsp = 2 * (np.abs(tf) ** 2) / (N * Fs)

        # Vecteur fréquence
        f = (Fs / 2) * np.linspace(0, 1, int(N / 2))

        # On retourne la moitié du vecteur (fréquences positives uniquement)
        return f[:len(f) // 2], dsp[:len(f) // 2]

    def DSP_Conjuguee(self, time, signal):
        '''
        Méthode 2 : Calcul via produit conjugué avec vérification de taille
        '''
        if len(time) != len(signal):
            raise ValueError(f"DSP ERROR : Time and temporal signal have not the same size: "
                             f"{len(time)} for time and {len(signal)} for signal")

        NombreDonnee = len(signal)
        timeStep = time[1] - time[0]
        Fe = 1 / timeStep

        # Transformée de Fourier
        tf = scipy.fft.fft(signal)

        # Calcul via le produit conjugué
        dsp = (tf * tf.conjugate()) / (NombreDonnee * Fe)

        # Vecteur fréquence
        f = (Fe / 2) * np.linspace(0, 1, NombreDonnee // 2)

        # On retourne f et la partie réelle de la DSP (car le produit conjugué peut laisser un 0j)
        return f, dsp[:NombreDonnee // 2].real

    def executer_calcul(self, methode="Standard"):
        """
        Lance le calcul sur toutes les colonnes sélectionnées.
        :param methode: "Standard" ou "Conjuguee"
        """
        if self.data is None:
            raise ValueError("Aucune donnée disponible pour le calcul.")

        # Récupération du temps
        time = self.data.iloc[:, self.time_column].values
        self.results = {}

        for col in self.selected_columns:
            signal = self.data[col].values

            if methode == "Standard":
                f, dsp_val = self.DSP_Standard(time, signal)
            else:
                f, dsp_val = self.DSP_Conjuguee(time, signal)

            self.frequencies = f  # Le vecteur fréquence est le même pour toutes les colonnes
            self.results[col] = dsp_val

        return self.frequencies, self.results


# --- Exemple d'utilisation (Similaire au bloc de test de Decomposition) ---
if __name__ == "__main__":
    # Simulation de données
    t = np.linspace(0, 10, 1000)
    s1 = np.sin(2 * np.pi * 1.5 * t) + 0.5 * np.random.randn(1000)
    df = pd.DataFrame({'Time': t, 'S1': s1})

    # Initialisation
    moteur_dsp = DSP(data=df, selected_columns=['S1'])

    # Calcul
    freq, res = moteur_dsp.executer_calcul(methode="Standard")
    print(f"Calcul terminé. Nombre de points fréquentiels : {len(freq)}")
    print(f"Max DSP pour S1 : {np.max(res['S1'])}")