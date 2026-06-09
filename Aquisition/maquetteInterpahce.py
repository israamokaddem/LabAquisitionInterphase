import requests
import time
import os


def lancer_acquisition(self, dictionnaire_voies, callback_maj=None, verifier_arret=None):
    # 🎯 À REMPLACER PAR LES URL QUE TU AS TROUVÉES (F12 ou ton script)
    url_start = f"http://169.254.119.150/api/daq/start"
    url_stop = f"http://169.254.119.150/api/daq/stop"
    url_status = f"http://169.254.119.150/api/daq/download/4615f0d4-65ff-4f24-a963-68593c1985ed"  # Pour récupérer l'UUID

    # On réutilise les headers que tu avais capturés
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Connection": "keep-alive",
        "PHPSESSID" : "2d319374cda45a05dae5294763c5a534"
    }

    try:
        # 1. DÉMARRAGE
        print("🚀 Envoi de la commande START...")
        requests.post(url_start, headers=headers)

        # 2. CHRONOMÈTRE (Python attend pendant la durée définie dans l'UI)
        duree = self.parametres["duree"]
        temps_debut = time.time()
        while time.time() - temps_debut < duree:
            if verifier_arret and verifier_arret():
                break
            time.sleep(0.5)

        # 3. ARRÊT
        print("⏹️ Envoi de la commande STOP...")
        requests.post(url_stop, headers=headers)

        # 4. RÉCUPÉRATION DE L'UUID (Le nom du fichier)
        print("🔍 Recherche du fichier généré...")
        reponse_status = requests.get(url_status, headers=headers)
        donnees_json = reponse_status.json()

        # ⚠️ Le chemin exact dépendra de ce que renvoie le JSON
        uuid_fichier = donnees_json['last_acquisition']['id']

        # 5. TÉLÉCHARGEMENT
        url_download = f"http://{self.ip}/api/daq/download/{uuid_fichier}?filename=donnees.csv"
        print(f"📥 Téléchargement depuis {url_download}...")

        reponse_fichier = requests.get(url_download, headers=headers)
        chemin_complet = os.path.join(self.parametres["dossier_sortie"], self.parametres["nom_fichier"])

        with open(chemin_complet, "wb") as f:
            f.write(reponse_fichier.content)

        print("✅ Acquisition terminée et fichier sauvegardé !")
        return True

    except Exception as e:
        print(f"❌ Erreur API : {e}")
        return False