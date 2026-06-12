import cv2
import numpy as np
import os
import time

import matplotlib

matplotlib.use('QtAgg')  # Force Matplotlib à utiliser la même technologie que ton interface
import matplotlib.pyplot as plt
from itertools import product

from PyQt6.QtWidgets import QFileDialog, QMessageBox
from tqdm import tqdm


class Imagerie:
    def __init__(self, image_path=None):
        """
        Constructeur de la classe Imagerie.
        Initialise les paramètres de traitement d'image et les variables de session.
        """
        self.img_redressee = None
        self.image_path = image_path
        self.base_image = None

        # Variables pour la sélection polygonale (anciennement globales)
        self.zone_selection = None
        self.selecting = False
        self.polygon_points = []
        self.current_point = (-1, -1)

        # Variables pour la correction de distorsion
        self.points_pixels_origine = None
        self.points_cm_origine = None

        # Variables pour la correction perspective
        self.transformed_pixels_perspective = None
        self.transformed_physical_perspective = None
        self.H_perspective = None
        self.w_perspective, self.h_perspective = 0, 0

        # Variables pour la correction radiale
        self.transformed_pixels_radiale = None
        self.transformed_physical_radiale = None
        self.transformed_pixels_radiale_cropped = None
        self.transformed_physical_radiale_cropped = None
        self.image_path = ""
        self.mtx = None
        self.dist = None
        self.w_radiale, self.h_radiale = 0, 0

        # Configuration pour l'interface (similaire à Decomposition)
        self.variables = ["Contrast", "Brightness", "Zoom"]

    def imflatfield(self, I, sigma):
        """
        Applique un flat-field correction à l'image.
        Logique et calculs conservés à l'identique du script original.
        """
        A = I.astype(np.float32)
        filterSize = int(2 * np.ceil(2 * sigma) + 1)

        shading = cv2.GaussianBlur(A, (filterSize, filterSize), sigma, borderType=cv2.BORDER_REPLICATE)
        meanVal = np.mean(A)
        shading = np.maximum(shading, 1e-6)
        B = A * meanVal / shading
        B = B - meanVal + 128
        B = np.round(np.clip(B, 0, 255)).astype(np.uint8)

        return B

    def select_zone(self, event, x, y, flags, param):
        """
        Gère les événements souris pour dessiner le polygone de sélection.
        Identique à la logique de votre script original.
        """
        if self.base_image is None:  ## ajout Israa de creation d'une copie de l'image actuelle
            self.base_image = param.copy()

        if event == cv2.EVENT_LBUTTONDOWN:
            self.selecting = True
            self.polygon_points.append((x, y))
            print(f"Point ajouté : ({x}, {y})")

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.selecting:
                self.current_point = (x, y)

        elif event == cv2.EVENT_RBUTTONDOWN:
            self.selecting = False
            if len(self.polygon_points) > 2:
                print("Sélection terminée.")
            else:
                print("Le polygone doit avoir au moins 3 points.")

        img_temp = self.base_image.copy()

        # On dessine tous les points validés
        for pt in self.polygon_points:
            cv2.circle(img_temp, pt, 15, (0, 255, 0), -1)

        # On dessine la ligne entre le dernier point et la souris (effet élastique)
        if self.selecting and len(self.polygon_points) > 0:
            cv2.line(img_temp, self.polygon_points[-1], self.current_point, (255, 0, 0), 2)

        # On affiche l'image rafraîchie
        cv2.imshow("Selectionnez la zone du damier", img_temp)

    def detecter_coins_dans_zone(self, image_path, pattern=(9, 6)):
        if self.polygon_points is None or len(self.polygon_points) < 3:
            print("Erreur : Veuillez d'abord sélectionner une zone.")
            return None

        img = cv2.imread(image_path)
        if img is None: return None

        # --- ÉTAPE 1 : Préparer l'image ---
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # --- # Masque pour isoler le damier--
        mask = np.zeros(gray.shape, dtype=np.uint8)
        roi_corners = np.array([self.polygon_points], dtype=np.int32)
        cv2.fillPoly(mask, roi_corners, 255)

        # --- ÉTAPE 3 : ASTUCE CRUCIALE ---
        # Au lieu de mettre du noir autour du damier, on met du BLANC.
        # # On force le fond en blanc pour aider OpenCV
        analysis_img = cv2.bitwise_and(gray, gray, mask=mask)
        inverse_mask = cv2.bitwise_not(mask)
        analysis_img = cv2.add(analysis_img, inverse_mask)  # Remplit l'extérieur en blanc

        # --- ÉTAPE 4 : Détection avec paramètres robustes ---
        # On enlève FAST_CHECK qui peut faire échouer la détection sur des images difficiles
        flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE

        ret, corners = cv2.findChessboardCorners(analysis_img, pattern, flags)

        if ret:
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            self.points_pixels_origine = corners2

            # --- CORRECTION ICI : ON REMPLIT LES VARIABLES POUR LA SURFACE LIBRE ---
            self.points_pixels_origine = corners2
            self.transformed_pixels_radiale = corners2.reshape(-1, 2)  # Format (N, 2)

            nx, ny = pattern  # Ici (9, 6)
            grid = np.zeros((nx * ny, 2), np.float32)
            grid[:, :2] = np.mgrid[0:nx, 0:ny].T.reshape(-1, 2)

            # On multiplie par la taille réelle du carré (ex: 1.0 cm ou valeur de l'interface)
            self.points_cm_origine = grid

            # VISUALISATION POUR DEBUG (Optionnel)
            img_visu = img.copy()
            cv2.drawChessboardCorners(img_visu, pattern, corners2, ret)
            cv2.imshow("Coins detectes", cv2.resize(img_visu, (1000, 700)))
            cv2.waitKey(500)

            print(f"{len(corners2)} coins détectés avec succès.")
            print(f"Pixels: {len(self.points_pixels_origine)} | CM: {len(self.points_cm_origine)}")
            return corners2
        else:
            # DEBUG : Si ça échoue, on regarde ce que l'ordi a essayé de lire
            cv2.imshow("Zone analysee (Doit etre nette)", cv2.resize(analysis_img, (800, 600)))
            cv2.waitKey(1000)
            print("Échec de la détection.")
            return None

    '''
    def detecter_coins_dans_zone(self, image_path, pattern=(9,6)):
        """
        Détecte les coins du damier dans la zone sélectionnée par l'utilisateur.
        pattern : (colonnes, lignes) du damier interne.
        """
        if self.polygon_points is None or len(self.polygon_points) < 3:
            print("Erreur : Veuillez d'abord sélectionner une zone avec select_zone.")
            return None

        # Charger l'image
        img = cv2.imread(image_path)
        if img is None:
            print(f"Erreur : Impossible de charger l'image {image_path}")
            return None

        # 1. Création d'un masque basé sur le polygone sélectionné
        mask = np.zeros(img.shape[:2], dtype=np.uint8)
        roi_corners = np.array([self.polygon_points], dtype=np.int32)
        cv2.fillPoly(mask, roi_corners, 255)

        # 2. Appliquer le masque (on ne garde que la zone du damier)
        masked_img = cv2.bitwise_and(img, img, mask=mask)
        gray = cv2.cvtColor(masked_img, cv2.COLOR_BGR2GRAY)

        # 3. Détection des coins du damier
        # On utilise CALIB_CB_ADAPTIVE_THRESH pour plus de robustesse
        ret, corners = cv2.findChessboardCorners(
            gray, pattern,
            cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_FAST_CHECK + cv2.CALIB_CB_NORMALIZE_IMAGE
        )

        if ret:
            # Affiner la position des coins au pixel près (SubPixel)
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

            self.points_pixels_origine = corners2
            print(f"{len(corners2)} coins détectés avec succès.")
            return corners2
        else:
            print("Échec de la détection. Essayez d'ajuster le contraste ou la zone.")
            return None
 '''

    # calibration
    def calculer_coordonnees_physiques(self, spacing_cm=4.0, n_initial=1, pattern=(9, 6)):
        """
        Génère les coordonnées physiques (x, y) en cm pour chaque coin détecté.
        spacing_cm : taille d'un côté de carré du damier (ex: 4cm).
        n_initial : décalage horizontal (nombre de carrés depuis le batteur).
        """
        if self.points_pixels_origine is None:
            print("Erreur : Aucun coin détecté. Lancez 'detecter_coins_dans_zone' d'abord.")
            return None

        # On récupère les dimensions du pattern (colonnes, lignes)
        # Supposons un pattern de (16, 9) comme dans l'exemple précédent
        nx, ny = pattern

        # Génération de la grille théorique en cm
        # x_coords ira de (n_initial * spacing) à ((n_initial + nx) * spacing)
        x_phys = (np.arange(nx) + n_initial) * spacing_cm
        y_phys = np.arange(ny) * spacing_cm

        # Création du maillage (meshgrid)
        X_phys, Y_phys = np.meshgrid(x_phys, y_phys)

        # Mise en forme pour correspondre à la structure de OpenCV (N, 2)
        self.points_cm_origine = np.vstack([X_phys.ravel(), Y_phys.ravel()]).T.astype(np.float32)

        self.transformed_physical_radiale = self.points_cm_origine

        print(f"Calibration terminée : {len(self.transformed_physical_radiale)} points physiques générés.")
        return self.points_cm_origine

    def calculer_homographie_et_redresser(self, image):
        """
        Calcule la matrice d'homographie et redresse l'image pour supprimer la perspective.
        image : l'image originale chargée (BGR).
        """
        if self.points_pixels_origine is None or self.points_cm_origine is None:
            print("Erreur : Points de calibration manquants.")
            return None

        # 1. Calcul de la matrice d'homographie (H)
        # Elle fait le lien entre les pixels du damier tordu et la grille théorique
        self.H_perspective, _ = cv2.findHomography(
            self.points_pixels_origine,
            self.points_cm_origine
        )

        # 2. Définition de la taille de l'image de sortie
        # On définit une résolution (ex: 10 pixels par cm) pour l'image redressée
        resolution = 40
        max_x = int(np.max(self.points_cm_origine[:, 0]) * resolution)
        max_y = int(np.max(self.points_cm_origine[:, 1]) * resolution)
        self.w_perspective, self.h_perspective = max_x, max_y

        # 3. Application de la transformation (Warp Perspective)
        # On crée une nouvelle matrice H qui inclut le facteur d'échelle (résolution)
        scale_matrix = np.array([[resolution, 0, 0], [0, resolution, 0], [0, 0, 1]])
        H_scaled = scale_matrix @ self.H_perspective

        self.img_redressee = cv2.warpPerspective(
            image,
            H_scaled,
            (max_x, max_y)
        )

        print("Image redressée avec succès.")
        return self.img_redressee

    def reinitialiser_origine_y_points_cm(self, y_pixel_surface):
        """
        Décale l'origine des coordonnées physiques pour que y=0
        corresponde à la surface libre au repos.
        y_pixel_surface : la coordonnée Y en pixel cliquée par l'utilisateur.
        """
        if self.H_perspective is None:
            print("Erreur : Calculez d'abord l'homographie.")
            return

        # 1. Convertir le point cliqué (pixel) en coordonnée physique (cm)
        # On crée un point homogène [x, y, 1]
        point_pixel = np.array([[[self.polygon_points[0][0], y_pixel_surface]]], dtype=np.float32)

        # On utilise la matrice H pour projeter ce point dans le monde réel
        point_physique_surface = cv2.perspectiveTransform(point_pixel, self.H_perspective)
        y_physique_zero = point_physique_surface[0][0][1]

        # 2. Soustraire cette valeur à tous nos points de calibration
        # Ainsi, le point cliqué devient Y = 0
        self.points_cm_origine[:, 1] -= y_physique_zero

        print(f"Origine Y recalée. Décalage appliqué : {y_physique_zero:.2f} cm")

    def detecter_surface_libre_et_recaler(self,mod_lot=False):

        print(f"\n{'=' * 60}")
        print("PHASE DE DÉTECTION DE LA SURFACE LIBRE ET RECALAGE VERTICAL")
        print(f"{'=' * 60}")

        HAUTEUR_RECTANGLE = 50
        NOMBRE_SOUS_ZONES = 30
        LARGEUR_RECTANGLE = None
        ZOOM_PROFIL = 100
        YLIM_INF = 500
        YLIM_SUP = 640

        # --- MODIFICATION INTERFACE : Utilisation de l'image en mémoire ---
        if self.img_redressee is None:
            print("Erreur : Aucune image redressée disponible.")
            return False

        image_path = "Image en mémoire"  # Pour garder la variable dans les logs
        img = self.img_redressee.copy()
        image_path = self.image_path if self.image_path else "Image_Interface.png"
        # -----------------------------------------------------------------

        if self.transformed_pixels_radiale is None or self.transformed_physical_radiale is None:
            print("Points de calibration radiale non disponibles.")
            print("Veuillez d'abord exécuter la phase de correction radiale.")
            return False

        print(f"\nPoints de calibration disponibles :")
        print(f"  • {len(self.transformed_pixels_radiale)} points pixels (après radiale)")
        print(f"  • {len(self.transformed_physical_radiale)} points cm correspondants")

        def convert_pixel_to_cm(x_pixel, y_pixel):
            """
            Convertit la position (x,y) en pixels en centimètres en utilisant la matrice d'homographie
            """
            try:
                # Calcul de la matrice d'homographie entre points pixels et points cm
                H, _ = cv2.findHomography(
                    np.array(self.transformed_pixels_radiale, dtype=np.float32),
                    np.array(self.transformed_physical_radiale, dtype=np.float32)
                )

                # Conversion d'un point pixel en cm
                point_pixel = np.array([[[x_pixel, y_pixel]]], dtype=np.float32)
                point_cm = cv2.perspectiveTransform(point_pixel, H)

                return point_cm[0][0]  # Retourne (x_cm, y_cm)

            except Exception as e:
                print(f"Erreur lors de la conversion pixel → cm : {e}")
                return (0, 0)

        def convert_surface_libre_to_cm(ligne_pixel, largeur_image):
            """
            Convertit la ligne de surface libre (en pixels) en centimètres
            et vérifie la cohérence sur plusieurs points
            """
            print(f"\n=== CONVERSION PIXELS → CENTIMÈTRES ===")
            print(f"Ligne de surface libre détectée : {ligne_pixel} pixels")

            # Points de test le long de la ligne
            points_test = [
                (largeur_image * 0.25, ligne_pixel),  # Gauche
                (largeur_image * 0.5, ligne_pixel),  # Centre
                (largeur_image * 0.75, ligne_pixel)  # Droite
            ]

            conversions_cm = []

            for i, (x_px, y_px) in enumerate(points_test):
                x_cm, y_cm = convert_pixel_to_cm(x_px, y_px)
                conversions_cm.append((x_cm, y_cm))
                print(f"Point {i + 1} - Pixel: ({x_px:.0f}, {y_px:.0f}) → CM: ({x_cm:.2f}, {y_cm:.2f})")

            # Vérification de la cohérence (les valeurs Y doivent être proches)
            y_values = [y for _, y in conversions_cm]
            y_moyen = np.mean(y_values)
            y_ecart = np.std(y_values)

            print(f"\nVérification de cohérence :")
            print(f"  Valeur Y moyenne : {y_moyen:.3f} cm")
            print(f"  Écart-type : {y_ecart:.3f} cm")

            if y_ecart < 0.1:  # Seuil de tolérance de 1 mm
                print(f"  ✓ Conversion cohérente - Surface libre à {y_moyen:.2f} cm")
            else:
                print(f"  ⚠ Attention : variations détectées le long de la surface libre")
                print(f"  Valeur retenue : {y_moyen:.2f} cm (moyenne)")

            return y_moyen, conversions_cm

        # On garde exactement la structure d'Alexandre
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        print(f"Image chargée : {img}")
        print(f"Dimensions de l'image : {img.shape}")
        print(f"\nParamètres utilisés :")
        print(f"  - Hauteur rectangle : {HAUTEUR_RECTANGLE} pixels")
        print(f"  - Nombre de sous-zones : {NOMBRE_SOUS_ZONES}")
        print(f"  - Limites Y pour calcul d'intensité : {YLIM_INF} à {YLIM_SUP} pixels")

        if LARGEUR_RECTANGLE is None:
            largeur_text = "Toute l'image"
        else:
            largeur_text = f"{LARGEUR_RECTANGLE} pixels"
        print(f"  - Largeur rectangle : {largeur_text}")

        # 1. Calculer la somme des intensités pour chaque ligne de pixels DANS LA ZONE LIMITÉE
        somme_lignes = np.zeros(img.shape[0])

        # Calculer la somme uniquement pour les lignes dans la plage YLIM
        for y in range(img.shape[0]):
            if YLIM_INF <= y <= YLIM_SUP:
                somme_lignes[y] = np.sum(img[y, :])
            else:
                somme_lignes[y] = 0

            # 2. Trouver la ligne avec l'intensité maximale DANS LA ZONE LIMITÉE
            masque_zone = np.zeros(img.shape[0], dtype=bool)
            masque_zone[YLIM_INF:YLIM_SUP + 1] = True

        # Trouver le maximum uniquement dans la zone limitée
        if np.any(masque_zone):
            ligne_max = np.argmax(somme_lignes[masque_zone]) + YLIM_INF
            intensite_max = somme_lignes[ligne_max]
        else:
            ligne_max = (YLIM_INF + YLIM_SUP) // 2
            intensite_max = 0
            print("⚠ ATTENTION : Aucune ligne dans la zone YLIM pour calculer l'intensité")

        print(f"\nLigne avec intensité maximale : {ligne_max}")
        print(f"Intensité maximale : {intensite_max}")

        # CONVERSION DE LA LIGNE DE SURFACE LIBRE EN CENTIMÈTRES
        hauteur_cm, points_conversion = convert_surface_libre_to_cm(
            ligne_max, img.shape[1]
        )
        # =============================================================================
        # RECALAGE VERTICAL DES COORDONNÉES PHYSIQUES
        # =============================================================================

        print(f"\n{'=' * 60}")
        print("RECALAGE VERTICAL DES COORDONNÉES PHYSIQUES")
        print(f"{'=' * 60}")
        print(f"Hauteur de surface libre détectée : {hauteur_cm:.4f} cm")

        # Sauvegarder les anciennes coordonnées pour comparaison
        anciennes_coords_y = [y for _, y in self.transformed_physical_radiale]

        # Appliquer le recalage selon le signe de hauteur_cm
        if hauteur_cm > 0:
            print(f"\n➡️ hauteur_cm = {hauteur_cm:.4f} cm > 0")
            print(f"   → AJOUT de cette valeur aux coordonnées Y")
            nouvelle_coords_y = [y + hauteur_cm for y in anciennes_coords_y]
        elif hauteur_cm < 0:
            print(f"\n➡️ hauteur_cm = {hauteur_cm:.4f} cm < 0")
            print(f"   → SOUSTRACTION de cette valeur (addition de |{abs(hauteur_cm):.4f}|) aux coordonnées Y")
            nouvelle_coords_y = [y + hauteur_cm for y in anciennes_coords_y]  # Ajout car hauteur_cm négatif
        else:
            print(f"\n➡️ hauteur_cm = 0 cm")
            print(f"   → AUCUN recalage appliqué")
            nouvelle_coords_y = anciennes_coords_y.copy()

        # Mettre à jour les coordonnées physiques
        nouvelle_coords = []
        for i, (x, _) in enumerate(self.transformed_physical_radiale):
            nouvelle_coords.append((x, nouvelle_coords_y[i]))

        self.transformed_physical_radiale = nouvelle_coords

        # =============================================================================
        # AFFICHAGE DES NOUVELLES COORDONNÉES
        # =============================================================================

        print(f"\n{'=' * 80}")
        print("COORDONNÉES APRÈS RECALAGE VERTICAL")
        print(f"{'=' * 80}")
        print(
            f"{'No':<6} {'X (px)':<12} {'Y (px)':<12} {'X (cm)':<12} {'Y (cm) ANCIEN':<16} {'Y (cm) NOUVEAU':<16} {'Écart (cm)':<12}")
        print(f"{'-' * 90}")

        for i in range(len(self.transformed_pixels_radiale)):
            px, py = self.transformed_pixels_radiale[i]
            x_cm, y_cm_nouveau = self.transformed_physical_radiale[i]
            y_cm_ancien = anciennes_coords_y[i]
            ecart = y_cm_nouveau - y_cm_ancien

            print(
                f"{i + 1:<6} {px:<12.2f} {py:<12.2f} {x_cm:<12.4f} {y_cm_ancien:<16.4f} {y_cm_nouveau:<16.4f} {ecart:<12.4f}")

        print(f"{'=' * 90}")

        # =============================================================================
        # CALCUL ET AFFICHAGE DE LA NOUVELLE MATRICE D'HOMOGRAPHIE
        # =============================================================================

        print(f"\n{'=' * 60}")
        print("NOUVELLE MATRICE D'HOMOGRAPHIE")
        print(f"{'=' * 60}")

        try:
            # Calcul de la nouvelle matrice d'homographie
            H_nouvelle, _ = cv2.findHomography(
                np.array(self.transformed_pixels_radiale, dtype=np.float32),
                np.array(self.transformed_physical_radiale, dtype=np.float32)
            )

            print(f"\nMatrice d'homographie H (pixels -> cm) APRÈS RECALAGE :")
            np.set_printoptions(precision=10, suppress=True)
            for i in range(3):
                print(f"  [{H_nouvelle[i][0]:15.10f} {H_nouvelle[i][1]:15.10f} {H_nouvelle[i][2]:15.10f}]")

            # Comparaison avec l'ancienne matrice
            H_ancienne, _ = cv2.findHomography(
                np.array(self.transformed_pixels_radiale, dtype=np.float32),
                np.array([(x, y_ancien) for (x, y_ancien) in
                          zip([x for x, _ in self.transformed_physical_radiale], anciennes_coords_y)], dtype=np.float32)
            )

            print(f"\nVariation de la matrice (nouvelle - ancienne) :")
            diff_H = H_nouvelle - H_ancienne
            for i in range(3):
                print(f"  [{diff_H[i][0]:+15.10f} {diff_H[i][1]:+15.10f} {diff_H[i][2]:+15.10f}]")
        except Exception as e:
            print(f"Erreur lors du calcul de l'homographie : {e}")

        # =============================================================================
        # VISUALISATION DE LA DÉTECTION
        # =============================================================================

        # 3. Définir la hauteur du rectangle autour de cette ligne

        y_min = max(YLIM_INF, ligne_max - HAUTEUR_RECTANGLE // 2)
        y_max = min(YLIM_SUP, ligne_max + HAUTEUR_RECTANGLE // 2)

        # 4. Définir la largeur du rectangle
        if LARGEUR_RECTANGLE is None:
            largeur_rectangle = img.shape[1]  # Toute la largeur de l'image
            x_min = 0
            x_max = img.shape[1]
        else:
            largeur_rectangle = LARGEUR_RECTANGLE
            x_min = (img.shape[1] - largeur_rectangle) // 2
            x_max = x_min + largeur_rectangle

        # 5. Créer la visualisation
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))

        # Graphique 1: Image originale avec le rectangle
        ax1.imshow(img, cmap='gray')
        ax1.axhline(y=YLIM_INF, color='green', linestyle=':', alpha=0.7, label=f'Ylim inf ({YLIM_INF})')
        ax1.axhline(y=YLIM_SUP, color='green', linestyle=':', alpha=0.7, label=f'Ylim sup ({YLIM_SUP})')
        ax1.axhline(y=ligne_max, color='yellow', linestyle='--', alpha=0.8, linewidth=2,
                    label=f'Surface libre: {ligne_max} px ({hauteur_cm:.4f} cm)')

        # Ajouter un texte indiquant le recalage
        if hauteur_cm != 0:
            signe = "+" if hauteur_cm > 0 else ""
            ax1.text(0.02, 0.98, f'Recalage Y: {signe}{hauteur_cm:.4f} cm',
                     transform=ax1.transAxes, fontsize=12, color='red', weight='bold',
                     bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

        ax1.set_title(f'Surface libre détectée\n{ligne_max} px = {hauteur_cm:.4f} cm')
        ax1.set_xlabel('Pixels')
        ax1.set_ylabel('Pixels')
        ax1.legend()

        # Graphique 2: Profil d'intensité par ligne
        ax2.plot(somme_lignes, range(len(somme_lignes)))
        ax2.axhspan(YLIM_INF, YLIM_SUP, alpha=0.1, color='green', label='Zone de recherche')
        ax2.axhline(y=ligne_max, color='red', linestyle='--', alpha=0.8, label='Ligne max')
        ax2.axhspan(y_min, y_max, alpha=0.2, color='red', label='Zone sélectionnée')
        ax2.set_xlabel('Somme des intensités')
        ax2.set_ylabel('Ligne (y)')
        ax2.set_title('Profil d\'intensité par ligne\n(zone verte = recherche limitée)')
        ax2.legend()
        ax2.invert_yaxis()

        # Graphique 3: Zoom sur le profil autour du maximum
        y_start = max(YLIM_INF, ligne_max - ZOOM_PROFIL)
        y_end = min(YLIM_SUP, ligne_max + ZOOM_PROFIL)

        ax3.plot(somme_lignes[y_start:y_end], range(y_start, y_end))
        ax3.axhline(y=ligne_max, color='red', linestyle='--', alpha=0.8, label='Ligne max')
        ax3.set_xlabel('Somme des intensités')
        ax3.set_ylabel('Pixels')
        ax3.set_title(f'Zoom autour du maximum (ligne {ligne_max})')
        ax3.legend()
        ax3.invert_yaxis()

        plt.tight_layout()

        # --- MODIFICATION ICI : Sauvegarde temporaire pour affichage dans l'interface au lieu de plt.show() ---
        temp_path = "temp_surface_plot.png"
        plt.savefig(temp_path, dpi=100)

        # Afficher les informations détaillées
        print(f"\n=== ZONE D'INTENSITÉ MAXIMALE DÉTECTÉE ===")
        print(f"Recherche limitée à ylim : {YLIM_INF} - {YLIM_SUP}")
        print(f"Ligne avec intensité maximale : {ligne_max} pixels")
        print(f"Hauteur de surface libre : {hauteur_cm:.4f} cm")
        print(f"Recalage appliqué : {'OUI' if hauteur_cm != 0 else 'NON'}")
        print(f"Nouvelle origine Y : {self.transformed_physical_radiale[0][1]:.4f} cm")

       # --------------------------------------------------------------------
        # CORRECTION ICI : ON PRÉPARE ET ON AFFICHE LE GRAPH D'ABORD !
        # ---------------------------------------------------------------------
        if not mod_lot:
            plt.tight_layout()
            print("Affichage du graphique devant l'interface...")
            plt.show(block=True)  # <--- Ouvre la fenêtre et bloque jusqu'à sa fermeture
            plt.pause(1)

            # Demander si l'utilisateur veut sauvegarder ces nouvelles coordonnées
            print(f"\n{'=' * 60}")
            print("SAUVEGARDE DES COORDONNÉES RECALÉES")
            print(f"{'=' * 60}")


            # Remplace le bloc input par :
            reply = QMessageBox.question(None, 'Sauvegarde',
                                         "Voulez-vous sauvegarder les nouvelles coordonnées ?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                try:
                    fichier_sortie, _ = QFileDialog.getSaveFileName(
                        None, "Sauvegarder les résultats de détection",
                        "surface_recalée.txt", "Fichiers Texte (*.txt)"
                    )

                    if fichier_sortie:
                        with open(fichier_sortie, 'w', encoding='utf-8') as f:
                            f.write("# RESULTATS DE DETECTION SURFACE LIBRE\n")
                            f.write(f"# Date : {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                            f.write(f"# Niveau moyen detecte (pixels) : {hauteur_cm:.2f}\n")
                            f.write("# " + "=" * 50 + "\n")
                            f.write("# Index | X (pixel) | Y (pixel)\n")

                            for i, pt in enumerate(self.transformed_pixels_radiale):
                                f.write(f"{i:4d}  {pt[0]:12.2f}  {pt[1]:12.2f}\n")

                            print(f"Fichier sauvegardé avec succès : {fichier_sortie}")
                            return True
                    else:
                        print("Sauvegarde annulée.")
                        return False

                except Exception as e:
                    print(f"Erreur lors de l'écriture du fichier : {e}")
                    return False


        else:

            # MODE LOT : Pas d'interface, on sauvegarde automatiquement
            plt.close(fig)  # Ferme le graphique en arrière-plan

            if self.image_path:

                # 1. Extraire le dossier et le nom du fichier
                dossier = os.path.dirname(self.image_path)
                nom_complet = os.path.basename(self.image_path)  # ex: "photo_1.jpg"
                nom_sans_extension, _ = os.path.splitext(nom_complet)  # "photo_1" et ".jpg"

                # 2. Créer le chemin de sortie (même dossier, extension .csv)
                fichier_sortie = os.path.join(dossier, f"{nom_sans_extension}.csv")

                # 3. Écrire le fichier CSV automatiquement

                try:

                    with open(fichier_sortie, 'w', encoding='utf-8') as f:

                        f.write("# RESULTATS DE DETECTION SURFACE LIBRE\n")

                        f.write(f"# Image source : {nom_complet}\n")

                        f.write(f"# Date : {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

                        f.write(f"# Niveau moyen detecte : {hauteur_cm:.4f} cm\n")

                        f.write("# " + "=" * 50 + "\n")

                        f.write("Index,X_cm,Y_cm\n")  # Format CSV standard avec virgules

                        # On sauvegarde les coordonnées physiques (en cm)

                        for i, pt in enumerate(self.transformed_physical_radiale):
                            f.write(f"{i},{pt[0]:.4f},{pt[1]:.4f}\n")

                    print(f"  -> Sauvegardé : {nom_sans_extension}.csv")

                except Exception as e:

                    print(f"  -> Erreur lors de la sauvegarde de {nom_complet} : {e}")

            else:

                print("  -> Erreur : Chemin de l'image inconnu, sauvegarde impossible.")

        return True









