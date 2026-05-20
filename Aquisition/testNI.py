import os
import time
import nidaqmx
from nidaqmx.constants import AcquisitionType


def tester_acquisition_ni():
    print(f"\n{'='*60}")
    print("TEST INTERFAÇAGE - BOÎTIER NI cDAQ-9184 : National instrument")
    print(f"{'='*60}")

    try:
        # 1. DÉTECTION DES VOIES ACTIVES / DISPONIBLES
        system = nidaqmx.system.System.local()
        print("\n[1] Recherche des périphériques NI connectés...")

        if not system.devices:
            print(
                "❌ Aucun boîtier NI détecté. Vérifie le branchement réseau/USB ou la config dans NI MAX."
            )
            return

        # On liste le premier appareil trouvé (ex: cDAQ9184)
        device = system.devices[0]
        nom_boitier = device.name
        print(f" ✓ Boîtier détecté : {nom_boitier} ({device.product_type})")

        # Détection des voies analogiques d'entrée disponibles (AI)
        voies_disponibles = [ch.name for ch in device.ai_physical_chans]
        print(f" ✓ Voies physiques disponibles ({len(voies_disponibles)}) :")
        for voie in voies_disponibles:
            print(f"   • {voie}")

        if not voies_disponibles:
            print("⚠ Aucune voie d'entrée analogique trouvée sur ce module.")
            return

        # 2. PARAMÉTRAGE DE L'ACQUISITION (Simulé depuis des futurs choix d'interface)
        frequence = 1000.0  # Fréquence en Hz (ex: 1000 points par seconde)
        temps_acquisition = 3.0  # Durée en secondes
        nombre_points = int(frequence * temps_acquisition)
        fichier_sortie = "acquisition_test_ni.txt"

        # On choisit arbitrairement de tester sur la première voie pour l'exemple
        voie_a_tester = voies_disponibles[0]

        print(f"\n[2] Configuration de la tâche d'acquisition...")
        print(f"  • Voie sélectionnée : {voie_a_tester}")
        print(f"  • Fréquence : {frequence} Hz")
        print(f"  • Durée : {temps_acquisition} s ({nombre_points} points)")
        print(f"  • Fichier cible : {fichier_sortie}")

        # 3. LANCEMENT DE L'ACQUISITION
        # On crée une tâche d'acquisition (Task)
        with nidaqmx.Task() as t_acq:
            # On ajoute la voie de tension analogique à la tâche
            t_acq.ai_channels.add_ai_voltage_chan(voie_a_tester)

            # On configure le timing (Horloge, Fréquence, Mode Continu ou Fini)
            t_acq.timing.cfg_samp_clk_timing(
                rate=frequence,
                sample_mode=AcquisitionType.FINITE,
                samps_per_chan=nombre_points,
            )

            print("\n[3] Acquisition en cours... Ne pas débrancher.")
            t_debut = time.time()

            # Lit les données (bloquant le temps que tous les points soient collectés)
            donnees = t_acq.read(number_of_samples_per_channel=nombre_points) #a revoir 

            t_fin = time.time()
            print(
                f" ✓ Acquisition terminée avec succès en {t_fin - t_debut:.2f} secondes !"
            )

        # 4. ÉCRITURE DANS LE FICHIER (Format standardisé pour ton stage)
        print(f"\n[4] Écriture des données dans : {fichier_sortie}")
        with open(fichier_sortie, "w", encoding="utf-8") as f:
            f.write("# ==========================================\n")
            f.write("# FICHIER D'ACQUISITION LABORATOIRE\n")
            f.write(f"# Date : {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Boîtier source : {nom_boitier}\n")
            f.write(f"# Voie : {voie_a_tester}\n")
            f.write(f"# Fréquence : {frequence} Hz\n")
            f.write("# ==========================================\n")
            f.write("# Index | Temps (s) | Tension (V)\n")

            for i, tension in enumerate(donnees):
                temps_relatif = i / frequence
                f.write(f"{i:6d}  {temps_relatif:10.4f}  {tension:12.6f}\n")

        print(" ✓ Fichier enregistré et prêt pour le traitement.")

    except nidaqmx.errors.DaqError as e:
        print(f"\n❌ Erreur matérielle NI-DAQmx : {e}")
    except Exception as e:
        print(f"\n❌ Erreur inattendue : {e}")


if __name__ == "__main__":
    tester_acquisition_ni()