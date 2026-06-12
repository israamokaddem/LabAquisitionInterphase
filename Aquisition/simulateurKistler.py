import socket
import time
import math
import random


def lancer_simulateur(ip="127.0.0.1", port=5000, frequence=500):
    """
    Simule un boîtier Kistler LabAmp 5165A en ouvrant un serveur TCP
    et en envoyant un flux continu de données au format ASCII.
    """
    print(f"🤖 [SIMULATEUR] Serveur Kistler virtuel lancé sur {ip}:{port}")

    # Création du socket serveur TCP
    serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serveur.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serveur.bind((ip, port))
    serveur.listen(1)

    pas_de_temps = 1.0 / frequence

    try:
        while True:
            print("\n⏳ [SIMULATEUR] En attente de connexion de ton application PyQt6/Python...")
            connexion, adresse = serveur.accept()
            print(f"✅ [SIMULATEUR] Application connectée ! Provenance : {adresse}")

            temps_ecoule = 0.0

            try:
                while True:
                    # Génération de signaux physiques factices (Ex: Capteur de pression/force)
                    # Voie 1 : Une belle sinusoïde à 5 Hz (amplitude 5V) + bruit blanc
                    ch1 = (math.sin(2 * math.pi * 5 * temps_ecoule) * 5.0) + random.uniform(-0.1, 0.1)
                    # Voie 2 : Un cosinus à 2 Hz (amplitude 2.5V) + bruit blanc
                    ch2 = (math.cos(2 * math.pi * 2 * temps_ecoule) * 2.5) + random.uniform(-0.05, 0.05)

                    # Formatage de la ligne en chaîne de caractères (ASCII CSV) attendue par ton gestionnaire
                    ligne_data = f"{ch1:.4f},{ch2:.4f}\n"

                    # Envoi des octets sur le réseau local virtuel
                    connexion.sendall(ligne_data.encode('utf-8'))

                    temps_ecoule += pas_de_temps
                    time.sleep(pas_de_temps)  # On respecte la fréquence d'échantillonnage

            except (ConnectionResetError, BrokenPipeError):
                print("❌ [SIMULATEUR] L'application s'est déconnectée.")
            finally:
                connexion.close()

    except KeyboardInterrupt:
        print("\n⏹ [SIMULATEUR] Fermeture du simulateur.")
    finally:
        serveur.close()


if __name__ == "__main__":
    # On le lance sur le "localhost" (127.0.0.1)
    lancer_simulateur(ip="127.0.0.1", port=5000, frequence=500)