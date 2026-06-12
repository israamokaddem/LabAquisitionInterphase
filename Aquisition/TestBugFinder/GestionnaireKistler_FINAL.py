"""
GestionnaireKistler_FINAL.py
════════════════════════════
Protocole COMPLET reverse-engineered par Firefox DevTools + tester_api_kistler.py

Séquence confirmée :
  1. POST /api/daq/start  body={"duration":D,"rate":R,"ch":[1,2,...]}
     → {"key":"<UUID>","result":0}          ← KEY requis partout ensuite !

  2. GET  /api/daq/status?dateStamp=<ms>&key=<UUID>
     → {"lastError":0,"scans":N,"status":2,"result":0}
     scans s'incrémente jusqu'à duration × rate  →  acquisition terminée

  3. POST /api/daq/stop   body={"key":"<UUID>"}
     → {"result":0}

  4. GET  /api/daq/download?key=<UUID>
     → CSV ou JSON de toutes les données enregistrées

Dépendance unique : pip install requests
"""

import os
import csv
import re
import time
import json
import subprocess
import requests
from GestionnaireAquisition import GestionnaireAquisition


# ─── Exceptions ────────────────────────────────────────────────
class KistlerError(Exception): pass
class BoitierIntrouvableError(KistlerError): pass
class ConnexionRefuseeError(KistlerError): pass
class ConnexionInterrompueError(KistlerError): pass
class TimeoutReseauError(KistlerError): pass


