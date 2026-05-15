# %% TRAITEMENT : ETAPE 1 : Calibration, transformation des images, incertitude

import cv2 # OpenCV pour le traitement d'image
import numpy as np  # NumPy pour les calculs numériques
from itertools import product  # Pour générer des combinaisons
import sys  # Pour les fonctionnalités système
import time  # Pour la gestion du temps
import matplotlib.pyplot as plt  # Pour l'affichage graphique
from tqdm import tqdm  # Pour les barres de progression
import os  # Pour les opérations sur le système de fichiers

# Variables globales pour la sélection polygonale
zone_selection = None  # Stockera les points du polygone
selecting = False
polygon_points = []  # Liste des points du polygone
current_point = (-1, -1)  # Point courant pendant la sélection

# Variables pour la correction de distorsion
points_pixels_origine = None  # Points de l'image originale (zone traitée)
points_cm_origine = None  # Coordonnées physiques (toujours les mêmes)

# Variables pour la correction perspective
transformed_pixels_perspective = None  # Pixels après correction perspective
transformed_physical_perspective = None  # Coordonnées physiques après perspective
H_perspective = None  # Matrice d'homographie pour la transformation perspective
w_perspective, h_perspective = 0, 0  # Dimensions après perspective

# Variables pour la correction radiale
transformed_pixels_radiale = None  # Pixels après correction radiale
transformed_physical_radiale = None  # Coordonnées physiques après radiale
transformed_pixels_radiale_cropped = None  # Pixels après radiale ET rognage
transformed_physical_radiale_cropped = None  # Physique après radiale ET rognage
mtx = None  # Matrice de caméra pour la correction radiale
dist = None  # Coefficients de distorsion pour la correction radiale
w_radiale, h_radiale = 0, 0  # Dimensions après radiale


# ===================================================================
# PHASE DE DETECTION DES COINS DE TOUTE LA MIRE, REORGANISATION, N
# ===================================================================
def imflatfield(I, sigma):
    """Applique un flat-field correction à l'image"""
    A = I.astype(np.float32)
    filterSize = int(2 * np.ceil(2 * sigma) + 1)

    shading = cv2.GaussianBlur(A, (filterSize, filterSize), sigma, borderType=cv2.BORDER_REPLICATE)
    meanVal = np.mean(A)
    shading = np.maximum(shading, 1e-6)
    B = A * meanVal / shading
    B = B - meanVal + 128
    B = np.round(np.clip(B, 0, 255)).astype(np.uint8)

    return B


def select_zone(event, x, y, flags, param):
    """Callback pour la sélection de zone polygonale avec la souris"""
    global selecting, polygon_points, current_point, zone_selection

    if event == cv2.EVENT_LBUTTONDOWN:
        polygon_points.append((x, y))
        selecting = True
        current_point = (x, y)
        print(f"Point ajouté: ({x}, {y}) - Total: {len(polygon_points)} points")

    elif event == cv2.EVENT_MOUSEMOVE:
        if selecting:
            current_point = (x, y)

    elif event == cv2.EVENT_RBUTTONDOWN:
        if len(polygon_points) >= 3:
            selecting = False
            zone_selection = polygon_points.copy()
            print(f"Polygone fermé avec {len(polygon_points)} points")
        else:
            print("Au moins 3 points sont nécessaires pour former un polygone")


