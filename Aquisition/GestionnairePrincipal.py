import threading
import pandas as pd
import os
from GestionnaireNI import GestionnaireNI
from GestionnaireKistler import GestionnaireKistler
from GestionnaireMCC import GestionnaireMCC

class GestionnairePrincipal:
    def __init__(self):
        self.ni = GestionnaireNI()
        self.kistler = GestionnaireKistler()
        self.mcc = GestionnaireMCC()

        self.parametres = {"duree": 10, "frequence": 1000, "nom_fichier": "donnees_fusionnees.csv",
                           "dossier_sortie": "."}
        self.boitiers_detectes = []

    def definir_parametres(self, duree, frequence):
        self.parametres["duree"] = duree
        self.parametres["frequence"] = frequence
        # On dit à chaque équipement de créer son propre fichier temporaire
        self.ni.definir_parametres(duree, frequence, nom_fichier="temp_ni.csv", dossier=".")
        self.kistler.definir_parametres(duree, frequence, nom_fichier="temp_kistler.csv", dossier=".")
        self.mcc.definir_parametres(duree, frequence, nom_fichier="temp_mcc.csv", dossier=".")

    def initialiser_systeme(self, scan_ni=True, scan_kistler=False,
                            scan_mcc=False, mode_simulation_mcc=False,
                            ips_manuelles=None):
        self.boitiers_detectes = []

        if scan_ni:
            if self.ni.initialiser_systeme():
                for b in self.ni.boitiers_detectes:
                    b['backend'] = 'NI'
                    self.boitiers_detectes.append(b)

        if scan_kistler:
            try:
                succes_kistler = self.kistler.initialiser_systeme_manuel(
                    ips_manuelles) if ips_manuelles else self.kistler.initialiser_systeme()
                if succes_kistler:
                    for b in self.kistler.boitiers_detectes:
                        b['backend'] = 'Kistler'
                        self.boitiers_detectes.append(b)
            except Exception as e:
                print(f"[Kistler] Erreur scan : {e}")
                self._erreur_kistler = str(e)

        if scan_mcc:
            if mode_simulation_mcc != self.mcc.mode_simulation:
                self.mcc = GestionnaireMCC(mode_simulation=mode_simulation_mcc)
            if self.mcc.initialiser_systeme():
                for b in self.mcc.boitiers_detectes:
                    b['backend'] = 'MCC'
                    self.boitiers_detectes.append(b)

        return len(self.boitiers_detectes) > 0

    def lancer_acquisition(self, dictionnaire_voies, callback_maj=None, verifier_arret=None):
        voies_ni = {}
        voies_kistler = {}
        indices_ni = []
        indices_kistler = []
        voies_mcc={}
        indices_mcc=[]


        # 1. On sépare le travail (Qui fait quoi ?)
        index_global = 0
        for boitier, voies in dictionnaire_voies.items():
            backend = self._trouver_backend(boitier)
            if backend == 'NI':
                voies_ni[boitier] = voies
                indices_ni.extend(range(index_global, index_global + len(voies)))
            elif backend == 'MCC':
                voies_mcc[boitier] = voies
                indices_mcc.extend(range(index_global, index_global + len(voies)))
            else:
                voies_kistler[boitier] = voies
                indices_kistler.extend(range(index_global, index_global + len(voies)))

            index_global += len(voies)

        threads_actifs = []

        # 2. Les sous-tâches pour lancer les matériels en parallèle
        def wrap_ni():
            if voies_ni:
                cb = lambda t, d: callback_maj(t, d, indices_ni) if callback_maj else None
                self.ni.lancer_acquisition(voies_ni, callback_maj=cb, verifier_arret=verifier_arret)

        def wrap_kistler():
            if voies_kistler:
                cb = lambda t, d: callback_maj(t, d, indices_kistler) if callback_maj else None
                self.kistler.lancer_acquisition(voies_kistler, callback_maj=cb, verifier_arret=verifier_arret)

        # Ajouter la fonction wrap et le démarrage du thread, après wrap_kistler :
        def wrap_mcc():
            if voies_mcc:
                cb = lambda t, d: callback_maj(t, d, indices_mcc) if callback_maj else None
                self.mcc.lancer_acquisition(voies_mcc, callback_maj=cb, verifier_arret=verifier_arret)



        # 3. Démarrage simultané
        if voies_ni:
            t1 = threading.Thread(target=wrap_ni)
            threads_actifs.append(t1)
            t1.start()

        if voies_kistler:
            t2 = threading.Thread(target=wrap_kistler)
            threads_actifs.append(t2)
            t2.start()

        if voies_mcc:
            t3 = threading.Thread(target=wrap_mcc)
            threads_actifs.append(t3)
            t3.start()


        # 4. On attend que tout le monde ait fini de mesurer
        for t in threads_actifs:
            t.join()

        # 5. FUSION MAGIQUE DES FICHIERS
        self.fusionner_fichiers()
        return True

    def _trouver_backend(self, nom_boitier):
        """Retrouve si un boîtier appartient à NI ou Kistler"""
        for b in self.boitiers_detectes:
            if b['nom'] == nom_boitier:
                return b.get('backend', 'NI')
        return 'NI'

    def fusionner_fichiers(self):
        """Aligne les temps de NI et Kistler et crée un seul fichier propre"""
        dfs = []

        if os.path.exists("temp_ni.csv"):
            df_ni = pd.read_csv("temp_ni.csv")
            if not df_ni.empty:
                df_ni.set_index("temps(s)", inplace=True)
                dfs.append(df_ni)

        if os.path.exists("temp_kistler.csv"):
            df_k = pd.read_csv("temp_kistler.csv")
            if not df_k.empty:
                df_k.set_index("temps(s)", inplace=True)
                dfs.append(df_k)

        if os.path.exists("temp_mcc.csv"):
            try:
                df_mcc = pd.read_csv("temp_mcc.csv")
                if not df_mcc.empty:
                    df_mcc.set_index("temps(s)", inplace=True)
                    dfs.append(df_mcc)
            except Exception as e:
                print(f"[Fusion] Lecture temp_mcc.csv impossible : {e}")
        try:
            if os.path.exists("temp_mcc.csv"): os.remove("temp_mcc.csv")
        except PermissionError:
            print("[Fusion] temp_mcc.csv encore ouvert — sera supprimé au prochain lancement.")

        if len(dfs) == 0:
            return
        elif len(dfs) == 1:
            df_final = dfs[0]
        else:
            # Interpolation temporelle (Fusion)
            df_final = pd.concat(dfs, axis=1).sort_index()
            df_final = df_final.interpolate(method='index').bfill().ffill()

        chemin_final = os.path.join(self.parametres["dossier_sortie"], self.parametres["nom_fichier"])
        df_final.to_csv(chemin_final)

        # Nettoyage des fichiers temporaires
        if os.path.exists("temp_ni.csv"): os.remove("temp_ni.csv")
        if os.path.exists("temp_kistler.csv"): os.remove("temp_kistler.csv")
        if os.path.exists("temp_mcc.csv"): os.remove("temp_mcc.csv")

    def tester_connexions(self, dictionnaire_voies):
        voies_en_echec = []
        voies_ni = {}
        voies_kistler = {}
        voies_mcc = {}


        # 1. On sépare les boîtiers
        for boitier, voies in dictionnaire_voies.items():
            if self._trouver_backend(boitier) == 'NI':
                voies_ni[boitier] = voies
            else:
                voies_kistler[boitier] = voies

        # 2. Test NI
        if voies_ni:
            if hasattr(self.ni, 'tester_connexions'):
                voies_en_echec.extend(self.ni.tester_connexions(voies_ni))
            else:
                print("⚠️ ERREUR : La méthode 'tester_connexions' manque dans GestionnaireNI !")

        # 3. Test Kistler (Sécurisé)
        if voies_kistler:
            if hasattr(self.kistler, 'tester_connexions'):
                try:
                    voies_en_echec.extend(self.kistler.tester_connexions(voies_kistler))
                except Exception as e:
                    print(f"⚠️ ERREUR RESEAU KISTLER : {e}")
                    for b, v_list in voies_kistler.items():
                        for v in v_list: voies_en_echec.append((b, v))
            if voies_mcc:
                if hasattr(self.mcc, 'tester_connexions'):
                    voies_en_echec.extend(self.mcc.tester_connexions(voies_mcc))


            else:
                print("⚠️ ERREUR : La méthode 'tester_connexions' manque dans GestionnaireKistler !")
                # Si la méthode manque, on met les voies en échec par sécurité pour forcer la popup
                for b, v_list in voies_kistler.items():
                    for v in v_list: voies_en_echec.append((b, v))

        return voies_en_echec