# ════════════════════════════════════════════════════════════════
class GestionnaireKistler(GestionnaireAquisition):

    HTML_FINGERPRINT = "skybase-app"   # unique à l'UI Kistler LabAmp

    def __init__(self, numero_serie="5294123"):
        super().__init__()
        self.sn     = numero_serie
        self.ip     = None
        self.port   = 80
        self._session = None

        self.voies_disponibles     = []
        self.voies_selectionnees   = []
        self.config_sondes         = {}
        self.boitiers_detectes     = []
        self.chemins_voies_actives = []

        self.parametres = {
            "frequence":      1000,
            "duree":          10,
            "nom_fichier":    "donnees_kistler.csv",
            "dossier_sortie": "."
        }

    # ═══════════════════════════════════════════════════════════
    # ÉTAPE 1 — DÉTECTION
    # ═══════════════════════════════════════════════════════════
    def initialiser_systeme(self):
        """Scan ARP → test fingerprint HTTP → boîtier trouvé."""
        self.boitiers_detectes.clear()
        self.ip = None
        self._creer_session()

        ips = self._ips_depuis_arp()
        if not ips:
            raise BoitierIntrouvableError(
                "Table ARP vide.\n"
                "→ Ouvre le Wizard Network, clique sur le boîtier, puis relance."
            )
        for ip in ips:
            if self._est_kistler(ip):
                self._enregistrer_boitier(ip)

        if not self.boitiers_detectes:
            raise BoitierIntrouvableError(
                f"Aucun boîtier Kistler parmi {ips}.\n"
                "→ Vérifier alimentation et câble RJ45."
            )
        return True

    def initialiser_systeme_manuel(self, liste_ips):
        """Bypass du scan ARP avec IP fournie directement."""
        self.boitiers_detectes.clear()
        self.ip = None
        self._creer_session()
        for ip in [i.strip() for i in liste_ips if i.strip()]:
            if self._est_kistler(ip):
                self._enregistrer_boitier(ip)
        if not self.boitiers_detectes:
            raise BoitierIntrouvableError(f"Aucun boîtier Kistler à {liste_ips}")
        return True

    def _creer_session(self):
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Kistler-Py/4.0",
            "Accept":          "application/json, text/html, */*",
            "Accept-Language": "fr,en;q=0.8",
        })

    def _est_kistler(self, ip):
        try:
            r = self._session.get(f"http://{ip}/", timeout=2)
            if self.HTML_FINGERPRINT in r.text:
                print(f"  ✅ Fingerprint Kistler confirmé à {ip}")
                return True
        except Exception:
            pass
        return False

    def _enregistrer_boitier(self, ip):
        nom   = f"Kistler_LabAmp_{self.sn}"
        voies = [f"{nom}/Ch{i+1}" for i in range(4)]
        self.boitiers_detectes.append({
            "nom": nom, "modele": "5165A", "ip": ip,
            "total_voies": 4, "voies_dispos": voies
        })
        if self.ip is None:
            self.ip = ip
            self.voies_disponibles = voies

    def _ips_depuis_arp(self):
        try:
            os.system("ping -n 1 -w 1000 169.254.255.255 > nul 2>&1")
            time.sleep(0.8)
            out = subprocess.check_output(
                "arp -a", shell=True
            ).decode("cp1252", errors="ignore")
            ips = re.findall(r"(169\.254\.\d{1,3}\.\d{1,3})", out)
            candidates = [ip for ip in set(ips) if not ip.endswith(".255")]
            if candidates:
                print(f"  IPs ARP : {candidates}")
            return candidates
        except Exception as e:
            print(f"  Erreur ARP : {e}")
            return []

    # ═══════════════════════════════════════════════════════════
    # ÉTAPES 2 & 3 — CONFIGURATION
    # ═══════════════════════════════════════════════════════════
    def configurer_voies(self):
        for i, v in enumerate(self.voies_disponibles):
            print(f"  [{i}] {v}")
        choix = input("Voies (ex: 0,1) : ")
        unites = {"Tension": "v", "Pression": "p", "Frequence": "hrtz", "Temperature": "c"}
        for i in [int(x.strip()) for x in choix.split(",")]:
            voie = self.voies_disponibles[i]
            self.voies_selectionnees.append(voie)
            c = input(f"Type {voie} (1=Tension,2=Pression,3=Freq,4=Temp): ")
            t = list(unites.keys())[int(c) - 1]
            self.config_sondes[voie] = {"type": t, "unite": unites[t]}

    def definir_parametres(self, duree, frequence, nom_fichier="donnees.csv", dossier="."):
        self.parametres.update({
            "duree": duree, "frequence": frequence,
            "nom_fichier": nom_fichier, "dossier_sortie": dossier
        })

    # ═══════════════════════════════════════════════════════════
    # ÉTAPE 4 — ACQUISITION
    # Protocole complet avec KEY session
    # ═══════════════════════════════════════════════════════════
    def lancer_acquisition(self, dictionnaire_voies, callback_maj=None, verifier_arret=None):
        self.chemins_voies_actives = []
        for voies in dictionnaire_voies.values():
            self.chemins_voies_actives.extend(voies)

        total_voies = len(self.chemins_voies_actives)
        if total_voies == 0:
            return False

        freq        = self.parametres["frequence"]
        duree       = self.parametres["duree"]
        csv_path    = os.path.join(
            self.parametres["dossier_sortie"],
            self.parametres["nom_fichier"]
        )

        # Extraire les numéros de canaux depuis les noms de voies
        # "Kistler_LabAmp_xxx/Ch2" → 2
        channels = []
        for v in self.chemins_voies_actives:
            nom_ch = v.split("/")[-1]          # "Ch1", "Ch2", etc.
            num_ch = int(re.sub(r"[^0-9]", "", nom_ch))
            channels.append(num_ch)

        key = None
        try:
            # ── 1. DÉMARRER ─────────────────────────────────────────
            key = self._start(freq, duree, channels)
            print(f"  🔑 Session key : {key}")
            debut = time.time()

            # ── 2. ATTENTE TEMPORELLE (fiable — scans ne s'incrémente pas en temps réel)
            # Le boîtier enregistre exactement `duree` secondes puis génère le fichier.
            # On attend la durée + 0.5s de marge et on envoie la progression au callback.
            print(f"  ⏳ Acquisition en cours... ({duree}s @ {freq}Hz)")
            pas_cb = 0.25   # mise à jour du callback toutes les 250ms

            while True:
                t_ecoule = time.time() - debut

                # Arrêt manuel demandé par l'interface
                if verifier_arret and verifier_arret():
                    print("\n  🛑 Arrêt demandé par l'utilisateur")
                    break

                # Progression pour la barre/graphe PyQt
                if callback_maj:
                    pct = min(t_ecoule / duree, 1.0)
                    try:
                        callback_maj([t_ecoule], [[pct]])
                    except Exception:
                        pass

                # Acquisition terminée : durée écoulée
                if t_ecoule >= duree + 0.5:
                    print(f"\n  ✅ {duree}s écoulées — acquisition terminée")
                    break

                time.sleep(pas_cb)

            # Vérification optionnelle du status (pour debug)
            etat_final = self._get_status(key)
            print(f"  Status final : {etat_final}")

            # ── 3. ARRÊTER ──────────────────────────────────────────
            self._stop(key)

            # ── 4. TÉLÉCHARGER LES DONNÉES ──────────────────────────
            print("  📥 Téléchargement des données...")
            donnees_brutes = self._download(key)

            if donnees_brutes:
                # Parser et sauvegarder en CSV
                tableau = self._parser_donnees(donnees_brutes, channels, freq)
                self._sauvegarder_csv(tableau, channels, csv_path)

                # Envoyer les données réelles au graphe PyQt
                if callback_maj and tableau:
                    temps = [ligne[0] for ligne in tableau]
                    valeurs_par_voie = [
                        [ligne[i+1] for ligne in tableau]
                        for i in range(len(channels))
                    ]
                    # Décimer si trop de points pour le graphe
                    pas = max(1, len(temps) // 2000)
                    callback_maj(temps[::pas], [v[::pas] for v in valeurs_par_voie])

                print(f"  💾 Données sauvegardées : {csv_path}")
                return True
            else:
                print("  ⚠️  Aucune donnée téléchargée depuis /api/daq/download")
                return False

        except KistlerError:
            raise
        except Exception as e:
            raise KistlerError(f"Erreur acquisition : {e}")
        finally:
            # Toujours tenter l'arrêt même en cas d'erreur
            if key:
                try:
                    self._stop(key)
                except Exception:
                    pass

    # ─── Méthodes HTTP privées ─────────────────────────────────

    def _start(self, freq, duree, channels):
        """POST /api/daq/start → retourne le KEY UUID."""
        body = json.dumps(
            {"duration": duree, "rate": freq, "ch": channels},
            separators=(",", ":")
        )
        print(f"  🚀 POST /api/daq/start  body={body}")

        r = self._session.post(
            f"http://{self.ip}/api/daq/start",
            data=body,
            headers={"Content-Type": "text/plain;charset=UTF-8"},
            timeout=5
        )
        if r.status_code != 200:
            raise ConnexionRefuseeError(
                f"POST /api/daq/start → HTTP {r.status_code}\n{r.text[:200]}"
            )
        data = r.json()
        if data.get("result", 1) != 0:
            raise ConnexionRefuseeError(
                f"Démarrage refusé : {data}\n"
                "→ Vérifier que la licence API est activée dans Maintenance → Software Licensing"
            )
        return data["key"]

    def _get_status(self, key):
        """GET /api/daq/status?dateStamp=<ms>&key=<UUID>"""
        ts = int(time.time() * 1000)
        try:
            r = self._session.get(
                f"http://{self.ip}/api/daq/status",
                params={"dateStamp": ts, "key": key},
                timeout=3
            )
            return r.json() if r.status_code == 200 else {}
        except requests.exceptions.Timeout:
            raise TimeoutReseauError("Timeout sur GET /api/daq/status")
        except Exception as e:
            raise TimeoutReseauError(f"Status polling échoué : {e}")

    def _stop(self, key):
        """POST /api/daq/stop  body={"key":"<UUID>"}"""
        body = json.dumps({"key": key}, separators=(",", ":"))
        try:
            r = self._session.post(
                f"http://{self.ip}/api/daq/stop",
                data=body,
                headers={"Content-Type": "text/plain;charset=UTF-8"},
                timeout=3
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("result") == 0:
                    print("  ⏹️  Arrêt OK")
                else:
                    print(f"  ⚠️  Arrêt : {data}")
        except Exception as e:
            print(f"  ⚠️  Arrêt : {e}")

    def _download(self, key):
        """
        Télécharge les données après acquisition.
        Essaie GET et POST, avec clé en paramètre URL ET en body JSON.
        Chaque tentative affiche la réponse exacte pour aider au debug.
        """
        body_key = json.dumps({"key": key}, separators=(",", ":"))
        headers_plain = {"Content-Type": "text/plain;charset=UTF-8"}

        tentatives = [
            # (méthode, url, params_url, body, description)
            ("GET",  "/api/daq/download",  {"key": key},                   None,     "GET download + key param"),
            ("POST", "/api/daq/download",  {},                              body_key, "POST download + key body"),
            ("GET",  "/api/daq/download",  {"key": key, "format": "csv"},  None,     "GET download CSV"),
            ("GET",  "/api/daq/download",  {"key": key, "format": "json"}, None,     "GET download JSON"),
            ("GET",  "/api/daq/data",      {"key": key},                   None,     "GET /api/daq/data"),
            ("POST", "/api/daq/data",      {},                              body_key, "POST /api/daq/data"),
            ("GET",  "/api/daq/result",    {"key": key},                   None,     "GET /api/daq/result"),
            ("POST", "/api/daq/result",    {},                              body_key, "POST /api/daq/result"),
        ]

        for methode, endpoint, params, body, desc in tentatives:
            url = f"http://{self.ip}{endpoint}"
            try:
                if methode == "GET":
                    r = self._session.get(url, params=params, timeout=30)
                else:
                    r = self._session.post(url, params=params, data=body,
                                           headers=headers_plain, timeout=30)

                contenu = r.text.strip() if r.text else ""
                # Toujours afficher la réponse pour debug
                print(f"  [{methode}] {endpoint} → HTTP {r.status_code} "
                      f"({len(r.content)} o) : {contenu[:120]}")

                # Données valides = pas de page HTML, pas de "not found", taille > 50
                if (r.status_code == 200
                        and len(r.content) > 50
                        and not contenu.startswith("<!DOCTYPE")
                        and "not found" not in contenu.lower()
                        and "404" not in contenu[:20]):
                    print(f"  ✅ Données trouvées via : {desc}")
                    return contenu

            except Exception as e:
                print(f"  [{methode}] {endpoint} → Erreur : {e}")

        print("  ❌ Download échoué sur tous les endpoints.")
        print("  → Cherche dans Firefox DevTools ce qui est appelé après avoir cliqué")
        print("    'Stop' puis 'Download' dans l'interface web du boîtier.")
        return None

    def _parser_donnees(self, contenu_brut, channels, freq):
        """
        Parse les données téléchargées (CSV ou JSON) en tableau Python.
        Retourne [[t, ch1_val, ch2_val, ...], [...], ...]
        """
        contenu = contenu_brut.strip()

        # ── Cas 1 : JSON ──────────────────────────────────────
        if contenu.startswith(("{", "[")):
            try:
                data = json.loads(contenu)
                tableau = []

                # Format A : {"data": [[t, v1, v2], ...]}
                if isinstance(data, dict) and "data" in data:
                    for pt in data["data"]:
                        if isinstance(pt, list) and len(pt) > 0:
                            tableau.append([float(v) for v in pt])

                # Format B : [[t, v1, v2], ...]
                elif isinstance(data, list) and data and isinstance(data[0], list):
                    tableau = [[float(v) for v in ligne] for ligne in data]

                # Format C : [{"t":0.001,"ch1":1.23,"ch2":0.45}, ...]
                elif isinstance(data, list) and data and isinstance(data[0], dict):
                    for pt in data:
                        t = pt.get("t", pt.get("time", pt.get("timestamp", 0)))
                        vals = [float(t)]
                        for ch in channels:
                            vals.append(float(pt.get(f"ch{ch}", pt.get(str(ch), 0.0))))
                        tableau.append(vals)

                return tableau
            except Exception as e:
                print(f"  ⚠️  Parse JSON échoué : {e}")

        # ── Cas 2 : CSV ───────────────────────────────────────
        tableau = []
        reader = csv.reader(contenu.splitlines())
        en_tete_sautee = False
        for ligne in reader:
            if not ligne:
                continue
            try:
                # Sauter la ligne d'en-tête si elle contient du texte
                float(ligne[0])
            except ValueError:
                if not en_tete_sautee:
                    en_tete_sautee = True
                    continue
                continue

            try:
                tableau.append([float(v) for v in ligne])
            except ValueError:
                pass

        return tableau

    def _sauvegarder_csv(self, tableau, channels, csv_path):
        """Sauvegarde le tableau en CSV avec en-têtes propres."""
        en_tetes = ["temps(s)"] + [f"Ch{ch}(v)" for ch in channels]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(en_tetes)
            for ligne in tableau:
                # S'assurer d'avoir le bon nombre de colonnes
                while len(ligne) < len(en_tetes):
                    ligne.append(0.0)
                writer.writerow([round(v, 6) for v in ligne[:len(en_tetes)]])

    # ═══════════════════════════════════════════════════════════
    # UTILITAIRES
    # ═══════════════════════════════════════════════════════════
    def appliquer_traitement(self, voie, valeur_brute):
        if voie not in self.config_sondes:
            return valeur_brute
        t = self.config_sondes[voie]["type"]
        if t == "Pression":  return valeur_brute * 2.5
        if t == "Frequence": return valeur_brute * 10.0
        return valeur_brute

    def sauvegarder_brut_csv(self):
        return True


# ════════════════════════════════════════════════════════════════
# TEST COMPLET EN LIGNE DE COMMANDE
# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    IP_BOITIER = "169.254.128.144"   # ← Mettre à jour si l'IP a changé

    print(f"=== TEST FINAL GestionnaireKistler — {IP_BOITIER} ===\n")

    m = GestionnaireKistler()
    try:
        m.initialiser_systeme_manuel([IP_BOITIER])
    except Exception as e:
        print(f"❌ Détection : {e}")
        sys.exit(1)

    m.definir_parametres(
        duree=3,           # 3 secondes de test
        frequence=100,     # 100 Hz (rapide pour le test)
        nom_fichier="test_final_kistler.csv",
        dossier="."
    )

    nom = m.boitiers_detectes[0]["nom"]
    dvt = {nom: [f"{nom}/Ch1", f"{nom}/Ch2"]}

    def cb_console(temps, valeurs):
        """Callback simplifié pour voir la progression dans la console."""
        print(f"  [callback] t={temps[-1]:.1f}s", end="\r")

    print("\n--- Lancement de l'acquisition ---")
    try:
        ok = m.lancer_acquisition(dvt, callback_maj=cb_console)
        print(f"\n{'✅ Succès !' if ok else '❌ Échec'}")
        if ok and os.path.exists("test_final_kistler.csv"):
            with open("test_final_kistler.csv") as f:
                lignes = f.readlines()
            print(f"CSV créé : {len(lignes)} lignes")
            print("Premières lignes :")
            for l in lignes[:5]:
                print(f"  {l.strip()}")
    except Exception as e:
        print(f"\n❌ {e}")