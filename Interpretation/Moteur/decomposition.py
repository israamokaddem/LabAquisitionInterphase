"""
written by @paul.tournant
march 2023

Modified and commented by @yasmine.benbelkacem
September 2023
April 2024

# Adapt experimental functions to the present case
# Adapt some functions to the numerical data
# Save data

"""

# Adapt experimental functions to the present case
# Adapt some functions to the numerical data
# Save data


# =====================================
# ==> Python packages Importations <==
# =====================================

import numpy as np
import scipy.fft
from scipy.optimize import newton


class Decomposition:
    def __init__(self, data, ProbeSpacing=None, depth=2, g=9.81, Irreg=False):
        """
        Constructeur de la classe de traitement.

        :param df: Le DataFrame Pandas contenant les données chargées.
        :param ProbeSpacing: Liste ou Array des positions X des sondes (ex: [0, 0.45, 1.2, 2.0]).
        :param depth: La profondeur d'eau (float) en mètres.
        :param g: Constante de gravité (par défaut 9.81).
        """
        # 1. Stockage des paramètres de base
        if ProbeSpacing is None:
            ProbeSpacing = [1, 2, 0.5, 10]
        self.data = data
        self.depth = depth
        self.g = g

        # 2. On s'assure que spacing est un array NumPy (plus rapide pour les calculs)
        self.ProbeSpacing = np.array(ProbeSpacing)
        self.Irreg= Irreg
        self.variables = ["ProbeSpacing", "Depth", "Gain"]

    def RelationDisp(self, omega, tolerence):
        """
        This function relates on the dispersion relation
        and returns the wave number k using the Newton-Raphson method:
            k_(i+1) = k_(i) - f(k_i)/f'(k_i)

        The loop start from the initial guess x0 and iterates until
        the result converges to the specified tolerance.
        """

        def z(x):
            y = x * np.tanh(x * self.depth) - (omega ** 2) / self.g  # Dispersion equation (1)
            return y

        def z2(x):
            y = np.tanh(x * self.depth) + x * self.depth * (
                        1 - np.tanh(x * self.depth) ** 2)  # Derivative of the dispersion equation (1)
            return y

        k = newton(x0=np.pi / (1.95 * self.depth), func=z, fprime=z2, tol=tolerence, maxiter=10000)
        # print('omega :',omega,' , k :',k,' , lambda :',2*np.pi/k)
        return k

    def RelationDisp_freewave(self,omega, tolerence, n):
        """
        USed in liu & Huang method and Lykke Andersen & Eldrub method
        where n represent the order
        """

        def z(x):
            y = x * np.tanh(x * self.depth) - ((n * omega) ** 2) / self.g  # Dispersion equation (1)
            return y

        def z2(x):
            y = np.tanh(x * self.depth) + x * self.depth * (
                        1 - np.tanh(x * self.depth) ** 2)  # Derivative of the dispersion equation (1)
            return y

        k_n = newton(x0=np.pi / (1.95 * self.depth), func=z, fprime=z2, tol=tolerence, maxiter=10000)
        # print('omega :',omega,' , k_n :',k_n,' , lambda_n :',2*np.pi/k_n)
        return k_n

    def RelationDisp_fifthOrder(self, omega, H, tolerence):
        def f(k):
            y = -omega / k * np.sqrt(k / self.g) + T(k) + (k * H / 2) ** 2 * T(k) * (
                    (2 + 7 * S(k) ** 2) / (4 * (1 - S(k)) ** 2)) + (k * H / 2) ** 4 * T(k) * (
                        (4 + 32 * S(k) - 116 * S(k) ** 2 - 400 * S(k) ** 3 - 71 * S(k) ** 4 + 146 * S(k) ** 5) / (
                        32 * (1 - S(k)) ** 5))
            return y

        def S(x):
            y = 1 / (np.cosh(2 * x * self.depth))
            return y

        def T(x):
            y = np.sqrt(np.tanh(x * self.depth))
            return y

        a, b = 0.001, 100
        while abs(b - a) > tolerence:
            m = (a + b) / 2
            if (f(a) * f(m) <= 0):
                b = m
            else:
                a = m
        return a


    def findMaxFrequency(self) -> list:
        """
        Function to find the fundamental frequency

        INPUT:
            - data[i,j] : array obtained by np.loadtxt
                - data[0,:] : time serie
                - data[i,:] : temporal series
        """
        # Utilisation de self.data directement
        t = self.data.iloc[:, 0].values
        # On prend toutes les colonnes sauf la première (le temps)
        S = self.data.iloc[:, 1:].values

        NombreDonnee = len(t)
        timeStep = t[1] - t[0]

        f = (1 / timeStep) / 2 * np.linspace(0, 1, int(NombreDonnee / 2))
        f0 = []
        for i in range(len(S[0, :])):
            tf = scipy.fft.fft(S[:, i])
            dsp = (tf * tf.conjugate()) / NombreDonnee ** 2
            # plt.figure()
            # plt.plot(f,abs(dsp[:int(NombreDonnee/2)]))
            # plt.show()
            ## AVANT:fmaxIndex = int(list(dsp[10:int(NombreDonnee / 2)]).index(max(dsp[10:int(NombreDonnee / 2)])) + 10)
            fmaxIndex = int(np.argmax(np.abs(dsp[10:int(NombreDonnee / 2)])) + 10) ##APRES CORRECTION
            f0.append(f[fmaxIndex])

        return f0

    def WaveProbeDecomposition(self,selected_columns):
        """
        This function breaks down the signal into:
             - Incident part
             - Reflected part
        INPUT:
            - data[0] = time series;
            - data[1:Nb_Probes+1] = Free surface elevation @ probes 1...Nb_Probe+1;
            - Dir = Path to the file location;
            - ProbeSpacing : Spacing between probes to perform the wave decomposition.
            - Irreg: is for the irregular wave calculation, spectrum is integer betwenn fp/2 and fp*4.5, where fp is the fundamental frequency
              When it is set to False, the regular calculation integer the spectrum between fp*0.9 and fp*1.1, to take in account the harmonic effect,
              you could be integer on a more large frequency band (maybe the same as in irregular case)
            -selected_columns: list of strings like ['S1', 'S2', 'S3']

        """

        NbProbe = len(selected_columns)
        if NbProbe > len(self.ProbeSpacing):  #nbr de colonnes selectionnes par l'utilisateur doit pas depasser le nbr de positions probeSpacing
            raise ValueError("Too many columns selected for the number of probe positions available.")

        def Calcul_Zelt(fourrierAmpli, phase, k, NbProbe, probePosition):
            """
             This function is based on the Zelt et al. method
             it returns the incident and reflected amplitudes;

             INPUT:
            - fourrierAmpli :
            - NbProbe : number of probe;
            - probePosition : to get spacing between 4 probes

            OUTPUT:
            - Ai: incident wave amplitude;
            - Ar: reflected wave amplitude .
            """
            P =NbProbe
            x = probePosition
            A = fourrierAmpli

            def W(j, p):
                W = 0
                for q in range(P):  # On regarde l'interaction avec TOUTES les sondes q ,P etant le nbr de sondes
                    W += np.sin(k[j] * (x[p] - x[q])) ** 2 / (1 + (k[j] * (x[p] - x[q]) / np.pi) ** 2)
                return W

            def S(j):
                S = 0
                for p in range(P):
                    S += W(j, p)
                return S

            def D(j):
                D = 0
                for p in range(P):
                    for q in range(p):
                        D += W(j, p) * W(j, q) * np.sin(k[j] * (x[p] - x[q])) ** 2
                return 4 * D

            A_i = np.zeros((len(A[0])), dtype=complex)
            A_r = np.zeros((len(A[0])), dtype=complex)

            for j in range(int(len(A[0]) / 2)):
                sum1, sum2, sum3, sum4 = 0, 0, 0, 0
                for p in range(P):
                    sum1 += W(j, p) * A[p][j] * np.exp(1j * phase[p][j]) * np.exp(-1j * k[j] * (x[p] - x[0]))
                    sum2 += W(j, p) * A[p][j] * np.exp(1j * phase[p][j]) * np.exp(1j * k[j] * (x[p] - x[0]))
                    sum3 += W(j, p) * np.exp(2 * 1j * k[j] * (x[p] - x[0]))
                    sum4 += W(j, p) * np.exp(-2 * 1j * k[j] * (x[p] - x[0]))

                A_r[j] = (S(j) * sum1 - sum2 * sum4) / D(j)
                A_i[j] = (S(j) * sum2 - sum1 * sum3) / D(j)

            return A_i, A_r

        startCutIndex = 10  # delete the first index dsp data to the calculation

        t  = self.data.iloc[:, 0].values
        NombreDonnee = len(t)
        S = self.data[selected_columns].values.T #S doit être transposé pour que S[i] accède à la sonde i entière
        timeStep = t[1] - t[0]

        #plt.figure()
        #plt.plot(t,S[0])
        #plt.plot(t,S[1])
        #plt.plot(t,S[2])
        #plt.plot(t,S[3])
        #plt.show()

        tf = scipy.fft.fft(S)
        phase = np.angle(tf)
        dsp = (tf * tf.conjugate()) / NombreDonnee ** 2
        f = (1 / timeStep) / 2 * np.linspace(0, 1, int(NombreDonnee / 2))

        #plt.figure()
        #plt.plot(f,dsp[0][:len(f)])
        #plt.plot(f,dsp[1][:len(f)])
        #plt.plot(f,dsp[2][:len(f)])
        #plt.plot(f,dsp[3][:len(f)])
        #plt.show()

        k = []
        for i in range(startCutIndex, len(f)):
            k.append(self.RelationDisp( 2 * np.pi * f[i], 10 ** (-6)))

        ampli_sonde = []
        ampli_spectre = []
        phase_spectre = []
        fmaxIndex = []
        f0 = []
        k0 = []
        phasePic = []
        for i in range(NbProbe):
            ampli_spectre.append(2 * np.sqrt(dsp[i][startCutIndex:int(NombreDonnee / 2)]))
            phase_spectre.append(phase[i][startCutIndex:int(NombreDonnee / 2)])
            fmaxIndex.append(int(np.argmax(np.abs(dsp[i][startCutIndex:int(NombreDonnee / 2)])) + startCutIndex)) #modifie recuperer le max par
            f0.append(f[fmaxIndex[i]])
            k0.append(k[fmaxIndex[i]-startCutIndex]) #############corrige de calcul############## k0 commence a startCutIndex non ?

            ampli_sonde.append(2 * np.sqrt(np.sum(dsp[i][startCutIndex:int(NombreDonnee / 2)])))
            phasePic.append(phase[i][fmaxIndex[i]])

        Ai_zelt, Ar_zelt = Calcul_Zelt(np.abs(np.array(ampli_spectre)), phase_spectre, k,NbProbe, self.ProbeSpacing)

       # plt.figure()
       #plt.plot(f[10:], np.abs(Ai_zelt), label='Ai')
       # plt.plot(f[10:], np.abs(Ar_zelt), label='Ar')
       # plt.legend()
       # plt.show()

        if self.Irreg == False:
            # ICI on intégre que sur le fondamentale sur la plage de -10% à +10 % de la fréquence fondamentale
            Ai = np.sqrt(np.sum(np.array(Ai_zelt[int(fmaxIndex[0] * 0.9):int(fmaxIndex[0] * 1.1)]) * np.array(
                Ai_zelt[int(fmaxIndex[0] * 0.9):int(fmaxIndex[0] * 1.1)].conjugate())))
            Ar = np.sqrt(np.sum(np.array(Ar_zelt[int(fmaxIndex[0] * 0.9):int(fmaxIndex[0] * 1.1)]) * np.array(
                Ar_zelt[int(fmaxIndex[0] * 0.9):int(fmaxIndex[0] * 1.1)].conjugate())))
        else:
            Ai = np.sqrt(2 * np.sum(np.array(Ai_zelt[int(fmaxIndex[0] / 2):int(fmaxIndex[0] * 4.5)]) * np.array(
                Ai_zelt[int(fmaxIndex[0] / 2):int(fmaxIndex[0] * 4.5)].conjugate())))
            Ar = np.sqrt(2 * np.sum(np.array(Ar_zelt[int(fmaxIndex[0] / 2):int(fmaxIndex[0] * 4.5)]) * np.array(
                Ar_zelt[int(fmaxIndex[0] / 2):int(fmaxIndex[0] * 4.5)].conjugate())))

        return Ai, Ar
