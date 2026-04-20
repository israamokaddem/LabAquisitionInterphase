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


import scipy.fft
from scipy.optimize import newton
import pandas as pd
import numpy as np



class Decomposition:
    def __init__(self, data, ProbeSpacing=None, depth: int|float=0.2, g=9.81, Irreg=False):
        """
        Constructeur de la classe de traitement.

        :param : data Le DataFrame Pandas contenant les données chargées.
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
        self.ProbeSpacing = np.array(ProbeSpacing) # 2. On s'assure que spacing est un array NumPy (plus rapide pour les calculs)
        self.Irreg= Irreg
        self.variables = ["ProbeSpacing", "Depth", "Gain"] # titre des colonnes selectionnes

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
            if f(a) * f(m) <= 0:
                b = m
            else:
                a = m
        return a

    def findMaxFrequency(self) -> list:
        # 1. Récupération des données
        t = self.data.iloc[:, 0].values
        S = self.data.iloc[:, 1:].values
        NombreDonnee = len(t)
        timeStep = t[1] - t[0]

        # 2. CALCUL CORRECT DU VECTEUR F
        f = (1 / timeStep) / 2 * np.linspace(0, 1, int(NombreDonnee / 2))
        f0 = []
        for i in range(S.shape[1]):  # On boucle sur le nombre de colonnes
            # Calcul de la FFT
            tf = scipy.fft.fft(S[:, i])
            dsp = (tf * tf.conjugate()) / NombreDonnee ** 2
            fmaxIndex = int(np.argmax(np.abs(dsp[10:NombreDonnee // 2])) + 10)
            f0.append(f[fmaxIndex])
        return f0

    def WaveProbeDecomposition(self,selected_columns,sci):
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

        t = self.data.iloc[:, 0].values
        NombreDonnee = len(t)
        S = self.data[selected_columns].values.T  # Transposition pour avoir S[Sonde][Temps]
        timeStep = t[1] - t[0]
        NbProbe = len(selected_columns)
        tf = scipy.fft.fft(S)
        phase = np.angle(tf)
        dsp = (tf * tf.conjugate()) / NombreDonnee ** 2
        f = (1 / timeStep) / 2 * np.linspace(0, 1, int(NombreDonnee / 2))

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
            - Ar: reflected wave amplitude .S
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

        startCutIndex=sci # delete the first index dsp data to the calculation
        if startCutIndex >= NombreDonnee//2: # verifier que le cut index entre par le chercheur est bien <nbdonness/2
            raise ValueError(
                f"Le StartCutIndex ({startCutIndex}) est trop élevé pour la taille des données.\n"
                f"Il doit être inférieur à {NombreDonnee//2} (Nombre de lignes / 2)."
            )

        #plt.figure()
        #plt.plot(t,S[0])
        #plt.plot(t,S[1])
        #plt.plot(t,S[2])
        #plt.plot(t,S[3])
        #plt.show()


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
            # 1. On isole le segment de recherche pour la sonde i
            segment_dsp = np.abs(dsp[i][startCutIndex:int(NombreDonnee / 2)])

            # 2. On vérifie si le segment n'est pas vide avant le argmax
            if segment_dsp.size > 0:
                fmaxIndex.append(int(np.argmax(segment_dsp) + startCutIndex))
            else:
                # Sécurité : si le fichier est trop court, on évite le crash
                fmaxIndex.append(startCutIndex)

            f0.append(f[fmaxIndex[i]])
            k0.append(k[fmaxIndex[i] - startCutIndex])  #############corrige de calcul############## k0 commence a startCutIndex non ?

            ampli_spectre.append(2 * np.sqrt(dsp[i][startCutIndex:int(NombreDonnee / 2)]))
            phase_spectre.append(phase[i][startCutIndex:int(NombreDonnee / 2)])
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

    def Decomposition_LiuHuang(self,selected_columns,omega, order=2):
        '''

         This function is based on the Liu et Huang method (2004)
         it returns the incident and reflected amplitudes with the consideration of free and bound waves;
         Used in non linear case and regular waves

         INPUT:
        - data[:,0] : time serie
        - data[:,j>0] : free surface for each probes
        - omega : wave fundamental frequency
        - depth : water depth
        - order : Order to free and bound waves (by default it's the second order)
        - probePosition : to get spacing between 4 probes

        OUTPUT:
        - Ai: incident wave amplitude;
        - Ar: reflected wave amplitude .
        '''

        def Eta_FT(order, eta_temporal, timeSeries):
            Eta_xm = 1 / timeSeries[-1] * np.sum(
                eta_temporal * np.exp(-1j * order * omega * timeSeries) * (timeSeries[1] - timeSeries[0]))
            return Eta_xm

        time = self.data.iloc[:, 0].values
        matrix_s= self.data[selected_columns].values.T
        S = [matrix_s[i] for i in range(len(selected_columns))] #array transformation

        # plt.figure()
        # plt.plot(time,S[0])
        # plt.plot(time,S[1])
        # plt.plot(time,S[2])
        # plt.plot(time,S[3])
        # plt.show()

        n = order
        # print(n)
        k = self.RelationDisp(omega, 10 ** (-6))
        k_n = self.RelationDisp_freewave(omega, 10 ** (-6), n)

        CI_1, CR_1, CIB_n, CIF_n, CRB_n, CRF_n = [], [], [], [], [], []

        print('lambda :', (2 * np.pi / k), ' , lambda nf : ', (2 * np.pi / k_n), ' , lambda nb : ',
              (2 * np.pi / (k * n)))
        for m in range(len(self.ProbeSpacing)):
            CI_1.append(np.exp(-1j * k * self.ProbeSpacing[m]) / 2)
            CR_1.append(np.exp(1j * k * self.ProbeSpacing[m]) / 2)
            CIB_n.append(np.exp(-1j * k * n * self.ProbeSpacing[m]) / 2)
            CIF_n.append(np.exp(-1j * k_n * self.ProbeSpacing[m]) / 2)
            CRB_n.append(np.exp(1j * k * n * self.ProbeSpacing[m]) / 2)
            CRF_n.append(np.exp(1j * k_n * self.ProbeSpacing[m]) / 2)

        # 1er ordre

        A11, A12, A21, A22, B1, B2 = 0, 0, 0, 0, 0, 0
        for m in range(len(self.ProbeSpacing)):
            A11 += CI_1[m] ** 2
            A12 += CI_1[m] * CR_1[m]
            A22 += CR_1[m] ** 2
            B1 += Eta_FT(1, S[m], time) * CI_1[m]
            B2 += Eta_FT(1, S[m], time) * CR_1[m]
        A21 = A12

        A = np.array([[A11, A12], [A21, A22]])
        B = np.array([B1, B2])

        XI_1, XR_1 = np.linalg.solve(A, B)
        Ai_1 = abs(XI_1)
        Ar_1 = abs(XR_1)

        # 2eme ordre

        A11, A12, A13, A14, A21, A22, A23, A24, A31, A32, A33, A34, A41, A42, A43, A44, B1, B2, B3, B4 = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        for m in range(len(self.ProbeSpacing)):
            A11 += CIB_n[m] ** 2
            A12 += CRB_n[m] * CIB_n[m]
            A13 += CIF_n[m] * CIB_n[m]
            A14 += CRF_n[m] * CIB_n[m]
            A22 += CRB_n[m] ** 2
            A23 += CIF_n[m] * CRB_n[m]
            A24 += CRF_n[m] * CRB_n[m]
            A33 += CIF_n[m] ** 2
            A34 += CRF_n[m] * CIF_n[m]
            A44 += CRF_n[m] ** 2
            B1 += Eta_FT(n, S[m], time) * CIB_n[m]
            B2 += Eta_FT(n, S[m], time) * CRB_n[m]
            B3 += Eta_FT(n, S[m], time) * CIF_n[m]
            B4 += Eta_FT(n, S[m], time) * CRF_n[m]
        A21 = A12
        A31 = A13
        A41 = A14
        A32 = A23
        A42 = A24
        A43 = A34

        A = np.array([[A11, A12, A13, A14], [A21, A22, A23, A24], [A31, A32, A33, A34], [A41, A42, A43, A44]])
        B = np.array([B1, B2, B3, B4])

        XIB_n, XRB_n, XIF_n, XRF_n = np.linalg.solve(A, B)
        AiB_n = abs(XIB_n)
        ArB_n = abs(XRB_n)
        AiF_n = abs(XIF_n)
        ArF_n = abs(XRF_n)

        return Ai_1, Ar_1, AiB_n, ArB_n, AiF_n, ArF_n


    def Decomposition_EldrupAnderson(self,selected_columns,omega,order=2):
        '''
         This function is based on the Lykke Andersen, Eldrup and Frigaard method (2016 - 2017)
         Is derivated of Liu and Huang method but a correction is applied for the case where bound and free harmonic are similar celerity
         Consider a wave number different for incident et reflected waves.

         Used in non linear case and regular waves for very shallow water depth

         INPUT:
        - data[0] : time serie
        - data[1:] : free surface for each probes
        - omega : wave fundamental frequency
        - depth : water depth
        - order : Order to free and bound waves (by default it's the second order)
        - probePosition : to get spacing between 4 probes

        OUTPUT:
        - Ai: incident wave amplitude;
        - Ar: reflected wave amplitude .
        '''

        def Eta_FT(order, eta_temporal, timeSeries):
            Eta_xm = 1 / timeSeries[-1] * np.sum(
                eta_temporal * np.exp(-1j * order * omega * timeSeries) * (timeSeries[1] - timeSeries[0]))
            return Eta_xm

        time = self.data.iloc[:, 0].values
        matrix_s = self.data[selected_columns].values.T
        S = [matrix_s[i] for i in range(len(selected_columns))] # array transformation

        n = order

        # STEP 1 : Initialisation de k_i et k_r

        k = self.RelationDisp(omega, 10 ** (-6))
        k_i, k_r = k, k
        k_n = self.RelationDisp_freewave(omega, 10 ** (-6), order)
        # STEP 2.1 : Intial value calculation

        CI_1, CR_1, CIB_n, CIF_n, CRB_n, CRF_n = [], [], [], [], [], []
        for m in range(len(self.ProbeSpacing)):
            CI_1.append(np.exp(-1j * k_i * self.ProbeSpacing[m]) / 2)
            CR_1.append(np.exp(1j * k_r * self.ProbeSpacing[m]) / 2)
            CIB_n.append(np.exp(-1j * k_i * n * self.ProbeSpacing[m]) / 2)
            CIF_n.append(np.exp(-1j * k_n * self.ProbeSpacing[m]) / 2)
            CRB_n.append(np.exp(1j * k_r * n * self.ProbeSpacing[m]) / 2)
            CRF_n.append(np.exp(1j * k_n * self.ProbeSpacing[m]) / 2)

        # 1er ordre
        A11, A12, A21, A22, B1, B2 = 0, 0, 0, 0, 0, 0
        for m in range(len(self.ProbeSpacing)):
            A11 += CI_1[m] ** 2
            A12 += CI_1[m] * CR_1[m]
            A22 += CR_1[m] ** 2
            B1 += Eta_FT(1, S[m], time) * CI_1[m]
            B2 += Eta_FT(1, S[m], time) * CR_1[m]
        A21 = A12

        A = np.array([[A11, A12], [A21, A22]])
        B = np.array([B1, B2])

        XI_1, XR_1 = np.linalg.solve(A, B)
        Ai_1 = abs(XI_1)
        Ar_1 = abs(XR_1)

        # 2eme ordre

        A11, A12, A13, A14, A21, A22, A23, A24, A31, A32, A33, A34, A41, A42, A43, A44, B1, B2, B3, B4 = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        for m in range(len(self.ProbeSpacing)):
            A11 += CIB_n[m] ** 2
            A12 += CRB_n[m] * CIB_n[m]
            A13 += CIF_n[m] * CIB_n[m]
            A14 += CRF_n[m] * CIB_n[m]
            A22 += CRB_n[m] ** 2
            A23 += CIF_n[m] * CRB_n[m]
            A24 += CRF_n[m] * CRB_n[m]
            A33 += CIF_n[m] ** 2
            A34 += CRF_n[m] * CIF_n[m]
            A44 += CRF_n[m] ** 2
            B1 += Eta_FT(n, S[m], time) * CIB_n[m]
            B2 += Eta_FT(n, S[m], time) * CRB_n[m]
            B3 += Eta_FT(n, S[m], time) * CIF_n[m]
            B4 += Eta_FT(n, S[m], time) * CRF_n[m]
        A21 = A12
        A31 = A13
        A41 = A14
        A32 = A23
        A42 = A24
        A43 = A34

        A = np.array([[A11, A12, A13, A14], [A21, A22, A23, A24], [A31, A32, A33, A34], [A41, A42, A43, A44]])
        B = np.array([B1, B2, B3, B4])

        XIB_n, XRB_n, XIF_n, XRF_n = np.linalg.solve(A, B)
        AiB_n = abs(XIB_n)
        ArB_n = abs(XRB_n)
        AiF_n = abs(XIF_n)
        ArF_n = abs(XRF_n)

        # STEP 3 : Wave height incident and reflected calculation

        k_i = self.RelationDisp_fifthOrder(omega, 2 * (Ai_1 + AiB_n), 0.0001)
        k_r = self.RelationDisp_fifthOrder(omega, 2 * (Ar_1 + ArB_n), 0.0001)
        # print(k_n,k_i,k_r)
        eps = 1
        while eps >= 0.00001:  # for j in range(3):
            Ai_init = (Ai_1 + AiB_n)  # parametre de reference pour la tolerance
            CI_1, CR_1, CIB_n, CIF_n, CRB_n, CRF_n = [], [], [], [], [], []
            for m in range(len(self.ProbeSpacing)):
                CI_1.append(np.exp(-1j * k_i * self.ProbeSpacing[m]) / 2)
                CR_1.append(np.exp(1j * k_r * self.ProbeSpacing[m]) / 2)
                CIB_n.append(np.exp(-1j * k_i * n * self.ProbeSpacing[m]) / 2)
                CIF_n.append(np.exp(-1j * k_n * self.ProbeSpacing[m]) / 2)
                CRB_n.append(np.exp(1j * k_r * n * self.ProbeSpacing[m]) / 2)
                CRF_n.append(np.exp(1j * k_n * self.ProbeSpacing[m]) / 2)

            # 1er ordre
            A11, A12, A21, A22, B1, B2 = 0, 0, 0, 0, 0, 0
            for m in range(len(self.ProbeSpacing)):
                A11 += CI_1[m] ** 2
                A12 += CI_1[m] * CR_1[m]
                A22 += CR_1[m] ** 2
                B1 += Eta_FT(1, S[m], time) * CI_1[m]
                B2 += Eta_FT(1, S[m], time) * CR_1[m]
            A21 = A12

            A = np.array([[A11, A12], [A21, A22]])
            B = np.array([B1, B2])

            XI_1, XR_1 = np.linalg.solve(A, B)
            Ai_1 = abs(XI_1)
            Ar_1 = abs(XR_1)

            # 2eme ordre

            A11, A12, A13, A14, A21, A22, A23, A24, A31, A32, A33, A34, A41, A42, A43, A44, B1, B2, B3, B4 = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0

            for m in range(len(self.ProbeSpacing)):
                A11 += CIB_n[m] ** 2
                A12 += CRB_n[m] * CIB_n[m]
                A13 += CIF_n[m] * CIB_n[m]
                A14 += CRF_n[m] * CIB_n[m]
                A22 += CRB_n[m] ** 2
                A23 += CIF_n[m] * CRB_n[m]
                A24 += CRF_n[m] * CRB_n[m]
                A33 += CIF_n[m] ** 2
                A34 += CRF_n[m] * CIF_n[m]
                A44 += CRF_n[m] ** 2
                B1 += Eta_FT(n, S[m], time) * CIB_n[m]
                B2 += Eta_FT(n, S[m], time) * CRB_n[m]
                B3 += Eta_FT(n, S[m], time) * CIF_n[m]
                B4 += Eta_FT(n, S[m], time) * CRF_n[m]
            A21 = A12
            A31 = A13
            A41 = A14
            A32 = A23
            A42 = A24
            A43 = A34

            A = np.array([[A11, A12, A13, A14], [A21, A22, A23, A24], [A31, A32, A33, A34], [A41, A42, A43, A44]])
            B = np.array([B1, B2, B3, B4])

            XIB_n, XRB_n, XIF_n, XRF_n = np.linalg.solve(A, B)
            AiB_n = abs(XIB_n)
            ArB_n = abs(XRB_n)
            # AiF_n = abs(XIF_n)
            # ArF_n = abs(XRF_n)

            k_i = self.RelationDisp_fifthOrder(omega, 2 * (Ai_1 + AiB_n), 0.0001)
            k_r = self.RelationDisp_fifthOrder(omega, 2 * (Ar_1 + ArB_n), 0.0001)

            eps = abs(Ai_init - (Ai_1 + AiB_n))
            # print(k_i,eps)

        return Ai_1, Ar_1, AiB_n, ArB_n, AiF_n, ArF_n


if __name__ == "__main__":
    import pandas as pd
    import numpy as np

    # 1. PARAMÈTRES PHYSIQUES (Identiques au script de Paul)
    h = 0.6
    f_test = 0.5
    positions = [0.0, 0.45, 1.25, 2.30]  # Positions x des 4 sondes
    omega = 2 * np.pi * 0.5

    # Temps : de 0 à 100s avec 10 000 points
    t = np.linspace(0, 100, 10000)
    dt = t[1] - t[0]

    # 2. GÉNÉRATION DU SIGNAL DE TEST (Simulant une houle non-linéaire)
    # On utilise la dispersion linéaire pour générer k
    # (Note: moteur temporaire juste pour calculer k)
    temp_moteur = Decomposition(data=None, depth=h, ProbeSpacing=positions)
    k_theo = temp_moteur.RelationDisp(omega, 1e-6)

    amp_inc = 1.0  # Amplitude cible incidente
    amp_ref = 0.2  # Amplitude cible réfléchie (20% de réflexion)

    data_dict = {'Time': t}
    for i, x in enumerate(positions):
        # Onde incidente + Onde réfléchie (1er ordre)
        eta_i = amp_inc * np.cos(omega * t - k_theo * x)
        eta_r = amp_ref * np.cos(omega * t + k_theo * x)
        # Ajout d'un petit second ordre lié pour tester Liu & Huang
        eta_2 = 0.1 * np.cos(2 * omega * t - 2 * k_theo * x)

        data_dict[f'S{i + 1}'] = eta_i + eta_r + eta_2

    # Création du DataFrame Pandas (le format que ta classe attend)
    df_test = pd.DataFrame(data_dict)

    # 3. INITIALISATION DU MOTEUR
    moteur = Decomposition(
        data=df_test,
        depth=h,
        ProbeSpacing=positions,
        Irreg=False
    )

    # 4. EXÉCUTION DE LA MÉTHODE LIU & HUANG
    print("--- COMPARAISON DES RÉSULTATS (Cible: Ai=1.0, Ar=0.2) ---")
    try:
        # Sélection des colonnes générées
        colonnes = ['S1', 'S2', 'S3', 'S4']

        Ai1, Ar1, AiB, ArB, AiF, ArF = moteur.Decomposition_LiuHuang(
            selected_columns=colonnes,
            omega=omega,
            order=2
        )
        Ai12, Ar12, AiB2, ArB2, AiF2, ArF2 = moteur.Decomposition_EldrupAnderson(
            selected_columns=colonnes,
            omega=omega,
            order=2
        )

        print(f"\n[CLASSE DECOMPOSITION]")
        print(f"Amplitude Incidente (1er ordre) : {Ai12:.4f} m")
        print(f"Amplitude Réfléchie (1er ordre) : {Ar12:.4f} m")
        print(f"Amplitude Liée (Bound Ai)       : {AiB2:.4f} m")
        print(f"Coefficient de Réflexion (R)    : {(Ar1 / Ai1) * 100:.2f} %")

    except Exception as e:
        print(f"Erreur lors du calcul : {e}")
