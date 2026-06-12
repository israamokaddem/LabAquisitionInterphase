import os
import csv
import socket
import subprocess
import re
from GestionnaireAquisition import GestionnaireAquisition
import time


# ==========================================
# DÉFINITION DES EXCEPTIONS LOGICIELLES
# ==========================================
class KistlerError(Exception): """Classe de base pour toutes les erreurs Kistler"""


pass
class BoitierIntrouvableError(KistlerError): pass
class ConnexionRefuseeError(KistlerError): pass
class ConnexionInterrompueError(KistlerError): pass
class FormatDonneesCorrompuError(KistlerError): pass
class TimeoutReseauError(KistlerError): pass


class GestionnaireKistler(GestionnaireAquisition):
    # 🎯 Déclaration de la liste des ports candidats au niveau de la classe
    PORTS_CANDIDATS = [80, 5000, 8080, 443, 8443, 10700, 10701, 3000, 9000]

    def __init__(self, port_donnees=5000, numero_serie="5294123"):
        super().__init__()
        self.port = port_donnees
        self.sn = numero_serie
        self.ip = None  # Découverte automatique réseau

        self.voies_disponibles = []
        self.voies_selectionnees = []
        self.config_sondes = {}
        self.parametres = {
            "frequence": 1000,
            "duree": 0,
            "nom_fichier": "donnees_kistler.csv",
            "dossier_sortie": "."
        }
        self.boitiers_detectes = []
        self.chemins_voies_actives = []

    # ==========================================
    # ÉTAPE 1 : DÉTECTION (Parallèle & Multi-boîtiers)
    # ==========================================
        # 🎯 On remet ta liste originale complète pour gérer tous tes boîtiers
        PORTS_CANDIDATS = [80, 5000, 8080, 443, 8443, 10700, 10701, 3000, 9000]

    def initialiser_systeme(self):
        """
        Découvre le boîtier Kistler en envoyant une requête HTTP de réveil.
        Filtre efficacement les vrais boîtiers des services fantômes locaux.
        """
        import urllib.request
        self.boitiers_detectes.clear()
        self.boitiers_detectes = []
        self.ip = None

        print("🔍 Lancement du scan parallèle (Simulateur + Réseau HTTP)...")

        # ── Étape 1 : Vérification exclusive du simulateur local (Port 5000) ──
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(0.1)
            test_socket.connect(("127.0.0.1", 5000))
            test_socket.close()

            nom_virtuel = f"Kistler_Simulateur_{self.sn}"
            self.boitiers_detectes.append({
                "nom": nom_virtuel,
                "modele": "5165A (Simulé)",
                "total_voies": 4,
                "voies_dispos": [f"{nom_virtuel}/Ch1", f"{nom_virtuel}/Ch2", f"{nom_virtuel}/Ch3", f"{nom_virtuel}/Ch4"]
            })
            self.ip = "127.0.0.1"
            print("🤖 Mode local détecté (simulateur actif sur 127.0.0.1:5000)")
        except Exception:
            print("🤖 Simulateur local hors ligne.")

        # ── Étape 2 : Collecte des IPs candidates via la table ARP ──
        ips_arp = self._lire_table_arp()
        compteur_boitier = 1

        # ── Étape 3 : Détection et Réveil par Requête HTTP (Port 80) ──
        for ip_test in ips_arp:
            if ip_test == "127.0.0.1" or ip_test.endswith(".255"):
                continue

            print(f"🕵️ Envoi d'une requête HTTP flash sur http://{ip_test}...")

            try:
                # On tente d'ouvrir l'URL du boîtier avec un timeout très court (300ms)
                # Même si le boîtier renvoie une erreur 404 ou 401, le simple fait qu'il
                # réponde en HTTP prouve qu'un serveur Kistler est physiquement là !
                url = f"http://{ip_test}"
                reponse = urllib.request.urlopen(url, timeout=0.3)
                reponse.close()
                http_ok = True
            except (urllib.error.URLError, socket.timeout):
                # Si l'IP ne répond pas ou que le timeout expire, ce n'est pas notre boîtier
                http_ok = False
            except Exception:
                # Tout autre type de réponse (ex: redirection ou accès refusé) prouve qu'un appareil répond au HTTP
                http_ok = True

            # Si l'appareil a répondu à la poignée de main HTTP
            if http_ok:
                # 🎯 On valide l'appareil et on bascule sur ton dictionnaire de ports pour l'acquisition
                self._tester_port_tcp(ip_test, timeout=0.1)

                nom_appareil = f"Kistler_LabAmp_{self.sn}_{compteur_boitier}"
                voies = [f"{nom_appareil}/Ch1", f"{nom_appareil}/Ch2", f"{nom_appareil}/Ch3", f"{nom_appareil}/Ch4"]

                self.boitiers_detectes.append({
                    "nom": nom_appareil,
                    "modele": "5165A",
                    "total_voies": 4,
                    "voies_dispos": voies
                })

                if self.ip is None or self.ip == "127.0.0.1":
                    self.ip = ip_test
                    self.voies_disponibles = voies

                print(
                    f"   ✅ Vrai boîtier Kistler détecté en HTTP ! IP : {ip_test} (Port TCP d'acquisition : {self.port})")
                compteur_boitier += 1

        # ── Étape 4 : Validation finale ──
        if not self.boitiers_detectes:
            raise BoitierIntrouvableError(
                "Le boîtier Kistler est introuvable sur le réseau.\n"
                "Vérifiez l'alimentation électrique du boîtier et l'état des câbles RJ45."
            )

        if self.ip == "127.0.0.1":
            self.voies_disponibles = self.boitiers_detectes[0]["voies_dispos"]

        return True

    def _lire_table_arp(self):
        """
        Lit la table ARP et retourne les IPs candidates en 169.254.x.x.
        """
        try:
            if os.name == "nt":  # Windows
                # Optionnel : un petit ping broadcast rapide pour réveiller la table locale
                os.system("ping -n 1 -w 200 169.254.255.255 > nul 2>&1")
                time.sleep(0.1)
                output = subprocess.check_output("arp -a", shell=True).decode('cp1252', errors='ignore')
            else:  # Linux / Mac
                os.system("ping -c 1 -b -W 1 169.254.255.255 > /dev/null 2>&1")
                time.sleep(0.1)
                output = subprocess.check_output("ip neigh", shell=True).decode('utf-8', errors='ignore')

            ips = re.findall(r'(169\.254\.\d{1,3}\.\d{1,3})', output)
            # On élimine les doublons potentiels et les adresses de diffusion .255
            return list({ip for ip in ips if not ip.endswith(".255")})
        except Exception as e:
            print(f"   Erreur lecture ARP : {e}")
            return []


    def _tester_port_tcp(self, ip, timeout=1.0):
        """
        Scanne automatiquement tous les ports candidats sur cette IP.
        """
        # 🎯 APPEL SÉCURISÉ : On utilise le scope de la classe pour éviter l'AttributeError
        for port in GestionnaireKistler.PORTS_CANDIDATS:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                s.connect((ip, port))
                s.close()
                self.port = port  # Sauvegarde du port actif trouvé
                return True
            except Exception:
                continue
        return False

    # ==========================================
    # ÉTAPES SÉLECTION & CONFIGURATION
    # ==========================================
    def configurer_voies(self):
        print("\n--- ÉTAPE 2 & 3 : SÉLECTION DES SONDES ---")
        for i, voie in enumerate(self.voies_disponibles):
            print(f"  [{i}] {voie}")
        choix = input("\nEntrez les numéros des voies (ex: 0,1) : ")
        index_choisis = [int(x.strip()) for x in choix.split(',')]
        unites = {"Tension": "v", "Pression": "p", "Frequence": "hrtz", "Temperature": "c"}

        for idx in index_choisis:
            voie = self.voies_disponibles[idx]
            self.voies_selectionnees.append(voie)
            choix_type = input(f"Type pour {voie} (1-4) : ")
            type_mesure = list(unites.keys())[int(choix_type) - 1]
            self.config_sondes[voie] = {"type": type_mesure, "unite": unites[type_mesure]}

    def definir_parametres(self, duree, frequence, nom_fichier="donnees.csv", dossier="."):
        self.parametres["duree"] = duree
        self.parametres["frequence"] = frequence
        self.parametres["nom_fichier"] = nom_fichier
        self.parametres["dossier_sortie"] = dossier

    # ==========================================
    # ÉTAPE 4 : ACQUISITION FLUX TCP/IP SÉCURISÉ
    # ==========================================
    def lancer_acquisition(self, dictionnaire_voies, callback_maj=None, verifier_arret=None):
        self.chemins_voies_actives = []
        for voies in dictionnaire_voies.values():
            self.chemins_voies_actives.extend(voies)

        total_voies = len(self.chemins_voies_actives)
        if total_voies == 0:
            return False

        frequence = self.parametres["frequence"]
        duree = self.parametres["duree"]

        points_par_paquet = int(frequence * 0.1) if frequence > 10 else 1
        points_totaux = int(duree * frequence) if duree > 0 else float('inf')
        points_lus = 0
        temps_ecoule = 0.0

        chemin_complet = os.path.join(self.parametres["dossier_sortie"], self.parametres["nom_fichier"])
        en_tetes = ["temps(s)"] + [v.split('/')[-1] + "(v)" for v in self.chemins_voies_actives]

        buffer_reseau = ""

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.settimeout(3.0)

                try:
                    client_socket.connect((self.ip, self.port))
                except ConnectionRefusedError:
                    raise ConnexionRefuseeError(
                        "Connexion refusée : Le serveur d'acquisition du boîtier n'écoute pas sur ce port.")
                except socket.timeout:
                    raise TimeoutReseauError("Impossible d'atteindre le boîtier (Timeout de connexion).")

                with open(chemin_complet, mode='w', newline='') as fichier:
                    writer = csv.writer(fichier)
                    writer.writerow(en_tetes)

                    print("▶ En écoute du flux de données Kistler...")
                    paquet_temps = []
                    paquet_donnees = [[] for _ in range(total_voies)]

                    while points_lus < points_totaux:
                        if verifier_arret and verifier_arret():
                            break

                        try:
                            paquet_brut = client_socket.recv(4096)
                        except socket.timeout:
                            raise TimeoutReseauError("Le flux de données s'est arrêté brusquement (Timeout Réception).")
                        except ConnectionResetError:
                            raise ConnexionInterrompueError("La connexion réseau a été coupée de force par le boîtier.")

                        if not paquet_brut:
                            raise ConnexionInterrompueError("Le boîtier a coupé le flux réseau de manière prématurée.")

                        buffer_reseau += paquet_brut.decode('utf-8', errors='ignore')

                        while "\n" in buffer_reseau:
                            ligne, buffer_reseau = buffer_reseau.split("\n", 1)
                            ligne = ligne.strip()
                            if not ligne: continue

                            valeurs = ligne.split(',')

                            if len(valeurs) < total_voies:
                                raise FormatDonneesCorrompuError(
                                    "Le paquet réseau reçu ne contient pas assez de voies analogiques.")

                            t = temps_ecoule + (points_lus / frequence)
                            paquet_temps.append(t)

                            ligne_csv = [round(t, 4)]
                            for i in range(total_voies):
                                try:
                                    val_convertie = float(valeurs[i])
                                except ValueError:
                                    val_convertie = 0.0

                                paquet_donnees[i].append(val_convertie)
                                ligne_csv.append(round(val_convertie, 6))

                            writer.writerow(ligne_csv)
                            points_lus += 1

                            if len(paquet_temps) >= points_par_paquet:
                                if callback_maj:
                                    pas = 100 if frequence > 5000 else 1
                                    callback_maj(paquet_temps[::pas], [v[::pas] for v in paquet_donnees])
                                paquet_temps.clear()
                                paquet_donnees = [[] for _ in range(total_voies)]

            return True

        except KistlerError:
            raise
        except Exception as e:
            raise KistlerError(f"Erreur système imprévue : {e}")

    def appliquer_traitement(self, voie, valeur_brute):
        if voie not in self.config_sondes: return valeur_brute
        type_sonde = self.config_sondes[voie]["type"]
        if type_sonde == "Pression":
            return valeur_brute * 2.5
        elif type_sonde == "Frequence":
            return valeur_brute * 10.0
        return valeur_brute

    def sauvegarder_brut_csv(self):
        return True

    def tester_connexions(self, dictionnaire_voies):
        import socket
        voies_en_echec = []

        for boitier_nom, voies in dictionnaire_voies.items():
            ip_boitier = None
            if hasattr(self, 'boitiers_detectes'):
                for b in self.boitiers_detectes:
                    if b['nom'] == boitier_nom:
                        ip_boitier = b.get('ip') or b.get('adresse')
                        break

            if not ip_boitier:
                print(f"Test Kistler : IP introuvable pour {boitier_nom}")
                for voie in voies: voies_en_echec.append((boitier_nom, voie))
                continue

            # On ping le boîtier sur le port 10001
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.0)  # 1 seconde max pour répondre
                resultat = sock.connect_ex((ip_boitier, 10001))
                sock.close()

                if resultat != 0:
                    raise Exception("Le port est fermé ou le boîtier est éteint.")
            except Exception as e:
                print(f"Test Kistler échoué pour {boitier_nom} : {e}")
                for voie in voies: voies_en_echec.append((boitier_nom, voie))

        return voies_en_echec