def afficher_coins(image, corners, pattern, zone_coords, title="Coins détectés"):
    """Affiche les coins sur l'image avec matplotlib"""
    plt.close('all')

    image_with_corners = image.copy()
    cross_size = 3

    for i, corner in enumerate(corners):
        x, y = int(corner[0][0]), int(corner[0][1])
        cv2.line(image_with_corners, (x - cross_size, y), (x + cross_size, y), (0, 0, 255), 2)
        cv2.line(image_with_corners, (x, y - cross_size), (x, y + cross_size), (0, 0, 255), 2)
        cv2.putText(image_with_corners, str(i + 1), (x + 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

    if zone_coords is not None and len(zone_coords) >= 3:
        pts = np.array(zone_coords, np.int32)
        cv2.polylines(image_with_corners, [pts], True, (0, 255, 0), 2)

    image_rgb = cv2.cvtColor(image_with_corners, cv2.COLOR_BGR2RGB)

    fig = plt.figure(figsize=(15, 10))
    plt.imshow(image_rgb)
    plt.title(f'{title}\nPattern: {pattern}, Coins: {len(corners)}')
    plt.axis('off')
    plt.tight_layout()
    plt.show(block=False)
    plt.pause(0.1)

    return fig


def reorganiser_coins(image, corners, pattern, zone_coords):
    """
    Réorganise les coins selon différentes transformations avec affichage en temps réel
    """
    if corners is None or pattern is None:
        return corners, pattern

    cols, rows = pattern
    total_corners = cols * rows
    original_pattern = pattern
    original_corners = corners.copy()

    # Créer et afficher la figure initiale
    fig = afficher_coins(image, corners, pattern, zone_coords, "Coins initiaux")

    while True:
        print(f"\n{'=' * 50}")
        print("OPTIONS DE RÉORGANISATION DES COINS")
        print(f"{'=' * 50}")
        print("1. Afficher les coins actuels")
        print("2. Transposer (échanger lignes/colonnes)")
        print("3. Inverser l'ordre des lignes")
        print("4. Inverser l'ordre des colonnes")
        print("5. Rotation 90° horaire")
        print("6. Rotation 90° anti-horaire")
        print("7. Rotation 180°")
        print("8. Réinitialiser à l'ordre original")
        print("9. Valider et quitter")
        print("0. Quitter sans valider")

        choix = input("\nVotre choix (0-9): ").strip()

        if choix == '1':
            print(f"\nCoins actuels (pattern: {pattern}):")
            for i in range(min(20, len(corners))):
                print(f"Coin {i + 1:3d}: ({corners[i][0][0]:7.2f}, {corners[i][0][1]:7.2f})")
            if len(corners) > 20:
                print(f"... et {len(corners) - 20} coins supplémentaires")

        elif choix == '2':
            new_pattern = (rows, cols)
            new_corners = np.zeros_like(corners)

            for i in range(rows):
                for j in range(cols):
                    old_idx = i * cols + j
                    new_idx = j * rows + i
                    if old_idx < total_corners and new_idx < total_corners:
                        new_corners[new_idx] = corners[old_idx]

            corners = new_corners
            pattern = new_pattern
            cols, rows = pattern
            print("Transposition effectuée!")
            plt.close(fig)
            fig = afficher_coins(image, corners, pattern, zone_coords, "Après transposition")

        elif choix == '3':
            new_corners = np.zeros_like(corners)

            for i in range(rows):
                for j in range(cols):
                    old_idx = i * cols + j
                    new_idx = (rows - 1 - i) * cols + j
                    if old_idx < total_corners and new_idx < total_corners:
                        new_corners[new_idx] = corners[old_idx]

            corners = new_corners
            print("Inversion des lignes effectuée!")
            plt.close(fig)
            fig = afficher_coins(image, corners, pattern, zone_coords, "Après inversion des lignes")

        elif choix == '4':
            new_corners = np.zeros_like(corners)

            for i in range(rows):
                for j in range(cols):
                    old_idx = i * cols + j
                    new_idx = i * cols + (cols - 1 - j)
                    if old_idx < total_corners and new_idx < total_corners:
                        new_corners[new_idx] = corners[old_idx]

            corners = new_corners
            print("Inversion des colonnes effectuée!")
            plt.close(fig)
            fig = afficher_coins(image, corners, pattern, zone_coords, "Après inversion des colonnes")

        elif choix == '5':
            new_pattern = (rows, cols)
            new_corners = np.zeros_like(corners)

            for i in range(rows):
                for j in range(cols):
                    old_idx = i * cols + j
                    new_idx = j * rows + (rows - 1 - i)
                    if old_idx < total_corners and new_idx < total_corners:
                        new_corners[new_idx] = corners[old_idx]

            corners = new_corners
            pattern = new_pattern
            cols, rows = pattern
            print("Rotation 90° horaire effectuée!")
            plt.close(fig)
            fig = afficher_coins(image, corners, pattern, zone_coords, "Après rotation 90° horaire")

        elif choix == '6':
            new_pattern = (rows, cols)
            new_corners = np.zeros_like(corners)

            for i in range(rows):
                for j in range(cols):
                    old_idx = i * cols + j
                    new_idx = (cols - 1 - j) * rows + i
                    if old_idx < total_corners and new_idx < total_corners:
                        new_corners[new_idx] = corners[old_idx]

            corners = new_corners
            pattern = new_pattern
            cols, rows = pattern
            print("Rotation 90° anti-horaire effectuée!")
            plt.close(fig)
            fig = afficher_coins(image, corners, pattern, zone_coords, "Après rotation 90° anti-horaire")

        elif choix == '7':
            new_corners = np.zeros_like(corners)

            for i in range(rows):
                for j in range(cols):
                    old_idx = i * cols + j
                    new_idx = (rows - 1 - i) * cols + (cols - 1 - j)
                    if old_idx < total_corners and new_idx < total_corners:
                        new_corners[new_idx] = corners[old_idx]

            corners = new_corners
            print("Rotation 180° effectuée!")
            plt.close(fig)
            fig = afficher_coins(image, corners, pattern, zone_coords, "Après rotation 180°")

        elif choix == '8':
            corners = original_corners.copy()
            pattern = original_pattern
            cols, rows = pattern
            print("Réinitialisation effectuée!")
            plt.close(fig)
            fig = afficher_coins(image, corners, pattern, zone_coords, "Après réinitialisation")

        elif choix == '9':
            print("Réorganisation validée!")
            plt.close(fig)
            plt.close('all')
            return corners, pattern

        elif choix == '0':
            print("Annulation de la réorganisation.")
            plt.close(fig)
            plt.close('all')
            return original_corners, original_pattern

        else:
            print("Choix invalide. Veuillez choisir entre 0 et 9.")

    return corners, pattern


def calculer_coordonnees_physiques(corners, pattern_size, spacing_cm=4.0, n_initial=0):
    """
    Calcule les coordonnées physiques des coins avec l'origine décalée
    """
    if len(corners) != pattern_size[0] * pattern_size[1]:
        print(
            f"Attention: {len(corners)} coins détectés mais pattern_size {pattern_size} attend {pattern_size[0] * pattern_size[1]} coins")

    cols, rows = pattern_size
    corners_array = np.array([corner[0] for corner in corners])
    min_x = np.min(corners_array[:, 0])
    max_y = np.max(corners_array[:, 1])

    origine_idx = None
    for i, corner in enumerate(corners):
        x, y = corner[0][0], corner[0][1]
        if abs(x - min_x) < 1e-10 and abs(y - max_y) < 1e-10:
            origine_idx = i
            break

    if origine_idx is None:
        distances = np.sqrt((corners_array[:, 0] - min_x) ** 2 + (corners_array[:, 1] - max_y) ** 2)
        origine_idx = np.argmin(distances)

    origine_x, origine_y = corners[origine_idx][0][0], corners[origine_idx][0][1]
    print(f"Coin origine (inférieur gauche): Coin {origine_idx + 1} à ({origine_x:.2f}, {origine_y:.2f}) pixels")

    N = 4 * n_initial
    decalage_origine = 1173.8 + N

    print(
        f"Décalage de l'origine appliqué: {decalage_origine:.3f} cm (distance de la Premiere ligne verticale de la mire au batteur [cm] + {N:.3f})")
    print(f"Valeur de n utilisée: {n_initial}")

    physical_coords = []

    for i, corner in enumerate(corners):
        row = i // cols
        col = i % cols
        origine_row = origine_idx // cols
        origine_col = origine_idx % cols

        delta_col = col - origine_col
        delta_row = origine_row - row

        x_cm = delta_col * spacing_cm
        y_cm = delta_row * spacing_cm

        x_cm_decalé = x_cm + decalage_origine
        y_cm_decalé = y_cm

        physical_coords.append((x_cm_decalé, y_cm_decalé))

    print(f"Nouvelle origine (0,0) positionnée à: ({decalage_origine:.3f}, 0.000) cm")

    return physical_coords


def afficher_coordonnees_finales(corners, physical_coords, pattern):
    """
    Affiche les coordonnées pixels et physiques dans un tableau formaté
    """
    print(f"\n{'=' * 120}")
    print("COORDONNÉES FINALES DES COINS - PIXELS ET PHYSIQUES")
    print(f"{'=' * 120}")
    print(
        f"{'No':<4} {'Col':<3} {'Lig':<3} {'X (pixels)':<12} {'Y (pixels)':<12} {'X (cm)':<10} {'Y (cm)':<10} {'Distance (cm)':<12}")
    print(f"{'-' * 120}")

    cols, rows = pattern

    for i, (corner, phys_coord) in enumerate(zip(corners, physical_coords)):
        x_pixel, y_pixel = corner[0][0], corner[0][1]
        x_cm, y_cm = phys_coord
        distance = np.sqrt(x_cm ** 2 + y_cm ** 2)

        col = i % cols + 1
        row = i // cols + 1

        print(
            f"{i + 1:<4} {col:<3} {row:<3} {x_pixel:<12.2f} {y_pixel:<12.2f} {x_cm:<10.2f} {y_cm:<10.2f} {distance:<12.2f}")

    print(f"{'=' * 120}")


def sauvegarder_coordonnees(points_pixels, points_cm, pattern, n_initial, image_path, fichier_sortie=None):
    """
    Sauvegarde les coordonnées pixels et cm dans un fichier texte
    """
    if fichier_sortie is None:
        dossier = os.path.dirname(image_path)
        nom_base = os.path.splitext(os.path.basename(image_path))[0]
        fichier_sortie = os.path.join(dossier, f"{nom_base}_coordonnees.txt")

    with open(fichier_sortie, 'w', encoding='utf-8') as f:
        f.write("# FICHIER DE COORDONNÉES DE CALIBRATION\n")
        f.write("# " + "=" * 60 + "\n")
        f.write(f"# Fichier source: {image_path}\n")
        f.write(f"# Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Pattern du damier: {pattern[0]} colonnes x {pattern[1]} lignes\n")
        f.write(f"# Nombre de points: {len(points_pixels)}\n")
        f.write(f"# n initial (décalage origine X): {n_initial}\n")
        f.write("# " + "=" * 60 + "\n")
        f.write("# Format: index, x_pixel, y_pixel, x_cm, y_cm\n")
        f.write("# " + "-" * 60 + "\n")

        for i, (pixel, cm) in enumerate(zip(points_pixels, points_cm)):
            f.write(f"{i + 1:4d}  {pixel[0]:12.4f}  {pixel[1]:12.4f}  {cm[0]:12.4f}  {cm[1]:12.4f}\n")

    print(f"Coordonnées sauvegardées dans: {fichier_sortie}")
    return fichier_sortie


def charger_coordonnees(fichier_coords):
    """
    Charge les coordonnées pixels et cm depuis un fichier texte
    Retourne: (points_pixels, points_cm, pattern, n_initial)
    """
    points_pixels = []
    points_cm = []
    pattern = None
    n_initial = 0

    try:
        with open(fichier_coords, 'r', encoding='utf-8') as f:
            lignes = f.readlines()

        for ligne in lignes:
            ligne = ligne.strip()

            if ligne.startswith('#') or not ligne:
                if 'Pattern du damier:' in ligne:
                    try:
                        pattern_str = ligne.split('Pattern du damier:')[1].strip()
                        pattern = tuple(map(int, pattern_str.replace('colonnes', '').replace('lignes', '').split('x')))
                    except:
                        pass
                elif 'n initial' in ligne:
                    try:
                        n_initial = float(ligne.split(':')[1].strip())
                    except:
                        pass
                continue

            parties = ligne.split()
            if len(parties) >= 5:
                try:
                    i = int(parties[0])
                    x_pix = float(parties[1])
                    y_pix = float(parties[2])
                    x_cm = float(parties[3])
                    y_cm = float(parties[4])

                    points_pixels.append((x_pix, y_pix))
                    points_cm.append((x_cm, y_cm))
                except ValueError:
                    continue

        if len(points_pixels) == 0:
            print("Aucune coordonnée valide trouvée dans le fichier")
            return None, None, None, None

        print(f"Coordonnées chargées depuis: {fichier_coords}")
        print(f"   • {len(points_pixels)} points chargés")
        if pattern:
            print(f"   • Pattern: {pattern[0]}x{pattern[1]}")
        print(f"   • n initial: {n_initial}")

        return points_pixels, points_cm, pattern, n_initial

    except FileNotFoundError:
        print(f"Fichier non trouvé: {fichier_coords}")
        return None, None, None, None
    except Exception as e:
        print(f"Erreur lors du chargement: {e}")
        return None, None, None, None


def demander_charger_coordonnees(image_path):
    """
    Demande à l'utilisateur s'il veut charger des coordonnées existantes
    """
    print(f"\n{'=' * 60}")
    print("CHARGEMENT DE COORDONNÉES EXISTANTES")
    print(f"{'=' * 60}")

    while True:
        reponse = input("Voulez-vous charger un fichier de coordonnées existant? (oui/o/y ou non/n): ").strip().lower()

        if reponse in ['oui', 'o', 'y', 'yes']:
            dossier = os.path.dirname(image_path)
            nom_base = os.path.splitext(os.path.basename(image_path))[0]
            chemin = os.path.join(dossier, f"{nom_base}_coordonnees.txt")

            print(f"Recherche du fichier: {chemin}")
            if os.path.exists(chemin):
                points_pixels, points_cm, pattern, n_initial = charger_coordonnees(chemin)
                if points_pixels is not None:
                    return points_pixels, points_cm, pattern, n_initial
                else:
                    print("Erreur lors du chargement. Voulez-vous réessayer?")
            else:
                print(f"Fichier non trouvé: {chemin}")
                print("Veuillez vérifier le chemin et réessayer.")

        elif reponse in ['non', 'n', 'no']:
            print("Lancement de la détection des coins...")
            return None, None, None, None
        else:
            print("Réponse invalide. Veuillez répondre par 'oui' (o/y) ou 'non' (n).")


def detecter_coins_dans_zone(image_path, max_size=24):
    """
    Permet de sélectionner une zone polygonale puis détecte les coins dans cette zone
    """
    global zone_selection, polygon_points, selecting, current_point, points_pixels_origine, points_cm_origine

    zone_selection = None
    polygon_points = []
    selecting = False
    current_point = (-1, -1)

    image = cv2.imread(image_path)
    if image is None:
        print("Erreur: Impossible de charger l'image")
        return None, None, [], None, None, None, None

    print("Application du traitement imflatfield sur TOUTE l'image (sigma=200)...")
    image_traitee = imflatfield(image, sigma=200)

    # Mode manuel - sélection avec la souris SUR L'IMAGE TRAITÉE
    print("Mode de sélection manuelle activé.")
    clone = image_traitee.copy()
    cv2.namedWindow('Selectionnez une zone du damier (Image traitée avec imflatfield)')
    cv2.setMouseCallback('Selectionnez une zone du damier (Image traitée avec imflatfield)', select_zone)

    print("Instructions:")
    print("On considère un damier d'un nombre N de carré")
    print("1. Clic gauche: ajouter un point au polygone")
    print("2. Clic droit: fermer le polygone (au moins 3 points)")
    print("3. Appuyez sur 'Entrée' pour valider la sélection")
    print("4. Appuyez sur 'r' pour recommencer")
    print("5. Appuyez sur 'q' pour quitter")
    print("NOTE: Vous travaillez sur l'image traitée avec imflatfield")

    while True:
        temp_image = clone.copy()

        if len(polygon_points) > 0:
            for point in polygon_points:
                cv2.circle(temp_image, point, 5, (0, 255, 0), -1)

            if len(polygon_points) > 1:
                for i in range(len(polygon_points) - 1):
                    cv2.line(temp_image, polygon_points[i], polygon_points[i + 1], (0, 255, 0), 2)

            if selecting and current_point != (-1, -1):
                cv2.line(temp_image, polygon_points[-1], current_point, (0, 255, 255), 2)
                cv2.circle(temp_image, current_point, 5, (0, 255, 255), -1)

            if zone_selection is not None and len(zone_selection) >= 3:
                pts = np.array(zone_selection, np.int32)
                overlay = temp_image.copy()
                cv2.fillPoly(overlay, [pts], (0, 255, 0))
                cv2.addWeighted(overlay, 0.2, temp_image, 0.8, 0, temp_image)
                cv2.polylines(temp_image, [pts], True, (0, 255, 0), 2)

        cv2.putText(temp_image, "Clic gauche: ajouter point", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(temp_image, "Clic droit: fermer le polygone", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(temp_image, "'r': recommencer, 'q': quitter", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(temp_image, "Image traitee avec imflatfield", (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        if zone_selection is not None:
            cv2.putText(temp_image, "Appuyez sur Entree pour valider",
                        (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow('Selectionnez une zone du damier (Image traitée avec imflatfield)', temp_image)
        key = cv2.waitKey(1) & 0xFF

        if key == 13:
            if zone_selection is not None and len(zone_selection) >= 3:
                cv2.destroyAllWindows()
                break
            else:
                print("Veuillez d'abord sélectionner un polygone valide (au moins 3 points)")

        elif key == ord('r'):
            zone_selection = None
            polygon_points = []
            selecting = False
            current_point = (-1, -1)
            clone = image_traitee.copy()
            print("Sélection réinitialisée")

        elif key == ord('q'):
            cv2.destroyAllWindows()
            return None, None, [], None, None, None, None

    if zone_selection is not None and len(zone_selection) >= 3:
        mask = np.zeros(image_traitee.shape[:2], dtype=np.uint8)
        pts = np.array(zone_selection, np.int32)
        cv2.fillPoly(mask, [pts], 255)

        masked_image = cv2.bitwise_and(image_traitee, image_traitee, mask=mask)

        x, y, w_bbox, h_bbox = cv2.boundingRect(pts)
        zone = masked_image[y:y + h_bbox, x:x + w_bbox]

        if zone.size == 0:
            print("Erreur: la zone est invalide")
            return None, None, [], None, None, None, None

        bbox_coords = (x, y, x + w_bbox, y + h_bbox)

        print(f"Zone extraite pour détection des coins")
        print(f"   Dimensions de la zone: {zone.shape[1]} x {zone.shape[0]} pixels")
    else:
        print("Erreur: Aucune zone valide sélectionnée")
        return None, None, [], None, None, None, None

    gray_zone = cv2.cvtColor(zone, cv2.COLOR_BGR2GRAY)

    sizes = []
    for cols in range(max_size, 2, -1):
        for rows in range(max_size, 2, -1):
            if cols * rows >= 9:
                sizes.append((cols, rows))

    best_corners = None
    best_pattern = None
    max_corners = 0
    successful_patterns = []

    print(f"Test de {len(sizes)} combinaisons de pattern_size sur la zone traitée...")

    for pattern_size in tqdm(sizes, desc="Recherche des patterns", unit="pattern"):
        ret, corners = cv2.findChessboardCorners(gray_zone, pattern_size,
                                                 cv2.CALIB_CB_ADAPTIVE_THRESH +
                                                 cv2.CALIB_CB_NORMALIZE_IMAGE +
                                                 cv2.CALIB_CB_FAST_CHECK)

        if ret:
            num_corners = corners.shape[0]
            successful_patterns.append((pattern_size, num_corners))

            if num_corners > max_corners:
                max_corners = num_corners
                best_corners = corners
                best_pattern = pattern_size

                if num_corners == pattern_size[0] * pattern_size[1]:
                    print(f"\nPattern optimal trouvé: {pattern_size}")
                    break

    print(f"\n{'=' * 50}")
    print("RÉSULTATS DE LA DÉTECTION DANS LA ZONE")
    print(f"{'=' * 50}")

    if best_corners is not None:
        successful_patterns.sort(key=lambda x: x[1], reverse=True)

        print(f"Meilleure détection: pattern {best_pattern}")
        print(f"Nombre de coins détectés: {max_corners}")

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.0001)
        corners_refined = cv2.cornerSubPix(gray_zone, best_corners, (11, 11), (-1, -1), criteria)

        corners_original = corners_refined.copy()
        for i, corner in enumerate(corners_original):
            corner[0][0] += x
            corner[0][1] += y

        original_pattern = best_pattern

        corners_final, pattern_final = reorganiser_coins(image, corners_original, best_pattern, zone_selection)

        print(f"\n{'=' * 50}")
        print("DÉCALAGE DE L'ORIGINE")
        print(f"{'=' * 50}")
        print(
            "L'origine (0,0) sera positionnée à (distance de la Premiere ligne verticale de la mire au batteur [cm] + 4 [cm] *n, 0)")

        while True:
            try:
                n_input = input("Entrez la valeur de n pour le décalage (appuyez sur Entrée pour n=0): ").strip()
                if n_input == "":
                    n_initial = 0
                    break
                n_initial = float(n_input)
                break
            except ValueError:
                print("Valeur invalide. Veuillez entrer un nombre.")

        print(f"Valeur de n utilisée: {n_initial}")

        physical_coords = calculer_coordonnees_physiques(corners_final, pattern_final, n_initial=n_initial)
        plt.close('all')

        points_pixels_origine = [(float(corner[0][0]), float(corner[0][1])) for corner in corners_final]
        points_cm_origine = [(float(x_cm), float(y_cm)) for x_cm, y_cm in physical_coords]

        afficher_coordonnees_finales(corners_final, physical_coords, pattern_final)

        image_final = image.copy()

        cross_size = 3

        for i, corner in enumerate(corners_final):
            x_pt, y_pt = int(corner[0][0]), int(corner[0][1])

            cv2.line(image_final, (x_pt - cross_size, y_pt), (x_pt + cross_size, y_pt), (0, 0, 255), 2)
            cv2.line(image_final, (x_pt, y_pt - cross_size), (x_pt, y_pt + cross_size), (0, 0, 255), 2)

            cv2.putText(image_final, f"{i + 1}", (x_pt + 10, y_pt - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        if zone_selection is not None and len(zone_selection) >= 3:
            pts = np.array(zone_selection, np.int32)
            cv2.polylines(image_final, [pts], True, (0, 255, 0), 2)

        if corners_final is not None:
            print(f"\n{'=' * 60}")
            print("SAUVEGARDE DES COORDONNÉES")
            print(f"{'=' * 60}")

            while True:
                reponse = input(
                    "Voulez-vous sauvegarder ces coordonnées dans un fichier? (oui/o/y ou non/n): ").strip().lower()

                if reponse in ['oui', 'o', 'y', 'yes']:
                    dossier = os.path.dirname(image_path)
                    nom_base = os.path.splitext(os.path.basename(image_path))[0]
                    defaut = os.path.join(dossier, f"{nom_base}_coordonnees.txt")

                    print(f"Nom de fichier par défaut: {defaut}")
                    reponse_fichier = input(
                        "Appuyez sur Entrée pour utiliser ce nom, ou entrez un autre chemin: ").strip()

                    if reponse_fichier == "":
                        fichier = defaut
                    else:
                        fichier = reponse_fichier

                    sauvegarder_coordonnees(points_pixels_origine, points_cm_origine, pattern_final, n_initial,
                                            image_path, fichier)
                    break
                elif reponse in ['non', 'n', 'no']:
                    print("Sauvegarde ignorée.")
                    break
                else:
                    print("Réponse invalide. Veuillez répondre par 'oui' (o/y) ou 'non' (n).")

        return corners_final, pattern_final, successful_patterns, zone_selection, physical_coords, points_pixels_origine, points_cm_origine
    else:
        print("Aucun damier détecté dans la zone sélectionnée.")
        return None, None, [], zone_selection, None, None, None


def charger_ou_detecter_coins(image_path):
    """
    Fonction principale pour charger ou détecter les coins de la mire
    """
    global points_pixels_origine, points_cm_origine

    points_pixels_origine, points_cm_origine, pattern, n_initial = demander_charger_coordonnees(image_path)

    if points_pixels_origine is None:

        result = detecter_coins_dans_zone(image_path, max_size=24)

        if result is not None and result[0] is not None:
            coins, pattern, all_results, zone_coords, physical_coords, points_pixels_origine, points_cm_origine = result
        else:
            print("Aucun damier n'a été détecté.")
            sys.exit(1)
    else:
        print(f"Coordonnées chargées avec succès!")
        print(f"   {len(points_pixels_origine)} points disponibles")

        # Récupération des variables pour le reste du programme
        zone_coords = None
        pattern = pattern
        n_initial = n_initial

    return points_pixels_origine, points_cm_origine, pattern, n_initial, zone_coords


def afficher_points_sur_image(image_path, points_pixels_origine, pattern, zone_coords):
    """
    Affiche les points sur l'image originale et propose de sauvegarder
    """
    img = cv2.imread(image_path)
    if img is None:
        print("Impossible de charger l'image")
        return img

    print(f"\n{'=' * 60}")
    print("IMAGE ORIGINALE AVEC POINTS")
    print(f"{'=' * 60}")

    img_avec_points = img.copy()

    for i, (x, y) in enumerate(points_pixels_origine):
        x_int, y_int = int(x), int(y)
        cv2.line(img_avec_points, (x_int - 5, y_int), (x_int + 5, y_int), (0, 0, 255), 2)
        cv2.line(img_avec_points, (x_int, y_int - 5), (x_int, y_int + 5), (0, 0, 255), 2)
        cv2.putText(img_avec_points, str(i + 1), (x_int + 10, y_int - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    if zone_coords is not None and len(zone_coords) >= 3:
        pts = np.array(zone_coords, np.int32)
        cv2.polylines(img_avec_points, [pts], True, (0, 255, 0), 2)

    plt.figure(figsize=(15, 10))
    plt.imshow(cv2.cvtColor(img_avec_points, cv2.COLOR_BGR2RGB))
    pattern_text = f" - Pattern {pattern}" if pattern else ""
    plt.title(f'IMAGE ORIGINALE AVEC POINTS DÉTECTÉS\n{len(points_pixels_origine)} points{pattern_text}')
    plt.axis('off')
    plt.tight_layout()
    plt.show(block=False)
    plt.pause(2)
    """
    reponse = input("\nVoulez-vous sauvegarder cette image? (o/n): ").strip().lower()
    if reponse in ['o', 'oui', 'y', 'yes']:
        dossier = os.path.dirname(image_path)
        img_points_path = os.path.join(dossier, 'Image_originale_avec_points.png')
        plt.savefig(img_points_path, dpi=300, bbox_inches='tight')
        print(f"Image sauvegardée: {img_points_path}")
    """
    plt.close()

    return img


# ========================================================================================
# FENETRAGE, MODIFICATION ORIGINE Y CM, MODIFICATION REFERENTIEL PX, SAVE FENETRAGE .TIF
# ========================================================================================

def reinitialiser_origine_y_points_cm(points_pixels_origine, points_cm_origine, indices_dans_zone):
    """
    Réinitialise l'origine Y des points cm pour que Y=0 soit au point de la première colonne
    et dernière ligne de la zone rognée

    Args:
        points_pixels_origine: Liste des points pixels (déjà ajustés)
        points_cm_origine: Liste des points cm (sera modifiée)
        indices_dans_zone: Liste des indices des points dans la zone

    Returns:
        idx_ref: Index du point de référence (première colonne, dernière ligne)
        y_offset: Valeur du décalage appliqué
    """
    print(f"\n{'=' * 60}")
    print("RÉINITIALISATION DE L'ORIGINE Y DES POINTS CM")
    print(f"{'=' * 60}")
    print("   Objectif: Y=0 à partir du point sur la première colonne et dernière ligne de la zone")

    idx_ref = None
    y_offset = 0

    if len(indices_dans_zone) == 0:
        print("Aucun point dans la zone rognée. Impossible de réinitialiser Y.")
        return idx_ref, y_offset

    # Étape 1: Trouver les points sur la dernière ligne de la zone
    y_max_zone = max(points_pixels_origine[i][1] for i in indices_dans_zone)
    print(f"\n--- Étape 1: Identification de la dernière ligne ---")
    print(f"   Y maximum dans la zone: {y_max_zone:.2f} pixels")

    tolerance_y = 5.0
    points_derniere_ligne = []

    for i in indices_dans_zone:
        x, y = points_pixels_origine[i]
        if abs(y - y_max_zone) <= tolerance_y:
            points_derniere_ligne.append((i, x, y))

    print(f"   Points sur la dernière ligne: {len(points_derniere_ligne)}")

    if len(points_derniere_ligne) == 0:
        print("Impossible d'identifier la dernière ligne")
        return idx_ref, y_offset

    # Étape 2: Parmi ces points, trouver celui avec le X minimum (première colonne)
    points_derniere_ligne.sort(key=lambda p: p[1])  # Trier par X croissant
    idx_ref, x_ref, y_ref = points_derniere_ligne[0]

    print(f"\n--- Étape 2: Point de référence (première colonne, dernière ligne) ---")
    print(f"   Index: {idx_ref + 1}")
    print(f"   Coordonnées pixels ajustées: ({x_ref:.2f}, {y_ref:.2f})")
    print(f"   Y physique avant recalibrage: {points_cm_origine[idx_ref][1]:.3f} cm")

    # Valeur Y actuelle du point de référence
    y_ref_cm = points_cm_origine[idx_ref][1]
    y_offset = y_ref_cm

    print(f"\n--- Étape 3: Application du décalage Y ---")
    print(f"   Décalage à appliquer: {y_offset:.3f} cm (pour ramener ce point à Y=0)")

    # Appliquer le décalage à TOUS les points cm
    for i in range(len(points_cm_origine)):
        x_cm, y_cm = points_cm_origine[i]
        points_cm_origine[i] = (x_cm, y_cm - y_offset)

    print(f"Décalage Y de {y_offset:.3f} cm appliqué aux {len(points_cm_origine)} points")
    print(f"Origine Y réinitialisée avec succès!")
    print(f"Le point de référence (index {idx_ref + 1}) est maintenant à Y = 0.000 cm")

    # Afficher TOUS les points (dans zone et hors zone)
    print(f"\n{'=' * 80}")
    print("TOUS LES POINTS APRÈS RÉINITIALISATION Y")
    print(f"{'=' * 80}")
    print(f"{'No':<6} {'X (px)':<12} {'Y (px)':<12} {'X (cm)':<12} {'Y (cm)':<12} {'Statut':<10} {'Dans zone?'}")
    print(f"{'-' * 80}")

    for i in range(len(points_pixels_origine)):
        px, py = points_pixels_origine[i]
        cm_x, cm_y = points_cm_origine[i]
        statut = "✓" if i in indices_dans_zone else "✗"
        dans_zone = "OUI" if i in indices_dans_zone else "NON"
        print(f"{i + 1:<6} {px:<12.2f} {py:<12.2f} {cm_x:<12.3f} {cm_y:<12.3f} {statut:<10} {dans_zone}")

    print(f"{'=' * 80}")
    print(f"Total points: {len(points_pixels_origine)}")
    print(f"Points dans zone: {len(indices_dans_zone)}")
    print(f"Points hors zone: {len(indices_hors_zone)}")

    return idx_ref, y_offset


def ajuster_points_referentiel_rognage(points_pixels_origine, left_adj, top_adj, width_adj, height_adj):
    """
    Ajuste les coordonnées des points pixels dans le référentiel de la zone rognée

    Args:
        points_pixels_origine: Liste des points pixels (sera modifiée)
        left_adj, top_adj: Coordonnées du coin supérieur gauche de la zone rognée
        width_adj, height_adj: Dimensions de la zone rognée

    Returns:
        indices_dans_zone: Liste des indices des points dans la zone
        indices_hors_zone: Liste des indices des points hors zone
        anciens_pixels: Copie des anciennes coordonnées pour référence
    """
    print(f"\n{'=' * 60}")
    print("AJUSTEMENT DES POINTS PIXELS DANS LE RÉFÉRENTIEL DE LA ZONE ROGNÉE")
    print(f"{'=' * 60}")

    # Sauvegarde des anciennes coordonnées pour référence
    anciens_pixels = points_pixels_origine.copy()

    # Ajustement: soustraire left et top pour obtenir les coordonnées dans la zone rognée
    for i in range(len(points_pixels_origine)):
        x, y = points_pixels_origine[i]
        points_pixels_origine[i] = (x - left_adj, y - top_adj)

    print(f"Ajustement effectué pour {len(points_pixels_origine)} points")
    print(f"   Nouveau référentiel: origine à ({left_adj}, {top_adj}) dans l'image originale")

    # Identifier les points dans la zone après ajustement
    indices_dans_zone = []
    indices_hors_zone = []

    for i, (x, y) in enumerate(points_pixels_origine):
        if 0 <= x <= width_adj and 0 <= y <= height_adj:
            indices_dans_zone.append(i)
        else:
            indices_hors_zone.append(i)

    print(f"RÉSULTATS DE L'AJUSTEMENT:")
    print(f"   • Points DANS la zone rognée: {len(indices_dans_zone)}")
    print(f"   • Points HORS de la zone rognée: {len(indices_hors_zone)}")

    print(f"\nEXEMPLE DE TRANSFORMATION (5 premiers points):")
    print(f"{'No':<6} {'X (original)':<14} {'Y (original)':<14} {'X (ajusté)':<14} {'Y (ajusté)':<14}")
    print(f"{'-' * 65}")
    for i in range(min(5, len(anciens_pixels))):
        x_orig, y_orig = anciens_pixels[i]
        x_ajust, y_ajust = points_pixels_origine[i]
        print(f"{i + 1:<6} {x_orig:<14.2f} {y_orig:<14.2f} {x_ajust:<14.2f} {y_ajust:<14.2f}")

    return indices_dans_zone, indices_hors_zone, anciens_pixels


def extraire_zone_rognage(img, left, top, width, height, image_path=None, suffixe="_rogee"):
    """
    Extrait la zone rognée de l'image originale et la sauvegarde en .tif

    Args:
        img: Image originale
        left, top, width, height: Coordonnées de rognage
        image_path: Chemin de l'image originale (pour générer le nom de sauvegarde)
        suffixe: Suffixe à ajouter au nom du fichier

    Returns:
        zone_rogee: Image rognée
        left, top, width, height: Coordonnées ajustées
        output_path: Chemin du fichier sauvegardé (ou None si non sauvegardé)
    """
    print(f"\n{'=' * 60}")
    print("EXTRACTION DE LA ZONE ROGNÉE")
    print(f"{'=' * 60}")

    h, w = img.shape[:2]

    if left < 0 or top < 0 or left + width > w or top + height > h:
        print(f"⚠️  Attention: La zone de rognage dépasse les limites de l'image")
        print(f"   Image: {w}x{h}, Zone: ({left},{top}) à ({left + width},{top + height})")

        left = max(0, left)
        top = max(0, top)
        right = min(w, left + width)
        bottom = min(h, top + height)
        width = right - left
        height = bottom - top

        print(f"   Zone ajustée: ({left},{top}) à ({left + width},{top + height})")

    # Extraction de la zone rognée
    zone_rogee = img[top:top + height, left:left + width].copy()

    print(f"Zone rognée extraite: {width} x {height} pixels")

    # Sauvegarde en .tif si un chemin d'image est fourni
    output_path = None
    if image_path is not None:
        dossier = os.path.dirname(image_path)
        nom_base = os.path.splitext(os.path.basename(image_path))[0]
        output_path = os.path.join(dossier, f"{nom_base}{suffixe}.tif")

        cv2.imwrite(output_path, zone_rogee)
        print(f"Image rognée sauvegardée: {output_path}")
        print(f"   • Dimensions: {width} x {height} pixels")
        print(f"   • Zone: ({left}, {top}) à ({left + width}, {top + height})")

    return zone_rogee, left, top, width, height, output_path


def demander_coordonnees_rognage():
    """
    Demande à l'utilisateur les coordonnées de rognage
    """
    print(f"\n{'=' * 60}")
    print("ROGNAGE FINAL DES POINTS DE CALIBRATION")
    print(f"{'=' * 60}")
    print("Veuillez entrer les coordonnées de rognage:")
    print("Format: left top width height")
    print("Exemple: '100 50 800 600' pour rogner à partir de (100,50) avec largeur 800 et hauteur 600")

    while True:
        try:
            coords_input = input("\nEntrez left top width height (ou 'q' pour annuler): ").strip()

            if coords_input.lower() == 'q':
                print("Rognage annulé.")
                return None, None, None, None

            coords = list(map(int, coords_input.split()))

            if len(coords) != 4:
                print("Format invalide. Veuillez entrer 4 nombres: left top width height")
                continue

            left, top, width, height = coords

            if left < 0 or top < 0:
                print("left et top ne peuvent pas être négatifs")
                continue

            if width <= 0 or height <= 0:
                print("width et height doivent être positifs")
                continue

            print(f"Coordonnées de rognage validées:")
            print(f"   Left: {left}")
            print(f"   Top: {top}")
            print(f"   Width: {width}")
            print(f"   Height: {height}")
            print(f"   Zone: rectangle de ({left}, {top}) à ({left + width}, {top + height})")

            return left, top, width, height

        except ValueError:
            print("Format invalide. Veuillez entrer des nombres entiers.")
        except Exception as e:
            print(f"Erreur: {e}")


"""
def afficher_resultats_fenetrage(zone_rogee, points_pixels, left, top, width, height, 
                                 idx_ref, image_path):

    fig, ax = plt.subplots(figsize=(12, 8))

    # Charger l'image si c'est un chemin, sinon utiliser directement
    if isinstance(zone_rogee, str):
        img = cv2.imread(zone_rogee)
        if img is None:
            raise ValueError(f"Impossible de charger l'image: {zone_rogee}")
        zone_rogee = img

    # Afficher l'image
    ax.imshow(cv2.cvtColor(zone_rogee, cv2.COLOR_BGR2RGB))

    # Dessiner le rectangle de la zone de rognage (optionnel, pour visualisation)
    rect = plt.Rectangle((left, top), width, height, 
                         fill=False, edgecolor='green', linewidth=2, linestyle='--')
    ax.add_patch(rect)

    # Séparer les points selon leur appartenance à la zone
    points_dans_zone = []
    points_hors_zone = []

    for i, (x, y) in enumerate(points_pixels):
        if left <= x <= left + width and top <= y <= top + height:
            points_dans_zone.append((i, x, y))
        else:
            points_hors_zone.append((i, x, y))

    # Points dans la zone (rouge)
    if points_dans_zone:
        x_dans = [p[1] for p in points_dans_zone]
        y_dans = [p[2] for p in points_dans_zone]
        ax.scatter(x_dans, y_dans, c='red', s=30, 
                  label=f'Dans zone ({len(points_dans_zone)})')

    # Points hors zone (bleu)
    if points_hors_zone:
        x_hors = [p[1] for p in points_hors_zone]
        y_hors = [p[2] for p in points_hors_zone]
        ax.scatter(x_hors, y_hors, c='blue', s=20, alpha=0.5, 
                  label=f'Hors zone ({len(points_hors_zone)})')

    # Point origine (jaune)
    if idx_ref is not None and idx_ref < len(points_pixels):
        ax.scatter([points_pixels[idx_ref][0]], [points_pixels[idx_ref][1]], 
                  c='yellow', s=200, marker='*', label='Origine Y=0')

    # Titre
    titre = f'Points de calibration - {os.path.basename(image_path)}'
    ax.set_title(titre)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    return fig
"""


def afficher_resultats_fenetrage(zone_rogee, points_pixels, points_cm, left, top, width, height,
                                 idx_ref, image_path, titre_etape):
    """
    Affiche les résultats du fenêtrage avec les points de calibration colorés selon
    leur appartenance à la zone de rognage ET une heatmap des erreurs de recalage

    Args:
        zone_rogee: Image rognée ou chemin vers l'image
        points_pixels: Points PIXELS DANS LE RÉFÉRENTIEL DE L'IMAGE AFFICHÉE
        points_cm: Points physiques correspondants (pour le calcul de l'homographie)
        left, top, width, height: Coordonnées de la zone de rognage (dans le référentiel actuel)
        idx_ref: Index du point de référence
        image_path: Chemin de l'image pour le titre
        titre_etape: "ORIGINALE", "PERSPECTIVE" ou "RADIALE" pour le titre
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))

    # ======================================================================
    # PREMIER GRAPHIQUE : IMAGE AVEC POINTS
    # ======================================================================

    # Charger l'image si c'est un chemin, sinon utiliser directement
    if isinstance(zone_rogee, str):
        img = cv2.imread(zone_rogee)
        if img is None:
            raise ValueError(f"Impossible de charger l'image: {zone_rogee}")
        zone_rogee = img

    # Afficher l'image
    ax1.imshow(cv2.cvtColor(zone_rogee, cv2.COLOR_BGR2RGB))

    # Dessiner le rectangle de la zone de rognage
    rect = plt.Rectangle((left, top), width, height,
                         fill=False, edgecolor='green', linewidth=2, linestyle='--')
    ax1.add_patch(rect)

    # Séparer les points selon leur appartenance à la zone
    points_dans_zone = []
    points_hors_zone = []
    indices_dans_zone = []

    for i, (x, y) in enumerate(points_pixels):
        if left <= x <= left + width and top <= y <= top + height:
            points_dans_zone.append((i, x, y))
            indices_dans_zone.append(i)
        else:
            points_hors_zone.append((i, x, y))

    # Points dans la zone (rouge)
    if points_dans_zone:
        x_dans = [p[1] for p in points_dans_zone]
        y_dans = [p[2] for p in points_dans_zone]
        ax1.scatter(x_dans, y_dans, c='red', s=30,
                    label=f'Dans zone ({len(points_dans_zone)})')

    # Points hors zone (bleu)
    if points_hors_zone:
        x_hors = [p[1] for p in points_hors_zone]
        y_hors = [p[2] for p in points_hors_zone]
        ax1.scatter(x_hors, y_hors, c='blue', s=20, alpha=0.5,
                    label=f'Hors zone ({len(points_hors_zone)})')

    # Point origine (jaune)
    if idx_ref is not None and idx_ref < len(points_pixels):
        ax1.scatter([points_pixels[idx_ref][0]], [points_pixels[idx_ref][1]],
                    c='yellow', s=200, marker='*', label='Origine Y=0')

    ax1.set_title(f'Points de calibration - {os.path.basename(image_path)}')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # ======================================================================
    # DEUXIÈME GRAPHIQUE : HEATMAP DES ERREURS DE RECALAGE (style comparatif)
    # ======================================================================

    print(f"\n{'=' * 60}")
    print(f"CALCUL DE LA HEATMAP - {titre_etape}")
    print(f"{'=' * 60}")

    # Utiliser TOUS les points pour calculer l'homographie
    if len(points_pixels) >= 4:
        # Conversion en tableaux numpy
        src_pts = np.array(points_pixels, dtype=np.float32)
        dst_pts = np.array(points_cm, dtype=np.float32)

        print(f"Calcul de l'homographie avec TOUS les points ({len(src_pts)} points)...")

        # Calcul de l'homographie (transformation pixels -> cm)
        H_pixels_to_cm, status = cv2.findHomography(src_pts, dst_pts, method=cv2.LMEDS)

        if H_pixels_to_cm is not None:
            print(f"Homographie calculée avec succès")

            # AFFICHAGE DE LA MATRICE D'HOMOGRAPHIE
            print(f"\nMatrice d'homographie H (pixels -> cm) - {titre_etape}:")
            np.set_printoptions(precision=10, suppress=True)
            for i in range(3):
                print(f"  [{H_pixels_to_cm[i][0]:15.10f} {H_pixels_to_cm[i][1]:15.10f} {H_pixels_to_cm[i][2]:15.10f}]")

            if len(indices_dans_zone) > 0:
                # Extraire les points dans la zone
                src_zone = np.array([points_pixels[i] for i in indices_dans_zone], dtype=np.float32)
                # print(src_zone)
                # print(src_zone)
                dst_zone = np.array([points_cm[i] for i in indices_dans_zone], dtype=np.float32)

                # H_pixels_to_cm, status = cv2.findHomography(src_zone, dst_zone, method=cv2.LMEDS)
                print(f"Application de l'homographie aux points DANS LA ZONE ({len(src_zone)} points)...")
                # print(dst_zone)
                # print(src_zone)
                # Application de la transformation aux points pixels de la zone
                src_zone_reshaped = src_zone.reshape(-1, 1, 2)
                converted_points_zone = cv2.perspectiveTransform(src_zone_reshaped, H_pixels_to_cm).reshape(-1, 2)

                # Calcul des distances entre points théoriques et calculés (uniquement zone)
                distances_zone = np.linalg.norm(dst_zone - converted_points_zone, axis=1)

                # Statistiques sur la zone uniquement

                print(f"   Nombre de points dans zone: {len(distances_zone)}")
                print(f"   Erreur moyenne: {np.mean(distances_zone):.6f} cm")
                print(f"   Erreur min: {np.min(distances_zone):.6f} cm")
                print(f"   Erreur max: {np.max(distances_zone):.6f} cm")

                # Graphique: Points avec heat map des distances (uniquement zone)
                scatter = ax2.scatter(dst_zone[:, 0], dst_zone[:, 1],
                                      c=distances_zone, cmap='viridis',
                                      marker='s', s=1000, alpha=0.8,
                                      label='Points dans zone (gradient = erreur)',
                                      vmin=0, vmax=0.05)

                # Ajouter des lignes de connexion avec couleur selon distance
                for i, (phys, trans) in enumerate(zip(dst_zone, converted_points_zone)):
                    color = plt.cm.viridis(
                        distances_zone[i] / np.max(distances_zone) if np.max(distances_zone) > 0 else 0)
                    ax2.plot([phys[0], trans[0]], [phys[1], trans[1]],
                             color=color, linestyle='--', linewidth=1.0, alpha=0.5)

                # Barre de couleur
                cbar = plt.colorbar(scatter, ax=ax2)
                cbar.set_label('Erreur entre la théorie et exp (cm)', fontsize=12)

                # Titre avec statistiques sur la zone
                ax2.set_title(f'Heatmap des erreurs - {titre_etape}\n'
                              f'(UNIQUEMENT points dans zone: {len(distances_zone)} points)\n'
                              f'Moy: {np.mean(distances_zone):.4f} cm | Max: {np.max(distances_zone):.4f} cm | '
                              )
                ax2.set_xlabel('X (cm)')
                ax2.set_ylabel('Y (cm)')
                ax2.grid(True, alpha=0.3)
                ax2.axis('equal')

                # Point avec la plus grande erreur dans la zone
                max_error_idx_zone = np.argmax(distances_zone)
                # Récupérer l'index global pour affichage
                global_max_idx = indices_dans_zone[max_error_idx_zone]
                ax2.scatter([dst_zone[max_error_idx_zone, 0]], [dst_zone[max_error_idx_zone, 1]],
                            c='red', marker='*', s=300, edgecolors='white', linewidth=2,
                            label=f'Max erreur zone: {distances_zone[max_error_idx_zone]:.4f} cm')

                ax2.legend()

                print(f"\n✅ Heatmap générée avec succès (points dans zone uniquement)")
                print(
                    f"   Point dans zone avec max erreur: #{global_max_idx + 1} - {distances_zone[max_error_idx_zone]:.6f} cm")

            else:
                print("Aucun point dans la zone")
                ax2.text(0.5, 0.5, "Aucun point dans la zone",
                         ha='center', va='center', transform=ax2.transAxes, fontsize=14)
                ax2.set_title('Heatmap - Aucun point dans la zone')
        else:
            print("Échec du calcul de l'homographie")
            ax2.text(0.5, 0.5, "Échec du calcul de l'homographie",
                     ha='center', va='center', transform=ax2.transAxes, fontsize=14)
            ax2.set_title('Heatmap - Erreur de calcul')
    else:
        print("Pas assez de points pour calculer l'homographie")
        ax2.text(0.5, 0.5, "Pas assez de points",
                 ha='center', va='center', transform=ax2.transAxes, fontsize=14)
        ax2.set_title('Heatmap - Points insuffisants')

    plt.tight_layout()
    plt.show()

    return fig


# ==========================================================================================
# CORRECTION PERSPECTIVE IMAGE ET POINTS PX
# ==========================================================================================

def correct_distortion_perspective(img, points_pixels, points_cm, img_path, suffixe="_corrigee_perspective"):
    #      Corrige la distorsion de l'image en utilisant les points de contrôle avec warpPerspective

    #     Args:
    #        img: Image à corriger (zone rognée)
    #       points_pixels: Liste des points pixels dans l'image (déjà ajustés au référentiel rogné)
    #       points_cm: Liste des points physiques correspondants
    #       img_path: Chemin de l'image originale (pour générer le nom de sauvegarde)
    #       suffixe: Suffixe à ajouter au nom du fichier

    #   Returns:
    #       mire_corrected: Image corrigée
    #       output_path: Chemindete de l'image sauvegardée
    #       transformed_pixels: Points pixels après transformation

    global transformed_pixels_perspective, transformed_physical_perspective, H_perspective, w_perspective, h_perspective

    if len(points_pixels) >= 4:
        print(f"\n{'=' * 60}")
        print("CORRECTION PERSPECTIVE DE L'IMAGE ROGNÉE")
        print(f"{'=' * 60}")
        print(f"Nombre de points utilisés: {len(points_pixels)}")

        # Points source (pixels dans l'image rognée)
        src_pts = np.array(points_pixels, dtype=np.float32)

        # Construction des points destination (basés sur les coordonnées physiques)
        dst_pts = []
        ref_x, ref_y = points_pixels[0]  # Point de référence dans l'image

        # Calcul du facteur d'échelle pixels/cm
        if len(points_pixels) >= 2:
            px_dist = np.linalg.norm(np.array(points_pixels[1]) - np.array(points_pixels[0]))
            cm_dist = np.linalg.norm(np.array(points_cm[1]) - np.array(points_cm[0]))
            px_per_cm = px_dist / cm_dist if cm_dist > 0 else 100
            print(f"Facteur d'échelle calculé: {px_per_cm:.2f} pixels/cm")
        else:
            px_per_cm = 100
            print(f"Facteur d'échelle par défaut: {px_per_cm} pixels/cm")

        # Construction des points destination dans l'espace image
        for (px, py), (cm_x, cm_y) in zip(points_pixels, points_cm):
            # Déplacement par rapport au premier point
            dx = (cm_x - points_cm[0][0]) * px_per_cm
            dy = -(cm_y - points_cm[0][1]) * px_per_cm  # Négatif car Y image vers le bas
            dst_pts.append([ref_x + dx, ref_y + dy])

        dst_pts = np.array(dst_pts, dtype=np.float32)

        # Calcul de l'homographie
        print("Calcul de l'homographie...")
        H_perspective, status = cv2.findHomography(src_pts, dst_pts, method=cv2.LMEDS)
        # H_perspective, status = cv2.findHomography(src_zone, dst_zone, method=cv2.LMEDS)
        if H_perspective is None:
            print("Échec du calcul de l'homographie")
            return img, None, None

        print(f"Homographie calculée avec succès")

        # Dimensions de l'image
        h_perspective, w_perspective = img.shape[:2]

        # Application de la transformation
        print("   Application de la transformation perspective...")
        mire_corrected = cv2.warpPerspective(
            img,
            H_perspective,
            (w_perspective, h_perspective),
            flags=cv2.INTER_LANCZOS4,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0
        )

        # Transformation des points pixels
        transformed_pts = cv2.perspectiveTransform(
            src_pts.reshape(1, -1, 2),
            H_perspective
        ).reshape(-1, 2)

        transformed_pixels_perspective = [(float(x), float(y)) for x, y in transformed_pts]
        transformed_physical_perspective = points_cm.copy()

        # Sauvegarde de l'image corrigée
        dossier = os.path.dirname(img_path)
        nom_base = os.path.splitext(os.path.basename(img_path))[0]
        output_path = os.path.join(dossier, f"{nom_base}{suffixe}.tif")

        cv2.imwrite(output_path, mire_corrected)
        print(f"Image corrigée (perspective) sauvegardée: {output_path}")
        print(f"Dimensions: {w_perspective} x {h_perspective} pixels")

        return img, None, None


# ==========================================================================================
# CORRECTION RADIALE IMAGE ET POINTS PX
# ==========================================================================================

def correct_distortion_radiale(img, points_pixels, points_cm, img_path, suffixe="_radiale"):
    """
    Corrige la distorsion radiale de l'image en utilisant cv2.calibrateCamera et cv2.undistort
    """
    global transformed_pixels_radiale, transformed_physical_radiale, mtx, dist, w_radiale, h_radiale

    if len(points_pixels) >= 4:
        print("Calibration de la caméra pour correction de distorsion radiale...")

        imgpoints = np.array(points_pixels, dtype=np.float32).reshape(-1, 1, 2)

        objpoints = []
        for x_cm, y_cm in points_cm:
            objpoints.append([x_cm, y_cm, 0.0])
        objpoints = np.array(objpoints, dtype=np.float32).reshape(-1, 1, 3)

        h_radiale, w_radiale = img.shape[:2]
        img_size = (w_radiale, h_radiale)

        print("Calcul des paramètres de distorsion...")
        ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
            [objpoints],
            [imgpoints],
            img_size,
            None,
            None
        )

        if ret:
            print("Calibration réussie !")
            print(f"Matrice de caméra (mtx):")
            print(f"{mtx}")
            print(f"Coefficients de distorsion (dist): {dist.ravel()}")

            print("Application de la correction de distorsion...")
            mire_corrected = cv2.undistort(img, mtx, dist, None, mtx)

            points_pixels_array = np.array(points_pixels, dtype=np.float32).reshape(-1, 1, 2)
            transformed_pts = cv2.undistortPoints(points_pixels_array, mtx, dist, P=mtx)
            transformed_pts = transformed_pts.reshape(-1, 2)

            transformed_pixels_radiale = [(float(x), float(y)) for x, y in transformed_pts]
            transformed_physical_radiale = points_cm.copy()

            # Sauvegarde de l'image corrigée
            dossier = os.path.dirname(img_path)
            nom_base = os.path.splitext(os.path.basename(img_path))[0]
            output_path = os.path.join(dossier, f"{nom_base}{suffixe}.tif")
            cv2.imwrite(output_path, mire_corrected)
            print(f"Image de mire corrigée (radiale) sauvegardée")

            print(f"\n{'=' * 60}")
            print("POINTS APRÈS CORRECTION RADIALE")
            print(f"{'=' * 60}")
            print(f"Points pixels d'entrée: {len(points_pixels)} points")
            print(f"Points pixels après radiale: {len(transformed_pixels_radiale)} points")
            print(f"Points physiques: {len(points_cm)} points (inchangés)")

            return mire_corrected, output_path
        else:
            print("Échec de la calibration de la caméra")
            return img, None
    else:
        print("Pas assez de points pour la calibration (minimum 4 requis)")
        return img, None


# ==========================================================================================
# CORRECTION DES IMAGES EXPS
# ==========================================================================================

def demander_confirmation_traitement():
    """
    Demande confirmation à l'utilisateur avant de traiter les dossiers d'images
    """
    print(f"\n{'=' * 60}")
    print("CONFIRMATION DU TRAITEMENT DES IMAGES")
    print(f"{'=' * 60}")

    while True:
        confirmation = input("Voulez-vous procéder au traitement des dossiers d'images? (y/n): ").strip().lower()
        if confirmation in ['y', 'yes', 'o', 'oui']:
            print("Traitement des images confirmé...")
            return True
        elif confirmation in ['n', 'no', 'non']:
            print("Traitement des images annulé.")
            return False
        else:
            print("Réponse invalide. Veuillez répondre par 'y' (oui) ou 'n' (non).")


def traiter_dossiers_images():
    """
    Traite tous les dossiers d'images en appliquant les mêmes transformations que sur la mire :
    d'abord la correction perspective, puis la correction radiale
    """
    # Déclare les variables globales
    global H_perspective, w_perspective, h_perspective, mtx, dist

    # Vérifie que les deux matrices de transformation sont disponibles
    if H_perspective is None:
        print("Matrice de correction perspective non disponible. Veuillez d'abord traiter l'image de mire.")
        return False

    if mtx is None or dist is None:
        print("Paramètres de correction radiale non disponibles. Veuillez d'abord traiter l'image de mire.")
        return False

    # Dossiers à traiter - À ADAPTER SELON VOS BESOINS
    # base_path = '/Volumes/One Touch/DRACCARV1/'  # À modifier selon votre structure
    # folders = [

    # ('/Volumes/One Touch/DRACCARV1/Tests/PIV/Campagne/avec_mat/14/CAM1','/Volumes/One Touch/DRACCARV1/Tests/PIV/Campagne/avec_mat/14/CAM1/CAM1_sansdistor'),

    # ]

    total_images = 0
    total_dossiers = 0
    images_par_dossier = {}

    # Parcourt tous les dossiers spécifiés
    for input_dir, output_dir in folders:
        # Vérifie que le dossier source existe
        if not os.path.exists(input_dir):
            print(f"⚠️  Dossier source inexistant: {input_dir}")
            continue

        # Crée le dossier de sortie s'il n'existe pas
        os.makedirs(output_dir, exist_ok=True)

        # Liste tous les fichiers image dans le dossier d'entrée
        # Adapter l'extension et le pattern selon vos besoins
        image_files = sorted([f for f in os.listdir(input_dir)
                              if f.lower().endswith(('.tif'))
                              and not f.startswith('.')])

        if not image_files:
            print(f"⚠️  Aucune image trouvée dans le dossier: {input_dir}")
            continue

        images_par_dossier[os.path.basename(input_dir)] = len(image_files)
        total_images += len(image_files)
        total_dossiers += 1

        print(f"\n Traitement du dossier: {os.path.basename(input_dir)}")
        print(f" Destination: {os.path.basename(output_dir)}")
        print(f"  {len(image_files)} images à traiter")

        # Traite chaque image du dossier avec tqdm
        for filename in tqdm(image_files, desc=f"Traitement {os.path.basename(input_dir)}"):
            current_img_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)

            try:
                # Charge l'image
                img_to_correct = cv2.imread(current_img_path)

                if img_to_correct is None:
                    print(f"Impossible de charger: {filename}")
                    continue

                # ÉTAPE 1: CORRECTION PERSPECTIVE
                img_corrected_perspective = cv2.warpPerspective(
                    img_to_correct,
                    H_perspective,
                    (w_perspective, h_perspective),
                    flags=cv2.INTER_LANCZOS4,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=0
                )

                # ÉTAPE 2: CORRECTION RADIALE
                img_corrected_final = cv2.undistort(
                    img_corrected_perspective,
                    mtx,
                    dist,
                    None,
                    mtx
                )

                # Sauvegarde l'image corrigée finale
                cv2.imwrite(output_path, img_corrected_final)

            except Exception as e:
                print(f"❌ Erreur sur {filename}: {e}")
                continue

    # Résumé final
    if total_images > 0:
        print(f"\n{'=' * 60}")
        print("RÉSUMÉ DU TRAITEMENT DES IMAGES")
        print(f"{'=' * 60}")
        print(f"Dossiers traités: {total_dossiers}")
        for dossier, nb_images in images_par_dossier.items():
            print(f"   • {dossier}: {nb_images} images")
        print(f"Traitement terminé: {total_images} images corrigées au total")
        print(f"{'=' * 60}")
        return True
    else:
        print("Aucune image n'a été traitée.")
        return False


# ==========================================================================================
# DÉTECTION DE LA SURFACE LIBRE ET RECALAGE VERTICAL
# ==========================================================================================

def detecter_surface_libre_et_recaler():
    """
    Fonction pour détecter la surface libre sur une image de test,
    puis recaler les coordonnées physiques en Y en fonction du résultat
    """
    global transformed_pixels_radiale, transformed_physical_radiale
    print(f"\n{'=' * 60}")
    print("PHASE DE DÉTECTION DE LA SURFACE LIBRE ET RECALAGE VERTICAL")
    print(f"{'=' * 60}")

    # =============================================================================
    # PARAMÈTRES MODIFIABLES - Ajustez ces valeurs selon vos besoins
    # =============================================================================

    # Chemins des dossiers d'images de surface libre
    # dossiers_surface_libre = [
    #    '/Volumes/One Touch/DRACCARV1/Caracterisation_vagues_octobre_novembre_Mm/Tests/test_temps_attente/4/4_2/CAM1_sansdistor',
    #   '/Volumes/One Touch/DRACCARV1/Caracterisation_vagues_octobre_novembre_Mm/Tests/test_differents_xf/146/CAM1_sansdistor',
    #  '/Volumes/One Touch/DRACCARV1/Caracterisation_vagues_octobre_novembre_Mm/Tests/test_particules/CAM1_sansdistor'
    # ]

    # Nom du fichier image à utiliser pour la détection
    # image_sf = 'Image_0000.tif'  # À ajuster selon votre nomenclature

    # Paramètres de détection
    HAUTEUR_RECTANGLE = 50  # Hauteur du rectangle en pixels
    NOMBRE_SOUS_ZONES = 30  # Nombre de subdivisions horizontales
    LARGEUR_RECTANGLE = None  # None = toute la largeur, ou spécifier une valeur en pixels
    ZOOM_PROFIL = 100  # Nombre de lignes à afficher autour du maximum
    YLIM_INF = 500  # Limite inférieure pour le calcul d'intensité
    YLIM_SUP = 640  # Limite supérieure pour le calcul d'intensité

    # =============================================================================

    # Vérifier que les points de calibration sont disponibles
    if transformed_pixels_radiale is None or transformed_physical_radiale is None:
        print("Points de calibration radiale non disponibles.")
        print("Veuillez d'abord exécuter la phase de correction radiale.")
        return False

    print(f"\nPoints de calibration disponibles :")
    print(f"  • {len(transformed_pixels_radiale)} points pixels (après radiale)")
    print(f"  • {len(transformed_physical_radiale)} points cm correspondants")

    # =============================================================================
    # FONCTIONS DE CONVERSION
    # =============================================================================

    def convert_pixel_to_cm(x_pixel, y_pixel):
        """
        Convertit la position (x,y) en pixels en centimètres en utilisant la matrice d'homographie
        """
        try:
            # Calcul de la matrice d'homographie entre points pixels et points cm
            H, _ = cv2.findHomography(
                np.array(transformed_pixels_radiale, dtype=np.float32),
                np.array(transformed_physical_radiale, dtype=np.float32)
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

    # =============================================================================
    # TRAITEMENT DE L'IMAGE
    # =============================================================================

    # Charger la première image
    chemin_premiere_image = os.path.join(dossier_images, image_sf)

    if not os.path.exists(chemin_premiere_image):
        print(f"❌ Fichier non trouvé : {chemin_premiere_image}")
        # Lister les fichiers disponibles
        fichiers = [f for f in os.listdir(dossier_images) if f.lower().endswith(('.tif', '.tiff', '.png', '.jpg'))]
        if fichiers:
            print(f"Fichiers image trouvés : {len(fichiers)}")
            print("Exemples :")
            for f in sorted(fichiers)[:5]:
                print(f"  {f.name if hasattr(f, 'name') else f}")
        return False

    # Charger l'image en niveaux de gris
    image = cv2.imread(chemin_premiere_image, cv2.IMREAD_GRAYSCALE)
    if image is None:
        # Essayer une autre méthode de chargement
        from matplotlib.image import imread
        image_color = imread(chemin_premiere_image)
        if len(image_color.shape) == 3:
            image = cv2.cvtColor(image_color, cv2.COLOR_RGB2GRAY)
        else:
            image = image_color

    print(f"Image chargée : {os.path.basename(chemin_premiere_image)}")
    print(f"Dimensions de l'image : {image.shape}")
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
    somme_lignes = np.zeros(image.shape[0])

    # Calculer la somme uniquement pour les lignes dans la plage YLIM
    for y in range(image.shape[0]):
        if YLIM_INF <= y <= YLIM_SUP:
            somme_lignes[y] = np.sum(image[y, :])
        else:
            somme_lignes[y] = 0

    # 2. Trouver la ligne avec l'intensité maximale DANS LA ZONE LIMITÉE
    masque_zone = np.zeros(image.shape[0], dtype=bool)
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
        ligne_max, image.shape[1]
    )

    # =============================================================================
    # RECALAGE VERTICAL DES COORDONNÉES PHYSIQUES
    # =============================================================================

    print(f"\n{'=' * 60}")
    print("RECALAGE VERTICAL DES COORDONNÉES PHYSIQUES")
    print(f"{'=' * 60}")
    print(f"Hauteur de surface libre détectée : {hauteur_cm:.4f} cm")

    # Sauvegarder les anciennes coordonnées pour comparaison
    anciennes_coords_y = [y for _, y in transformed_physical_radiale]

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
    for i, (x, _) in enumerate(transformed_physical_radiale):
        nouvelle_coords.append((x, nouvelle_coords_y[i]))

    transformed_physical_radiale = nouvelle_coords

    # =============================================================================
    # AFFICHAGE DES NOUVELLES COORDONNÉES
    # =============================================================================

    print(f"\n{'=' * 80}")
    print("COORDONNÉES APRÈS RECALAGE VERTICAL")
    print(f"{'=' * 80}")
    print(
        f"{'No':<6} {'X (px)':<12} {'Y (px)':<12} {'X (cm)':<12} {'Y (cm) ANCIEN':<16} {'Y (cm) NOUVEAU':<16} {'Écart (cm)':<12}")
    print(f"{'-' * 90}")

    for i in range(len(transformed_pixels_radiale)):
        px, py = transformed_pixels_radiale[i]
        x_cm, y_cm_nouveau = transformed_physical_radiale[i]
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
            np.array(transformed_pixels_radiale, dtype=np.float32),
            np.array(transformed_physical_radiale, dtype=np.float32)
        )

        print(f"\nMatrice d'homographie H (pixels -> cm) APRÈS RECALAGE :")
        np.set_printoptions(precision=10, suppress=True)
        for i in range(3):
            print(f"  [{H_nouvelle[i][0]:15.10f} {H_nouvelle[i][1]:15.10f} {H_nouvelle[i][2]:15.10f}]")

        # Comparaison avec l'ancienne matrice
        H_ancienne, _ = cv2.findHomography(
            np.array(transformed_pixels_radiale, dtype=np.float32),
            np.array([(x, y_ancien) for (x, y_ancien) in
                      zip([x for x, _ in transformed_physical_radiale], anciennes_coords_y)], dtype=np.float32)
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
        largeur_rectangle = image.shape[1]  # Toute la largeur de l'image
        x_min = 0
        x_max = image.shape[1]
    else:
        largeur_rectangle = LARGEUR_RECTANGLE
        x_min = (image.shape[1] - largeur_rectangle) // 2
        x_max = x_min + largeur_rectangle

    # 5. Créer la visualisation
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))

    # Graphique 1: Image originale avec le rectangle
    ax1.imshow(image, cmap='gray')
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
    plt.show()

    # Afficher les informations détaillées
    print(f"\n=== ZONE D'INTENSITÉ MAXIMALE DÉTECTÉE ===")
    print(f"Recherche limitée à ylim : {YLIM_INF} - {YLIM_SUP}")
    print(f"Ligne avec intensité maximale : {ligne_max} pixels")
    print(f"Hauteur de surface libre : {hauteur_cm:.4f} cm")
    print(f"Recalage appliqué : {'OUI' if hauteur_cm != 0 else 'NON'}")
    print(f"Nouvelle origine Y : {transformed_physical_radiale[0][1]:.4f} cm")

    # Demander si l'utilisateur veut sauvegarder ces nouvelles coordonnées
    print(f"\n{'=' * 60}")
    print("SAUVEGARDE DES COORDONNÉES RECALÉES")
    print(f"{'=' * 60}")

    while True:
        reponse = input(
            "Voulez-vous sauvegarder ces nouvelles coordonnées dans un fichier? (oui/o/y ou non/n): ").strip().lower()

        if reponse in ['oui', 'o', 'y', 'yes']:
            # Générer un nom de fichier avec indication du recalage
            base_path = '/Volumes/One Touch/DRACCARV2/Tests/Marée Moyenne 0,700m/Période 1,6s/Amplitude 0.21m/Sans mât/Mire/CAM1/'
            nom_base = os.path.splitext(os.path.basename(image_path))[0]
            fichier_sortie = os.path.join(base_path, f"{nom_base}_coordonnees_recallees_y{hauteur_cm:+.4f}cm.txt")

            with open(fichier_sortie, 'w', encoding='utf-8') as f:
                f.write("# FICHIER DE COORDONNÉES DE CALIBRATION APRÈS RECALAGE VERTICAL\n")
                f.write("# " + "=" * 70 + "\n")
                f.write(f"# Fichier source: {image_path}\n")
                f.write(f"# Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Hauteur surface libre détectée: {hauteur_cm:.4f} cm\n")
                f.write(
                    f"# Recalage appliqué: {'AJOUT' if hauteur_cm > 0 else 'SOUSTRACTION' if hauteur_cm < 0 else 'AUCUN'}\n")
                f.write(f"# Nombre de points: {len(transformed_pixels_radiale)}\n")
                f.write("# " + "=" * 70 + "\n")
                f.write("# Format: index, x_pixel, y_pixel, x_cm, y_cm\n")
                f.write("# " + "-" * 70 + "\n")

                for i, (pixel, cm) in enumerate(zip(transformed_pixels_radiale, transformed_physical_radiale)):
                    f.write(f"{i + 1:4d}  {pixel[0]:12.4f}  {pixel[1]:12.4f}  {cm[0]:12.4f}  {cm[1]:12.4f}\n")

            print(f"Coordonnées recalées sauvegardées dans: {fichier_sortie}")
            break
        elif reponse in ['non', 'n', 'no']:
            print("Sauvegarde ignorée.")
            break
        else:
            print("Réponse invalide. Veuillez répondre par 'oui' (o/y) ou 'non' (n).")

    return True


# ==========================================================================================
# MAIN PROGRAMME COMPLET
# ==========================================================================================

if __name__ == "__main__":

    # Chemin de base
    base_path = '/Volumes/One Touch/DRACCARV2/Tests/Marée Moyenne 0,700m/Période 1,6s/Amplitude 0.21m/Sans mât/Mire/CAM1/'
    image_path = os.path.join(base_path, 'Image_cam1_000000.tif')

    nom_base = os.path.splitext(os.path.basename(image_path))[0]

    # Correction : utiliser f-strings ou .format() pour insérer la variable
    image_rogee_path = os.path.join(base_path, f'{nom_base}_rogee.tif')
    image_perspective_path = os.path.join(base_path, f'{nom_base}_rogee_corrigee_perspective.tif')
    image_radiale_path = os.path.join(base_path, f'{nom_base}_rogee_corrigee_perspective_radiale.tif')

    # ======================================================================================
    # PHASE DE DETECTION
    # ======================================================================================

    print(f"\n{'=' * 60}")
    print("DEBUT DE LA PHASE DE DETECTION DES COINS DE TOUTE LA MIRE, REORGANISATION, N")
    print(f"{'=' * 60}")

    # ÉTAPE 1: Chargement ou détection des coins
    points_pixels_origine, points_cm_origine, pattern, n_initial, zone_coords = charger_ou_detecter_coins(image_path)
    img = afficher_points_sur_image(image_path, points_pixels_origine, pattern, zone_coords)
    if img is None:
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print("FIN DE LA PHASE DE DETECTION DES COINS DE TOUTE LA MIRE, REORGANISATION, N")
    print(f"{'=' * 60}")

    # ======================================================================================
    # PHASE DE FENETRAGE
    # ======================================================================================

    print(f"\n{'=' * 60}")
    print("DEBUT DE LA PHASE DE FENETRAGE, MODIFICATION ORIGINE Y CM, MODIFICATION REFERENTIEL PX, SAVE FENETRAGE .TIF")
    print(f"{'=' * 60}")

    # ÉTAPE 2: Demander les coordonnées de rognage
    left, top, width, height = demander_coordonnees_rognage()

    # ÉTAPE 3: Extraire la zone rognée
    zone_rogee, left_adj, top_adj, width_adj, height_adj, output_path = extraire_zone_rognage(
        img, left, top, width, height, image_path, suffixe="_rogee"
    )

    # ÉTAPE 4: AJUSTER LES POINTS PIXELS DANS LE NOUVEAU RÉFÉRENTIEL
    indices_dans_zone, indices_hors_zone, anciens_pixels = ajuster_points_referentiel_rognage(
        points_pixels_origine, left_adj, top_adj, width_adj, height_adj
    )

    # ÉTAPE 5: RÉINITIALISER L'ORIGINE Y DES POINTS CM
    idx_ref, y_offset = reinitialiser_origine_y_points_cm(
        points_pixels_origine, points_cm_origine, indices_dans_zone
    )

    # Affichage avec l'image rognée (image_rogee_path)
    fig_origine = afficher_resultats_fenetrage(
        image_rogee_path,
        points_pixels_origine,
        points_cm_origine,
        0, 0, width_adj, height_adj,
        idx_ref,
        image_rogee_path,
        titre_etape="ORIGINALE"  # ← NOUVEAU paramètre
    )

    print(f"\n{'=' * 60}")
    print("FIN DE LA PHASE DE FENETRAGE, MODIFICATION ORIGINE Y CM, MODIFICATION REFERENTIEL PX, SAVE FENETRAGE .TIF")
    print(f"{'=' * 60}")

    # ======================================================================================
    # PHASE DE CORRECTION PERSPECTIVE + HEATMAP
    # ======================================================================================

    print(f"\n{'=' * 60}")
    print("DEBUT DE LA PHASE DE CORRECTION PERSPECTIVE")
    print(f"{'=' * 60}")

    # Correction perspective en utilisant l'image rognée
    img_rogee = cv2.imread(image_rogee_path)
    if img_rogee is not None:
        # Appel de la fonction de correction perspective

        mire_corrected_perspective, path_perspective, transformed_points = correct_distortion_perspective(
            img=img_rogee,
            points_pixels=points_pixels_origine,  # Tous les points
            points_cm=points_cm_origine,  # Tous les points cm
            img_path=image_rogee_path,
            suffixe="_corrigee_perspective"
        )

        # points_pixels_zone = [points_pixels_origine[i] for i in indices_dans_zone]
        # points_cm_zone     = [points_cm_origine[i]     for i in indices_dans_zone]

        # mire_corrected_perspective, path_perspective, transformed_points = correct_distortion_perspective(
        #   img=img_rogee,
        #   points_pixels=points_pixels_zone,   # ← uniquement les points dans la zone
        #   points_cm=points_cm_zone,           # ← uniquement les points cm correspondants
        #   img_path=image_rogee_path,
        #  suffixe="_corrigee_perspective"
        # )

        print(f"Image corrigée (perspective) créée: {image_perspective_path}")

        # Affichage avec l'image corrigée en perspective
        fig_perspective = afficher_resultats_fenetrage(
            image_perspective_path,
            transformed_pixels_perspective,
            transformed_physical_perspective,
            0, 0, width_adj, height_adj,
            idx_ref,
            image_perspective_path,
            titre_etape="PERSPECTIVE"  # ← NOUVEAU paramètre
        )

        print(f"\n{'=' * 60}")
        print("FIN DE LA PHASE DE CORRECTION PERSPECTIVE")
        print(f"{'=' * 60}")

    # ======================================================================================
    # PHASE DE CORRECTION RADIALE + HEATMAP
    # ======================================================================================

    print(f"\n{'=' * 60}")
    print("DEBUT DE LA PHASE DE CORRECTION RADIALE")
    print(f"{'=' * 60}")

    # Correction radiale en utilisant l'image rognée perspective
    img_rogee_perspective = cv2.imread(image_perspective_path)
    if img_rogee_perspective is not None:
        # Appel de la fonction de correction radiale - retourne 2 valeurs
        mire_corrected_radiale, path_radiale = correct_distortion_radiale(
            img=img_rogee_perspective,
            points_pixels=transformed_pixels_perspective,  # Tous les points après perspective
            points_cm=transformed_physical_perspective,  # Tous les points cm
            img_path=image_perspective_path,
            suffixe="_radiale"
        )

        print(f"Image corrigée (radiale) créée: {image_radiale_path}")

        # Affichage avec l'image corrigée en radiale
        fig_radiale = afficher_resultats_fenetrage(
            image_radiale_path,
            transformed_pixels_radiale,
            transformed_physical_radiale,
            0, 0, width_adj, height_adj,
            idx_ref,
            image_radiale_path,
            titre_etape="RADIALE"  # ← NOUVEAU paramètre
        )

        print(f"\n{'=' * 60}")
        print("FIN DE LA PHASE DE CORRECTION RADIALE")
        print(f"{'=' * 60}")

    plt.pause(2)
    print("Appuyez sur Entrée pour continuer vers la phase de correction des images...")
    input()

    # ======================================================================================
    # PHASE DE CORRECTION DES IMAGES EXPS
    # ======================================================================================

    if demander_confirmation_traitement():
        print("Configuration des dossiers à traiter...")
        # Appel de la fonction de traitement des dossiers
        traiter_dossiers_images()

        # ==================================================================================
        # PHASE DE DÉTECTION DE LA SURFACE LIBRE ET RECALAGE
        # ==================================================================================

        print(f"\n{'=' * 60}")
        print("PHASE FINALE : DÉTECTION DE LA SURFACE LIBRE")
        print(f"{'=' * 60}")

        while True:
            reponse = input(
                "\nVoulez-vous procéder à la détection de la surface libre et au recalage vertical? (y/n): ").strip().lower()
            if reponse in ['y', 'yes', 'o', 'oui']:
                detecter_surface_libre_et_recaler()
                break
            elif reponse in ['n', 'no', 'non']:
                print("Phase de détection de surface libre ignorée.")
                break
            else:
                print("Réponse invalide. Veuillez répondre par 'y' (oui) ou 'n' (non).")
    else:
        print("Phase de correction des images expérimentales ignorée.")

        # Même si le traitement des images est ignoré, on peut quand même proposer la détection
        print(f"\n{'=' * 60}")
        print("PHASE FINALE : DÉTECTION DE LA SURFACE LIBRE")
        print(f"{'=' * 60}")

        while True:
            reponse = input(
                "\nVoulez-vous procéder à la détection de la surface libre et au recalage vertical? (y/n): ").strip().lower()
            if reponse in ['y', 'yes', 'o', 'oui']:
                detecter_surface_libre_et_recaler()
                break
            elif reponse in ['n', 'no', 'non']:
                print("Phase de détection de surface libre ignorée.")
                break
            else:
                print("Réponse invalide. Veuillez répondre par 'y' (oui) ou 'n' (non).")

    print(f"\n{'=' * 60}")
    print("PROGRAMME TERMINÉ AVEC SUCCÈS")
    print(f"{'=' * 60}")