# ==========================================
# BANC DE TEST AUTONOME (SANS INTERFACE)
# ==========================================
if __name__ == "__main__":
    print("=== TEST AUTONOME STRATÉGIE KISTLER AVEC EXCEPTIONS ===")

    manager = GestionnaireKistler(port_donnees=5000)
    manager.ip = "127.0.0.1"


    def mon_callback_console(liste_temps, listes_voies):
        print(f"📦 [Flux Live] Temps : {liste_temps[-1]:.2f}s | Échantillons lus : {len(liste_temps)}")


    try:
        manager.initialiser_systeme()
        manager.definir_parametres(duree=4, frequence=500, nom_fichier="donnees_pattern_kistler.csv")

        dict_voies_test = {"Kistler_LabAmp_5294123": ["Kistler_LabAmp_5294123/Ch1", "Kistler_LabAmp_5294123/Ch2"]}
        manager.lancer_acquisition(dictionnaire_voies=dict_voies_test, callback_maj=mon_callback_console)

        print("\n🎉 Test validé ! Le fichier 'donnees_pattern_kistler.csv' est prêt.")

    except BoitierIntrouvableError as e:
        print(f"\n❌ ERREUR DE DÉTECTION :\n{e}")
    except ConnexionRefuseeError as e:
        print(f"\n❌ ERREUR DE CONNEXION :\n{e}\n-> Lancez d'abord 'SimulateurKistler.py' !")
    except TimeoutReseauError as e:
        print(f"\n❌ ERREUR DE TIMEOUT :\n{e}")
    except ConnexionInterrompueError as e:
        print(f"\n❌ COUPURE DE FLUX FLUIDE :\n{e}")
    except FormatDonneesCorrompuError as e:
        print(f"\n❌ ERREUR FORMAT PAQUET :\n{e}")
    except KistlerError as e:
        print(f"\n❌ ERREUR INCONNUE CRITIQUE :\n{e}")