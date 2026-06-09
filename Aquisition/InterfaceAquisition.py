import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                             QVBoxLayout, QPushButton, QLabel, QStackedWidget,
                             QFrame, QGridLayout, QScrollArea, QSpinBox, QProgressBar, QFileDialog, QMessageBox,
                             QComboBox, QLineEdit)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import QTimer
import pyqtgraph as pg
import math

from Aquisition.AquisitionThread import AcquisitionThread
from GestionnaireNI import GestionnaireNI
from PyQt6.QtWidgets import QMessageBox
# Importer la classe et ses erreurs
from GestionnaireKistler1 import (
    GestionnaireKistler, BoitierIntrouvableError,
    TimeoutReseauError, ConnexionInterrompueError, KistlerError
)

# ==========================================
# 1. CLASSE PERSONNALISÉE POUR LES VOIES
# ==========================================
class VoieButton(QFrame):
    def __init__(self, nom_boitier, nom_voie, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.nom_boitier = nom_boitier  # Le bouton mémorise son boîtier
        self.nom_voie = nom_voie  # Le bouton mémorise sa voie
        self.is_checked = False

        self.setMinimumHeight(35)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Layout interne pour le texte et le tiret
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)

        self.lbl_nom = QLabel(nom_voie)
        self.lbl_tiret = QLabel("—")

        layout.addWidget(self.lbl_nom)
        layout.addStretch()
        layout.addWidget(self.lbl_tiret)

        self.update_style()

    def mouseReleaseEvent(self, event):
        # Capture le clic gauche pour sélectionner/désélectionner
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_checked(not self.is_checked)
        super().mouseReleaseEvent(event)

    def set_checked(self, state):
        self.is_checked = state
        self.update_style()

    def update_style(self):
        if self.is_checked:
            self.setStyleSheet("""
                VoieButton {
                    background-color: #E6F1FB;
                    border: 1px solid #378ADD;
                    border-radius: 6px;
                }
            """)
            self.lbl_nom.setStyleSheet("color: #0C447C; font-weight: bold; font-size: 12px; background: transparent;")
            self.lbl_tiret.setStyleSheet("color: #185FA5; font-weight: bold; font-size: 12px; background: transparent;")
        else:
            self.setStyleSheet("""
                VoieButton {
                    background-color: #f9fafb;
                    border: 1px solid #e5e7eb;
                    border-radius: 6px;
                }
                VoieButton:hover {
                    background-color: #f3f4f6;
                }
            """)
            self.lbl_nom.setStyleSheet("color: #1f2937; font-weight: normal; font-size: 12px; background: transparent;")
            self.lbl_tiret.setStyleSheet("color: #9ca3af; font-weight: bold; font-size: 12px; background: transparent;")


# ==========================================
# 2. FEUILLE DE STYLE GLOBALE
# ==========================================
STYLESHEET = """
    QMainWindow { background-color: #ffffff; }

    /* Menu Latéral */
    #Sidebar {
        background-color: #ffffff;
        border-right: 1px solid #e5e7eb;
    }
    #Sidebar QPushButton {
        text-align: left;
        padding: 10px 15px;
        border: none;
        border-left: 3px solid transparent;
        font-size: 13px;
        color: #4b5563;
        background-color: transparent;
    }
    #Sidebar QPushButton:hover { background-color: #f3f4f6; }
    #Sidebar QPushButton:checked {
        color: #185FA5;
        border-left: 3px solid #185FA5;
        background-color: #E6F1FB;
        font-weight: bold;
    }

    /* Topbar */
    #Topbar {
        background-color: #ffffff;
        border-bottom: 1px solid #e5e7eb;
    }
    #BtnMenu {
        border: none;
        border-right: 1px solid #e5e7eb;
        background-color: #ffffff;
        font-size: 18px;
    }
    #BtnMenu:hover { background-color: #f3f4f6; }

    /* Titres de sections */
    .SectionTitle {
        color: #4b5563;
        font-size: 10px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Cartes Boîtiers */
    .BoxButton {
        background-color: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        text-align: left;
    }
    .BoxButton:hover { background-color: #f3f4f6; }
    .BoxButton:checked {
        border: 1px solid #378ADD;
        background-color: #E6F1FB;
    }
    .BoxButton:disabled {
        background-color: #f9fafb;
        border: 1px solid #e5e7eb;
        opacity: 0.6;
    }

    /* Boutons standards */
    .BtnPrimary {
        background-color: #185FA5;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: bold;
    }
    .BtnPrimary:hover { background-color: #0C447C; }

    .BtnSecondary {
        background-color: #ffffff;
        color: #374151;
        border: 1px solid #d1d5db;
        border-radius: 4px;
        padding: 6px 12px;
    }
    .BtnSecondary:hover { background-color: #f3f4f6; }
    /* Paramètres */
    .ParamBox {
        border: 1px solid #d1d5db;
        border-radius: 4px;
        padding: 5px;
        background-color: #ffffff;
    }

    /* Bannière de succès */
    .SuccessBanner {
        background-color: #EAF3DE;
        border: 1px solid #C0DD97;
        border-radius: 6px;
    }
    .BtnSuccess {
        background-color: #C0DD97;
        color: #27500A;
        border: 1px solid #A4C773;
        border-radius: 4px;
        padding: 6px 12px;
        font-weight: bold;
    }
    .BtnSuccess:hover { background-color: #A4C773; }
    
    .BtnDanger {
        background-color: #FCEBEB;
        color: #791F1F;
        border: 1px solid #F7C1C1;
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: bold;
    }
    .BtnDanger:hover { background-color: #F7C1C1; }
    
    /* Barre de progression */
    QProgressBar {
        border: 1px solid #e5e7eb;
        border-radius: 4px;
        background-color: #f3f4f6;
        height: 8px;
        text-align: center;
        color: transparent; /* Cache le texte % par défaut */
    }
    QProgressBar::chunk {
        background-color: #378ADD;
        border-radius: 3px;
    }
    /* --- Calibration --- */
    .DropZone {
        background-color: #f9fafb;
        border: 2px dashed #d1d5db;
        border-radius: 8px;
        color: #6b7280;
        text-align: center;
        font-size: 13px;
    }
    .DropZone:hover {
        background-color: #f3f4f6;
        border-color: #9ca3af;
    }
    .FileBanner {
        background-color: #E6F1FB;
        border: 1px solid #B5D4F4;
        border-radius: 6px;
    }
    .InputCalib {
        border: 1px solid #d1d5db;
        border-radius: 4px;
        padding: 4px;
        background-color: #ffffff;
        font-family: monospace;
    }
    QComboBox {
        border: 1px solid #d1d5db;
        border-radius: 4px;
        padding: 4px;
        background-color: #ffffff;
    }
    .TagPression { background-color: #E6F1FB; color: #0C447C; border-radius: 10px; padding: 2px 8px; font-size: 10px; font-weight: bold; }
    .TagAccel { background-color: #EEEDFE; color: #3C3489; border-radius: 10px; padding: 2px 8px; font-size: 10px; font-weight: bold; }
    .TagTemp { background-color: #FAEEDA; color: #633806; border-radius: 10px; padding: 2px 8px; font-size: 10px; font-weight: bold; }
    .TagDebit { background-color: #EAF3DE; color: #27500A; border-radius: 10px; padding: 2px 8px; font-size: 10px; font-weight: bold; }
    .TagBrut { background-color: #f3f4f6; color: #4b5563; border-radius: 10px; padding: 2px 8px; font-size: 10px; font-weight: bold; }
     
     /* --- Visualisation --- */
    .VisuTab {
        border: none;
        border-bottom: 2px solid transparent;
        background: transparent;
        padding: 6px 12px;
        font-size: 12px;
        color: #6b7280;
    }
    .VisuTab:hover { color: #1f2937; }
    .VisuTab:checked {
        border-bottom: 2px solid #185FA5;
        color: #185FA5;
        font-weight: bold;
    }
    
    .MetricBox {
        background-color: #f9fafb;
        border-radius: 6px;
        padding: 10px 15px;
    }
    .MetricLabel {
        font-size: 10px;
        color: #6b7280;
        text-transform: uppercase;
        font-weight: bold;
        letter-spacing: 1px;
    }



"""


# ==========================================
# 3. APPLICATION PRINCIPALE
# ==========================================
class WaveLabApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # AJOUT : On connecte le backend à l'interface
        self.gestionnaire = GestionnaireNI()

        self.setWindowTitle("WaveLab - Acquisition")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(STYLESHEET)

        self.is_sidebar_open = True
        self.setup_ui()

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- Sidebar ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(200)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(0, 20, 0, 0)
        self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.nav_buttons = []
        menus = [
            ("Détection boîtiers", 0), ("Sélection voies", 1), ("Acquisition", 2),
            ("Calibration fichier", 3), ("Visualisation", 4)
        ]

        for text, index in menus:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked, idx=index: self.switch_page(idx))
            self.sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

            if index == 2:
                self.sidebar_layout.addSpacing(15)
                lbl = QLabel("  POST-TRAITEMENT")
                lbl.setProperty("class", "SectionTitle")
                self.sidebar_layout.addWidget(lbl)

        self.nav_buttons[0].setChecked(True)

        # --- Zone Principale ---
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # --- Topbar ---
        self.topbar = QFrame()
        self.topbar.setObjectName("Topbar")
        self.topbar.setFixedHeight(42)
        self.topbar_layout = QHBoxLayout(self.topbar)
        self.topbar_layout.setContentsMargins(0, 0, 15, 0)
        self.topbar_layout.setSpacing(10)

        self.btn_toggle_menu = QPushButton("☰")
        self.btn_toggle_menu.setObjectName("BtnMenu")
        self.btn_toggle_menu.setFixedSize(42, 42)
        self.btn_toggle_menu.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_toggle_menu.clicked.connect(self.toggle_sidebar)

        self.lbl_title = QLabel("WaveLab · Acquisition")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.lbl_top_status = QLabel("3 boîtiers trouvés")
        self.lbl_top_status.setStyleSheet("color: #6b7280; font-size: 11px;")

        self.topbar_layout.addWidget(self.btn_toggle_menu)
        self.topbar_layout.addWidget(self.lbl_title)
        self.topbar_layout.addStretch()
        self.topbar_layout.addWidget(self.lbl_top_status)

        # --- Assemblage Central (SANS Scroll global) ---
        self.stacked_widget = QStackedWidget()

        self.content_layout.addWidget(self.topbar)
        self.content_layout.addWidget(self.stacked_widget)

        self.setup_pages()


        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.content_area)

        # Animation du menu
        self.animation = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.setDuration(200)

    def setup_pages(self):
        self.page_detect = QWidget()
        self.page_voies = QWidget()
        self.page_acq = QWidget()

        self.build_page_detect()
        self.build_page_voies([])
        self.build_page_acq()
        self.build_page_calib()
        self.build_page_visu()

        self.stacked_widget.addWidget(self.page_detect)
        self.stacked_widget.addWidget(self.page_voies)
        self.stacked_widget.addWidget(self.page_acq)
        self.stacked_widget.addWidget(self.page_calib)
        self.stacked_widget.addWidget(self.page_visu)

    # ==========================================
    # CONSTRUCTION: PAGE "DÉTECTION"
    # ==========================================
    def build_page_detect(self):
        layout = QVBoxLayout(self.page_detect)
        layout.setContentsMargins(40, 30, 40, 30)

        header_layout = QHBoxLayout()
        lbl_header = QLabel("Détection des boîtiers réseau")
        lbl_header.setStyleSheet("font-size: 15px; font-weight: 500;")

        self.btn_scanner = QPushButton("Scanner")
        self.btn_scanner.setProperty("class", "BtnSecondary")
        self.btn_scanner.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_scanner.clicked.connect(self.lancer_scan_materiel)

        header_layout.addWidget(lbl_header)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_scanner)
        layout.addLayout(header_layout)

        layout.addSpacing(20)

        self.lbl_online = QLabel("EN LIGNE — EN ATTENTE DE SCAN")  # Texte par défaut
        self.lbl_online.setProperty("class", "SectionTitle")
        layout.addWidget(self.lbl_online)

        # AJOUTE DES 'self.' ICI :
        self.grid_online = QGridLayout()
        self.grid_online.setSpacing(15)
        layout.addLayout(self.grid_online)


        layout.addSpacing(30)

        lbl_offline = QLabel("HORS LIGNE")
        lbl_offline.setProperty("class", "SectionTitle")
        layout.addWidget(lbl_offline)

        grid_offline = QGridLayout()
        grid_offline.setSpacing(15)

        box_offline = self.create_boitier_btn("NI-DAQ-04", "injoignable", status="offline")
        grid_offline.addWidget(box_offline, 0, 0)
        grid_offline.setColumnStretch(1, 1)
        grid_offline.setColumnStretch(2, 1)
        layout.addLayout(grid_offline)

        layout.addStretch()

        bottom_layout = QHBoxLayout()
        self.btn_continuer = QPushButton("Continuer → Sélection voies")
        self.btn_continuer.setProperty("class", "BtnPrimary")
        self.btn_continuer.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_continuer.clicked.connect(lambda: self.switch_page(1))

        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_continuer)
        layout.addLayout(bottom_layout)

    def create_boitier_btn(self, name, desc, status):
        btn = QPushButton()
        is_online = (status == "online")
        btn.setCheckable(is_online)
        btn.setProperty("class", "BoxButton")
        btn.setMinimumHeight(60)

        if is_online:
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        else:
            btn.setEnabled(False)

        btn_layout = QHBoxLayout(btn)
        btn_layout.setContentsMargins(15, 10, 15, 10)

        dot = QLabel("●")
        dot_color = "#639922" if is_online else "#B4B2A9"
        dot.setStyleSheet(f"color: {dot_color}; font-size: 16px;")
        dot.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        info = QLabel(f"<span style='font-size: 13px; font-weight: 600; color: #1f2937;'>{name}</span><br>"
                      f"<span style='font-size: 11px; color: #6b7280;'>{desc}</span>")
        info.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        btn_layout.addWidget(dot)
        btn_layout.addWidget(info)
        btn_layout.addStretch()

        return btn

    def lancer_scan_materiel(self):
        # 1. Mise à jour de l'UI pendant le scan
        self.lbl_online.setText("EN LIGNE — RECHERCHE...")
        self.btn_scanner.setText("Scan en cours...")
        self.btn_scanner.setEnabled(False)
        QApplication.processEvents()  # Force l'affichage immédiat du texte

        # 2. Appel au backend pour chercher le vrai matériel
        succes = self.gestionnaire.initialiser_systeme()

        # 3. Nettoyage de l'ancienne grille
        # 3. NETTOYAGE SÉCURISÉ DE L'ANCIENNE GRILLE
        while self.grid_online.count():
            item = self.grid_online.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # 4. Affichage des résultats
        if succes:
            boitiers = self.gestionnaire.boitiers_detectes
            nb_trouves = len(boitiers)

            self.lbl_online.setText(f"EN LIGNE — {nb_trouves} TROUVÉ(S)")
            self.lbl_top_status.setText(f"{nb_trouves} boîtiers trouvés")

            # On crée un bouton pour chaque vrai boîtier détecté
            for index, boitier in enumerate(boitiers):
                desc = f"{boitier['modele']} · {boitier['total_voies']} voies"
                btn_box = self.create_boitier_btn(boitier['nom'], desc, status="online")
                if index == 0:
                    btn_box.setChecked(True)

                self.grid_online.addWidget(btn_box, index // 3, index % 3)

            # MAGIE : On reconstruit immédiatement la page "Sélection Voies" avec les vrais boîtiers !
            self.build_page_voies(boitiers)

        else:
            self.lbl_online.setText("EN LIGNE — 0 TROUVÉ")
            self.lbl_top_status.setText("0 boîtier")
            lbl_erreur = QLabel("Aucun matériel NI détecté. Vérifiez vos branchements.")
            lbl_erreur.setStyleSheet("color: #791F1F; font-weight: bold;")
            self.grid_online.addWidget(lbl_erreur, 0, 0)

            # On vide la page des voies puisqu'il n'y a rien
            self.build_page_voies([])

            # 5. Restauration du bouton Scanner
        self.btn_scanner.setText("Scanner")
        self.btn_scanner.setEnabled(True)




    # ==========================================
    # CONSTRUCTION: PAGE "SÉLECTION VOIES"
    # ==========================================
    def build_page_voies(self, boitiers_actifs=None):
        if boitiers_actifs is None:
            boitiers_actifs = [
                    {"nom": "NI-DAQ-01", "total_voies": 36, "voies_dispos": [f"AI{i}" for i in range(36)]},
                    {"nom": "NI-DAQ-02", "total_voies": 16, "voies_dispos": [f"AI{i}" for i in range(16)]}
                ]

        if self.page_voies.layout():
            QWidget().setLayout(self.page_voies.layout())

        main_layout = QVBoxLayout(self.page_voies)
        main_layout.setContentsMargins(40, 20, 40, 20)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 15, 0)
        scroll_layout.setSpacing(20)

        # 1. Création de notre liste magique
        self.tous_les_boutons = []

        for boitier in boitiers_actifs:
            nom_b = boitier['nom']
            lbl_titre = QLabel(f"{nom_b} · {boitier['total_voies']} voies")
            lbl_titre.setStyleSheet("font-size: 13px; font-weight: bold; color: #374151;")
            scroll_layout.addWidget(lbl_titre)

            grid_voies = QGridLayout()
            grid_voies.setSpacing(8)
            colonnes = 3

            for i, voie_nom in enumerate(boitier['voies_dispos']):
                # 2. On passe le nom du boitier ET de la voie
                btn_voie = VoieButton(nom_b, voie_nom)

                if i < 3:
                    btn_voie.set_checked(True)

                # 3. On stocke le bouton dans notre liste
                self.tous_les_boutons.append(btn_voie)

                row = i // colonnes
                col = i % colonnes
                grid_voies.addWidget(btn_voie, row, col)

            scroll_layout.addLayout(grid_voies)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # --- Boutons du bas (Fixes) ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 15, 0, 0)

        self.btn_retour = QPushButton("Retour")
        self.btn_retour.setProperty("class", "BtnSecondary")
        self.btn_retour.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_retour.clicked.connect(lambda: self.switch_page(0))

        self.btn_continuer_acq = QPushButton("Continuer → Acquisition")
        self.btn_continuer_acq.setProperty("class", "BtnPrimary")
        self.btn_continuer_acq.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # 4. MODIFICATION CRUCIALE : on appelle notre méthode pour construire le dictionnaire
        self.btn_continuer_acq.clicked.connect(self.valider_selection_voies)

        bottom_layout.addWidget(self.btn_retour)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_continuer_acq)

        main_layout.addLayout(bottom_layout)

    def valider_selection_voies(self):
        """Lit la couleur des boutons, crée le dictionnaire et passe à l'acquisition"""
        self.dico_voies = {}  # Le fameux dictionnaire pour le backend !
        total_coche = 0

        # On parcourt notre liste unique de boutons
        for btn in self.tous_les_boutons:
            if btn.is_checked:
                total_coche += 1
                # Si le boîtier n'est pas encore dans le dico, on le crée
                if btn.nom_boitier not in self.dico_voies:
                    self.dico_voies[btn.nom_boitier] = []

                # On ajoute la voie à ce boîtier
                self.dico_voies[btn.nom_boitier].append(btn.nom_voie)

        # Sécurité
        if total_coche == 0:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner au moins une voie pour continuer.")
            return

        # On met à jour le petit texte sur la page d'acquisition ("X sélectionnées")
        self.lbl_voies_val.setText(f"{total_coche} sélectionnées")

        # On passe à la page Acquisition (Index 2)
        self.switch_page(2)

        # Pour tester que ça a marché, ça va l'écrire dans la console :
        print(f"Dictionnaire prêt pour NI-DAQ : {self.dico_voies}")


    # ==========================================
    # GESTION GLOBALE
    # ==========================================
    def switch_page(self, index):
        for idx, btn in enumerate(self.nav_buttons):
            btn.setChecked(idx == index)
        self.stacked_widget.setCurrentIndex(index)

        titres = ["Détection boîtiers", "Sélection voies", "Acquisition", "Calibration", "Visualisation"]
        if index < len(titres):
            self.lbl_title.setText(f"WaveLab · {titres[index]}")

    def toggle_sidebar(self):
        if self.is_sidebar_open:
            self.animation.setStartValue(200)
            self.animation.setEndValue(0)
        else:
            self.animation.setStartValue(0)
            self.animation.setEndValue(200)

        self.animation.start()
        self.is_sidebar_open = not self.is_sidebar_open

    # ==========================================
    # CONSTRUCTION: PAGE "ACQUISITION"
    # ==========================================
    def build_page_acq(self, duree_defaut=60, freq_defaut=100, voies_actives=4):
        if self.page_acq.layout():
            QWidget().setLayout(self.page_acq.layout())

        layout = QVBoxLayout(self.page_acq)
        layout.setContentsMargins(40, 20, 40, 20)
        layout.setSpacing(20)

        # --- 1. Paramètres ---
        lbl_params = QLabel("Paramètres")
        lbl_params.setProperty("class", "SectionTitle")
        layout.addWidget(lbl_params)

        grid_params = QGridLayout()
        grid_params.setSpacing(20)

        # Durée
        lbl_duree = QLabel("DURÉE (S)")
        lbl_duree.setProperty("class", "SectionTitle")
        self.spin_duree = QSpinBox()
        self.spin_duree.setRange(1, 3600)
        self.spin_duree.setValue(duree_defaut)
        self.spin_duree.setProperty("class", "ParamBox")

        layout_duree = QVBoxLayout()
        layout_duree.addWidget(lbl_duree)
        layout_duree.addWidget(self.spin_duree)
        grid_params.addLayout(layout_duree, 0, 0)

        # Fréquence
        lbl_freq = QLabel("FRÉQUENCE (HZ)")
        lbl_freq.setProperty("class", "SectionTitle")
        self.spin_freq = QSpinBox()
        self.spin_freq.setRange(1, 150000)
        self.spin_freq.setValue(freq_defaut)
        self.spin_freq.setProperty("class", "ParamBox")

        layout_freq = QVBoxLayout()
        layout_freq.addWidget(lbl_freq)
        layout_freq.addWidget(self.spin_freq)
        grid_params.addLayout(layout_freq, 0, 1)

        # Voies actives (Lecture seule)
        lbl_voies = QLabel("VOIES ACTIVES")
        lbl_voies.setProperty("class", "SectionTitle")
        self.lbl_voies_val = QLabel(f"{voies_actives} sélectionnées")
        self.lbl_voies_val.setStyleSheet("padding: 5px; color: #6b7280;")

        layout_voies = QVBoxLayout()
        layout_voies.addWidget(lbl_voies)
        layout_voies.addWidget(self.lbl_voies_val)
        grid_params.addLayout(layout_voies, 0, 2)

        layout.addLayout(grid_params)
        layout.addSpacing(10)

        # --- 2. Contrôles et Progression ---
        ctrl_layout = QHBoxLayout()

        self.lbl_status_acq = QLabel("● En attente")
        self.lbl_status_acq.setStyleSheet("color: #6b7280; font-weight: bold; font-size: 12px;")

        self.lbl_time_acq = QLabel(f"0.0 s / {duree_defaut} s")
        self.lbl_time_acq.setStyleSheet("color: #6b7280; font-size: 11px;")

        self.btn_lancer = QPushButton("Lancer")
        self.btn_lancer.setProperty("class", "BtnPrimary")
        self.btn_lancer.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_lancer.clicked.connect(self.start_acquisition)

        self.btn_arreter = QPushButton("Arrêter")
        self.btn_arreter.setProperty("class", "BtnDanger")
        self.btn_arreter.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_arreter.clicked.connect(lambda: self.stop_acquisition(manually=True))
        self.btn_arreter.hide()  # Caché par défaut

        ctrl_layout.addWidget(self.lbl_status_acq)
        ctrl_layout.addWidget(self.lbl_time_acq)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.btn_lancer)
        ctrl_layout.addWidget(self.btn_arreter)

        layout.addLayout(ctrl_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # --- 3. Graphique PyQtGraph ---
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', '#6b7280')
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setYRange(-0.15, 0.15)  # Plage par défaut basée sur ta maquette

        # Création des courbes (ex: 3 courbes pour la simulation)
        self.curve1 = self.plot_widget.plot(pen=pg.mkPen('#185FA5', width=2), name="AI0")
        self.curve2 = self.plot_widget.plot(pen=pg.mkPen('#993556', width=2), name="AI1")
        self.curve3 = self.plot_widget.plot(pen=pg.mkPen('#854F0B', width=2), name="AI2")

        layout.addWidget(self.plot_widget, stretch=1)

        # --- 4. Bannière de succès (Cachée par défaut) ---
        self.banner_success = QFrame()
        self.banner_success.setProperty("class", "SuccessBanner")
        self.banner_success.hide()
        banner_layout = QHBoxLayout(self.banner_success)

        info_layout = QVBoxLayout()
        self.lbl_banner_title = QLabel("Acquisition terminée")
        self.lbl_banner_title.setStyleSheet("color: #27500A; font-weight: bold; font-size: 13px;")
        self.lbl_banner_sub = QLabel("Détails...")
        self.lbl_banner_sub.setProperty("class", "TextSubSuccess")
        info_layout.addWidget(self.lbl_banner_title)
        info_layout.addWidget(self.lbl_banner_sub)

        self.btn_calibrer = QPushButton("Calibrer ce fichier")
        self.btn_calibrer.setProperty("class", "BtnSecondary")
        self.btn_calibrer.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # Connexion : envoie vers la méthode de transition pour la calibration
        self.btn_calibrer.clicked.connect(self.basculer_vers_calibration)

        self.btn_enregistrer = QPushButton("Enregistrer...")
        self.btn_enregistrer.setProperty("class", "BtnSuccess")
        self.btn_enregistrer.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_enregistrer.clicked.connect(self.save_file)

        banner_layout.addLayout(info_layout)
        banner_layout.addStretch()
        banner_layout.addWidget(self.btn_calibrer)
        banner_layout.addWidget(self.btn_enregistrer)

        layout.addWidget(self.banner_success)

        # Variables pour la simulation
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_acquisition)
        self.current_time = 0.0
        self.data_x = []
        self.data_y1, self.data_y2, self.data_y3 = [], [], []

    # ==========================================
    # LOGIQUE D'ACQUISITION (TEMPS RÉEL & THREAD)
    # ==========================================
    def start_acquisition(self):
        # Réinitialisation de l'UI
        self.banner_success.hide()
        self.btn_lancer.hide()
        self.btn_arreter.show()
        self.spin_duree.setEnabled(False)
        self.spin_freq.setEnabled(False)

        self.lbl_status_acq.setText("● En cours")
        self.lbl_status_acq.setStyleSheet("color: #185FA5; font-weight: bold; font-size: 12px;")
        self.progress_bar.setValue(0)

        # 1. Envoi des paramètres au Backend
        self.target_duree = self.spin_duree.value()
        self.gestionnaire.definir_parametres(
            duree=self.target_duree,
            frequence=self.spin_freq.value()
        )

        # 2. Préparation du Graphique dynamique
        self.plot_widget.clear()
        self.courbes_actives = []
        couleurs = ['#185FA5', '#993556', '#854F0B', '#3B6D11', '#5B3256', '#212121']

        index = 0
        # On utilise le dictionnaire créé à la page précédente
        if hasattr(self, 'dico_voies'):
            for boitier, voies in self.dico_voies.items():
                for voie in voies:
                    c = self.plot_widget.plot(pen=pg.mkPen(couleurs[index % len(couleurs)], width=2),
                                              name=f"{boitier}/{voie}")
                    self.courbes_actives.append(c)
                    index += 1

        self.donnees_x_plot = []
        self.donnees_y_plot = [[] for _ in range(index)]

        # 3. Lancement du Thread avec connexion aux méthodes EXISTANTES
        self.thread_acq = AcquisitionThread(self.gestionnaire, getattr(self, 'dico_voies', {}))
        self.thread_acq.maj_graphique.connect(self.update_acquisition)  # Relie au rafraîchissement
        self.thread_acq.acquisition_terminee.connect(
            lambda succes: self.stop_acquisition(manually=False, succes=succes))  # Relie à l'arrêt
        self.thread_acq.start()

    def update_acquisition(self, nouveaux_temps, nouvelles_donnees):
        # Cette méthode est maintenant déclenchée par le Thread, avec de vraies données !
        self.donnees_x_plot.extend(nouveaux_temps)

        for i in range(len(self.courbes_actives)):
            self.donnees_y_plot[i].extend(nouvelles_donnees[i])

            # Anti-ralentissement : on ne garde que les 2000 derniers points à l'écran
            if len(self.donnees_x_plot) > 2000:
                self.donnees_y_plot[i] = self.donnees_y_plot[i][-2000:]

        if len(self.donnees_x_plot) > 2000:
            self.donnees_x_plot = self.donnees_x_plot[-2000:]

        # Mise à jour des courbes
        for i, courbe in enumerate(self.courbes_actives):
            courbe.setData(self.donnees_x_plot, self.donnees_y_plot[i])

        # Mise à jour des textes et de la barre
        if self.donnees_x_plot:
            temps_actuel = self.donnees_x_plot[-1]
            self.lbl_time_acq.setText(f"{temps_actuel:.1f} s / {self.target_duree} s")
            progress = int((temps_actuel / self.target_duree) * 100)
            self.progress_bar.setValue(min(progress, 100))

    def stop_acquisition(self, manually=False, succes=True):
        # Si c'est un arrêt manuel, on demande au thread de s'arrêter
        if manually and hasattr(self, 'thread_acq'):
            self.thread_acq.stop()
            self.thread_acq.wait()  # On attend que NI-DAQmx se coupe proprement

        # Restauration de l'UI
        self.btn_arreter.hide()
        self.btn_lancer.show()
        self.spin_duree.setEnabled(True)
        self.spin_freq.setEnabled(True)

        if manually:
            self.lbl_status_acq.setText("● Arrêtée")
            self.lbl_status_acq.setStyleSheet("color: #791F1F; font-weight: bold; font-size: 12px;")
            self.lbl_banner_title.setText("Acquisition arrêtée manuellement")
        elif succes:
            self.lbl_status_acq.setText("● Terminée")
            self.lbl_status_acq.setStyleSheet("color: #27500A; font-weight: bold; font-size: 12px;")
            self.lbl_banner_title.setText("Acquisition terminée avec succès")
            self.progress_bar.setValue(100)
            self.lbl_time_acq.setText(f"{self.target_duree:.1f} s / {self.target_duree} s")
        else:
            self.lbl_status_acq.setText("● Échec")
            self.lbl_status_acq.setStyleSheet("color: #791F1F; font-weight: bold; font-size: 12px;")
            self.lbl_banner_title.setText("Erreur matérielle NI-DAQmx")

        # Mise à jour de la bannière finale
        freq = self.spin_freq.value()
        voies = len(getattr(self, 'courbes_actives', []))
        temps = self.donnees_x_plot[-1] if hasattr(self, 'donnees_x_plot') and self.donnees_x_plot else 0
        pts = int(temps * freq)
        self.lbl_banner_sub.setText(f"{temps:.1f} s · {freq} Hz · {voies} voies · {pts} pts")

        self.banner_success.show()

    '''def save_file(self):
        import os

        # On récupère le nom par défaut du backend
        nom_defaut = self.gestionnaire.parametres.get("nom_fichier", "donnees_brutes.csv")

        # Ouvre l'explorateur de fichiers natif de l'OS
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer les données d'acquisition",
            nom_defaut,
            "Fichiers CSV (*.csv)"
        )

        if file_name:
            # 1. Séparer le dossier et le nom du fichier
            dossier = os.path.dirname(file_name)
            nom_fichier = os.path.basename(file_name)

            # 2. Mettre à jour le gestionnaire
            self.gestionnaire.parametres["dossier_sortie"] = dossier
            self.gestionnaire.parametres["nom_fichier"] = nom_fichier

            # 3. Lancer la sauvegarde
            try:
                # Appelle la méthode de sauvegarde du backend
                if hasattr(self.gestionnaire, 'sauvegarder_brut_csv'):
                    self.gestionnaire.sauvegarder_brut_csv()
                else:
                    self.gestionnaire.sauvegarder_csv()

                QMessageBox.information(self, "Succès", f"Fichier enregistré avec succès sous :\n{file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible de sauvegarder le fichier :\n{e}")
        '''

    def save_file(self):
        import os
        import shutil  # Bibliothèque Python pour copier/déplacer des fichiers

        # Le fichier qui a été créé "au vol" pendant l'acquisition
        chemin_auto_sauvegarde = os.path.join(
            self.gestionnaire.parametres.get("dossier_sortie", "."),
            self.gestionnaire.parametres.get("nom_fichier", "donnees.csv")
        )

        # On vérifie que le fichier a bien été créé
        if not os.path.exists(chemin_auto_sauvegarde):
            QMessageBox.critical(self, "Erreur", "Le fichier temporaire d'acquisition est introuvable.")
            return

        # On demande où l'utilisateur veut le garder définitivement
        nom_defaut = self.gestionnaire.parametres.get("nom_fichier", "donnees_brutes.csv")
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer les données d'acquisition",
            nom_defaut,
            "Fichiers CSV (*.csv)"
        )

        if file_name:
            try:
                # On copie le gros fichier vers son emplacement final
                shutil.copy(chemin_auto_sauvegarde, file_name)

                # (Optionnel) On peut mettre à jour le gestionnaire pour la suite
                self.gestionnaire.parametres["dossier_sortie"] = os.path.dirname(file_name)
                self.gestionnaire.parametres["nom_fichier"] = os.path.basename(file_name)

                QMessageBox.information(self, "Succès", f"Fichier enregistré avec succès sous :\n{file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible de copier le fichier :\n{e}")
        # ==========================================
        # CONSTRUCTION: PAGE "CALIBRATION"
        # ==========================================
    def build_page_calib(self):
            self.page_calib = QWidget()
            layout = QVBoxLayout(self.page_calib)
            layout.setContentsMargins(40, 20, 40, 20)
            layout.setSpacing(20)

            # --- Section : Fichier source ---
            lbl_source = QLabel("Fichier source")
            lbl_source.setStyleSheet("font-size: 14px; font-weight: bold;")
            layout.addWidget(lbl_source)

            # 1. Zone de dépôt (Bouton géant)
            self.btn_dropzone = QPushButton(
                "Glisser un fichier ou cliquer pour importer\n\n.csv · .mat · .txt — données brutes acquises")
            self.btn_dropzone.setProperty("class", "DropZone")
            self.btn_dropzone.setMinimumHeight(120)
            self.btn_dropzone.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.btn_dropzone.clicked.connect(self.simulate_file_import)
            layout.addWidget(self.btn_dropzone)

            # 2. Bannière de fichier chargé (Modifiée pour inclure le bouton Parcourir)
            self.banner_file = QFrame()
            self.banner_file.setProperty("class", "FileBanner")
            self.banner_file.hide()
            banner_layout = QHBoxLayout(self.banner_file)  # <-- Modifié en Horizontal

            info_layout = QVBoxLayout()
            self.lbl_filename = QLabel("nom_du_fichier.csv")
            self.lbl_filename.setStyleSheet("color: #0C447C; font-weight: bold; font-size: 13px;")
            self.lbl_fileinfo = QLabel("X lignes · Y colonnes · chargé")
            self.lbl_fileinfo.setStyleSheet("color: #185FA5; font-size: 11px;")

            info_layout.addWidget(self.lbl_filename)
            info_layout.addWidget(self.lbl_fileinfo)

            # Le nouveau bouton Parcourir
            self.btn_parcourir = QPushButton("Parcourir...")
            self.btn_parcourir.setProperty("class", "BtnSecondary")
            self.btn_parcourir.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.btn_parcourir.clicked.connect(self.simulate_file_import)  # Rappelle la même fonction

            banner_layout.addLayout(info_layout)
            banner_layout.addStretch()
            banner_layout.addWidget(self.btn_parcourir)  # Ajout du bouton à droite

            layout.addWidget(self.banner_file)

            # --- Section : Tableau de calibration ---
            self.calib_container = QWidget()
            self.calib_container.hide()
            self.calib_layout = QVBoxLayout(self.calib_container)
            self.calib_layout.setContentsMargins(0, 20, 0, 0)

            lbl_def = QLabel("Définition des capteurs par voie")
            lbl_def.setStyleSheet("font-size: 14px; font-weight: bold;")
            self.calib_layout.addWidget(lbl_def)

            # En-têtes du tableau (Sans Gain ni Offset)
            headers_layout = QGridLayout()
            headers = ["VOIE", "TYPE", "UNITÉ", "VALEUR LUE"]
            for col, text in enumerate(headers):
                lbl = QLabel(text)
                lbl.setProperty("class", "SectionTitle")
                headers_layout.addWidget(lbl, 0, col)

            headers_layout.setColumnStretch(1, 2)
            self.calib_layout.addLayout(headers_layout)

            # Layout pour les lignes dynamiques
            self.rows_layout = QVBoxLayout()
            self.rows_layout.setSpacing(15)
            self.calib_layout.addLayout(self.rows_layout)

            # Boutons d'action
            bottom_layout = QHBoxLayout()
            bottom_layout.setContentsMargins(0, 20, 0, 0)

            self.btn_visu = QPushButton("Visualiser calibré")
            self.btn_visu.setProperty("class", "BtnSecondary")
            self.btn_visu.clicked.connect(self.process_and_visualize)  # Utilisation de la méthode de pont

            self.btn_save_calib = QPushButton("Enregistrer fichier calibré...")
            self.btn_save_calib.setProperty("class", "BtnSuccess")
            self.btn_save_calib.clicked.connect(self.save_calibrated_file)

            bottom_layout.addStretch()
            bottom_layout.addWidget(self.btn_visu)
            bottom_layout.addWidget(self.btn_save_calib)
            self.calib_layout.addLayout(bottom_layout)

            layout.addWidget(self.calib_container)
            layout.addStretch()

            self.dynamic_tags = {}
            self.dynamic_units = {}

        # ==========================================
        # LOGIQUE DE CALIBRATION
        # ==========================================

    def simulate_file_import(self):
        # Ouvre un explorateur de fichiers
        file_name, _ = QFileDialog.getOpenFileName(self, "Importer un fichier d'acquisition", "",
                                                   "Fichiers CSV (*.csv);;Tous les fichiers (*)")

        if file_name:
            import os
            base_name = os.path.basename(file_name)

            # Mise à jour de l'UI
            self.btn_dropzone.hide()
            self.lbl_filename.setText(base_name)
            self.lbl_fileinfo.setText("24 000 lignes · 4 colonnes · chargé")  # Valeurs simulées
            self.banner_file.show()

            # Simulation : le fichier contient 4 voies
            colonnes_detectees = ["AI0", "AI1", "AI2", "D2-AI0"]
            self.populate_calibration_table(colonnes_detectees)

            self.calib_container.show()

    def populate_calibration_table(self, colonnes):
        # Nettoie les anciennes lignes si on recharge un fichier
        for i in reversed(range(self.rows_layout.count())):
            widget = self.rows_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        self.dynamic_tags.clear()
        self.dynamic_units.clear()

        # Options de capteurs
        types_capteurs = ["Pression", "Accélération", "Température", "Débit", "Brut"]

        for row_index, voie in enumerate(colonnes):
            row_widget = QWidget()
            row_grid = QGridLayout(row_widget)
            row_grid.setContentsMargins(0, 0, 0, 0)

            # 1. Nom de la voie
            lbl_voie = QLabel(voie)
            lbl_voie.setStyleSheet("font-weight: bold; font-size: 12px;")
            row_grid.addWidget(lbl_voie, 0, 0)

            # 2. Type (Menu déroulant + Tag)
            type_layout = QVBoxLayout()
            combo_type = QComboBox()
            combo_type.addItems(types_capteurs)

            lbl_tag = QLabel("pression")
            lbl_tag.setProperty("class", "TagPression")
            lbl_tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_tag.setFixedWidth(70)

            type_layout.addWidget(combo_type)
            type_layout.addWidget(lbl_tag)
            row_grid.addLayout(type_layout, 0, 1)

            # 5. Unité
            lbl_unite = QLabel("Pa")
            lbl_unite.setStyleSheet("font-family: monospace; color: #4b5563;")
            row_grid.addWidget(lbl_unite, 0, 2)

            # 6. Valeur simulée
            lbl_valeur = QLabel("0.0")
            lbl_valeur.setStyleSheet("color: #185FA5; font-family: monospace;")
            row_grid.addWidget(lbl_valeur, 0, 3)

            # Sauvegarde des références pour les mettre à jour lors du changement
            self.dynamic_tags[row_index] = lbl_tag
            self.dynamic_units[row_index] = lbl_unite

            # Connexion du signal de changement du menu déroulant
            # L'utilisation de lambda avec default arg (idx=row_index) est cruciale ici en Python !
            combo_type.currentIndexChanged.connect(
                lambda current_text, idx=row_index, combo=combo_type: self.update_row_type(idx, combo.currentText()))

            # Initialisation aléatoire pour simuler ta maquette
            if "AI1" in voie:
                combo_type.setCurrentText("Accélération")
            elif "AI2" in voie:
                combo_type.setCurrentText("Température")
            elif "D2" in voie:
                combo_type.setCurrentText("Débit")
            else:
                combo_type.setCurrentText("Pression")

            row_grid.setColumnStretch(1, 2)
            self.rows_layout.addWidget(row_widget)

    def update_row_type(self, row_index, selected_type):
        """Met à jour le tag de couleur et l'unité quand le menu déroulant change"""
        tag = self.dynamic_tags[row_index]
        unite = self.dynamic_units[row_index]

        if selected_type == "Pression":
            tag.setText("pression")
            tag.setProperty("class", "TagPression")
            unite.setText("Pa")
        elif selected_type == "Accélération":
            tag.setText("accél.")
            tag.setProperty("class", "TagAccel")
            unite.setText("m/s²")
        elif selected_type == "Température":
            tag.setText("temp.")
            tag.setProperty("class", "TagTemp")
            unite.setText("°C")
        elif selected_type == "Débit":
            tag.setText("débit")
            tag.setProperty("class", "TagDebit")
            unite.setText("L/min")
        else:
            tag.setText("brut")
            tag.setProperty("class", "TagBrut")
            unite.setText("V")

        # Force PyQt à recharger le CSS du tag pour appliquer la nouvelle couleur
        tag.style().unpolish(tag)
        tag.style().polish(tag)

    def save_calibrated_file(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Enregistrer fichier calibré", "", "Fichiers CSV (*.csv)")
        if file_name:
            QMessageBox.information(self, "Succès", "Fichier calibré enregistré avec succès.")

    # ==========================================
    # CONSTRUCTION: PAGE "VISUALISATION"
    # ==========================================
    def build_page_visu(self):
        self.page_visu = QWidget()
        layout = QVBoxLayout(self.page_visu)
        layout.setContentsMargins(40, 20, 40, 20)
        layout.setSpacing(15)

        # --- 1. En-tête et Menu déroulant ---
        header_layout = QHBoxLayout()
        lbl_title = QLabel("Visualisation des données")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.combo_visu_voies = QComboBox()
        self.combo_visu_voies.setMinimumWidth(150)
        # Texte par défaut tant qu'aucune donnée n'est chargée
        self.combo_visu_voies.addItem("Aucune donnée chargée")
        self.combo_visu_voies.currentTextChanged.connect(self.filter_visu_channels)

        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.combo_visu_voies)
        layout.addLayout(header_layout)

        # --- 2. Onglets (Brut et Calibré UNIQUEMENT) ---
        tabs_layout = QHBoxLayout()
        self.btn_tab_brut = QPushButton("Brut")
        self.btn_tab_calib = QPushButton("Calibré")

        for btn in [self.btn_tab_brut, self.btn_tab_calib]:
            btn.setCheckable(True)
            btn.setProperty("class", "VisuTab")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            tabs_layout.addWidget(btn)

        self.btn_tab_brut.setChecked(True)
        self.btn_tab_brut.clicked.connect(lambda: self.switch_visu_tab("Brut"))
        self.btn_tab_calib.clicked.connect(lambda: self.switch_visu_tab("Calibré"))

        tabs_layout.addStretch()
        layout.addLayout(tabs_layout)

        # --- 3. Métriques ---
        metrics_layout = QGridLayout()
        metrics_layout.setSpacing(10)
        self.lbl_metric_hs = self.create_metric_box("HS", "0.000", "m", metrics_layout, 0)
        self.lbl_metric_tp = self.create_metric_box("TP", "0.00", "s", metrics_layout, 1)
        self.lbl_metric_hmax = self.create_metric_box("HMAX", "0.000", "m", metrics_layout, 2)
        self.lbl_metric_duree = self.create_metric_box("DURÉE", "0", "s", metrics_layout, 3)
        layout.addLayout(metrics_layout)

        # --- 4. Graphique PyQtGraph ---
        self.visu_plot = pg.PlotWidget()
        self.visu_plot.setBackground('w')
        self.visu_plot.showGrid(x=True, y=True, alpha=0.3)
        self.visu_plot.addLegend(offset=(10, 10))
        layout.addWidget(self.visu_plot, stretch=1)

        # Variables pour stocker les données actives
        self.visu_curves = {}
        self.visu_current_data = {}


    def switch_visu_tab(self, mode):
        """Gère le clic sur les onglets Brut / Calibré"""
        self.btn_tab_brut.setChecked(mode == "Brut")
        self.btn_tab_calib.setChecked(mode == "Calibré")

        print(f"Demande d'affichage des données : {mode}")
        # Ici, ton futur code métier pourra rafraîchir le graphique
        # en passant les données brutes ou calibrées selon le mode cliqué.


    def create_metric_box(self, label, val, unit, layout, col):
        """Fonction utilitaire pour générer les encarts de métriques"""
        box = QFrame()
        box.setProperty("class", "MetricBox")
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(15, 10, 15, 10)

        lbl_title = QLabel(label)
        lbl_title.setProperty("class", "MetricLabel")

        # Utilisation de HTML pour avoir un grand chiffre et une petite unité
        lbl_val = QLabel(
            f"<span style='font-size: 18px; font-weight: bold; font-family: monospace;'>{val}</span> <span style='font-size: 11px; color: #6b7280;'>{unit}</span>")

        box_layout.addWidget(lbl_title)
        box_layout.addWidget(lbl_val)
        layout.addWidget(box, 0, col)

        return lbl_val  # On retourne le label pour pouvoir le mettre à jour plus tard

        # ==========================================
        # LOGIQUE DE GESTION DES DONNÉES
        # ==========================================


    def load_visu_data(self, time_array, channels_dict, metrics_dict):
        """
        MÉTHODE PARAMÉTRABLE À APPELER DEPUIS TON CODE MÉTIER.

        - time_array: Liste ou array NumPy des valeurs X (temps ou fréquences)
        - channels_dict: Dictionnaire contenant les données Y par voie, couleurs et noms
        - metrics_dict: Dictionnaire des valeurs à afficher en haut
        """
        self.visu_current_data = channels_dict

        # 1. Mise à jour des métriques
        self.lbl_metric_hs.setText(
            f"<span style='font-size: 18px; font-weight: bold; font-family: monospace;'>{metrics_dict.get('HS', '0')}</span> <span style='font-size: 11px; color: #6b7280;'>m</span>")
        self.lbl_metric_tp.setText(
            f"<span style='font-size: 18px; font-weight: bold; font-family: monospace;'>{metrics_dict.get('TP', '0')}</span> <span style='font-size: 11px; color: #6b7280;'>s</span>")
        self.lbl_metric_hmax.setText(
            f"<span style='font-size: 18px; font-weight: bold; font-family: monospace;'>{metrics_dict.get('HMAX', '0')}</span> <span style='font-size: 11px; color: #6b7280;'>m</span>")
        self.lbl_metric_duree.setText(
            f"<span style='font-size: 18px; font-weight: bold; font-family: monospace;'>{metrics_dict.get('DUREE', '0')}</span> <span style='font-size: 11px; color: #6b7280;'>s</span>")

        # 2. Mise à jour du menu déroulant (sans déclencher le signal)
        self.combo_visu_voies.blockSignals(True)
        self.combo_visu_voies.clear()
        self.combo_visu_voies.addItem("Toutes les voies")
        for key, info in channels_dict.items():
            self.combo_visu_voies.addItem(info.get('name', key))
        self.combo_visu_voies.blockSignals(False)

        # 3. Dessin des courbes
        self.visu_plot.clear()  # Nettoie le graphique
        self.visu_curves.clear()

        for key, info in self.visu_current_data.items():
            name = info.get("name", key)
            curve = self.visu_plot.plot(
                time_array,
                info["data"],
                pen=pg.mkPen(info.get("color", "#000000"), width=1.5),
                name=name
            )
            self.visu_curves[key] = curve  # On stocke l'objet courbe pour pouvoir le cacher/afficher

        self.combo_visu_voies.setCurrentIndex(0)  # Affiche toutes les voies par défaut


    def filter_visu_channels(self, selected_text):
        """Affiche ou cache les courbes en fonction du menu déroulant"""
        for key, curve in self.visu_curves.items():
            name = self.visu_current_data[key].get("name", key)

            # La magie est ici : .setVisible() est instantané, pas besoin de recalculer !
            if selected_text == "Toutes les voies" or selected_text == name:
                curve.setVisible(True)
            else:
                curve.setVisible(False)


    def switch_visu_tab(self, mode):
        """Gère le clic sur les onglets Brut / Calibré / FFT"""
        self.btn_tab_brut.setChecked(mode == "Brut")
        self.btn_tab_calib.setChecked(mode == "Calibré")
        self.btn_tab_fft.setChecked(mode == "FFT")

        # Ici, tu pourras appeler à nouveau load_visu_data() avec les données
        # correspondantes au mode cliqué (par ex. les données issues de la FFT)
        print(f"Demande d'affichage des données : {mode}")


    def process_and_visualize(self):
        """
        Cette méthode est appelée quand on clique sur 'Visualiser calibré'.
        Elle lit le fichier, calcule les données, et les envoie à la page Visu.
        """
        import numpy as np  # Importé ici temporairement pour la simulation

        # 1. Dans ton vrai code, tu liras ton fichier CSV ici...
        # Pour l'instant, on simule les tableaux de données
        temps = np.linspace(0, 10, 500)

        # 2. Tu construis ton dictionnaire avec les données Brutes ou Calibrées
        donnees = {
            "AI0": {"data": np.sin(temps) * 0.14, "color": "#185FA5", "name": "AI0 - Pression"},
            "AI1": {"data": np.cos(temps * 1.5) * 0.08, "color": "#993556", "name": "AI1 - Accélération"},
            "D2": {"data": np.sin(temps * 0.5) * 0.04, "color": "#3B6D11", "name": "D2 - Débit"}
        }
        metriques = {"HS": "0.142", "TP": "1.84", "HMAX": "0.241", "DUREE": "60"}

        # 3. On injecte les données dans la page de Visualisation
        self.load_visu_data(temps, donnees, metriques)

        # 4. Enfin, on bascule visuellement sur la page Visualisation (Index 4)
        self.switch_page(4)

    def basculer_vers_calibration(self):
        """Prend les voies acquises, prépare le tableau de calibration et change de page"""

        # Récupère les voies qu'on vient juste de lire
        if hasattr(self.gestionnaire, 'chemins_voies_actives') and self.gestionnaire.chemins_voies_actives:
            voies_a_calibrer = self.gestionnaire.chemins_voies_actives
        else:
            # Sécurité au cas où on teste l'interface sans matériel
            voies_a_calibrer = ["AI0", "AI1", "AI2"]

            # 1. On masque la zone de dépôt (Drag & Drop)
        self.btn_dropzone.hide()

        # 2. On affiche la bannière bleue avec le nom du fichier
        self.lbl_filename.setText(self.gestionnaire.parametres.get("nom_fichier", "donnees.csv"))

        freq = self.spin_freq.value()
        temps = self.donnees_x_plot[-1] if hasattr(self, 'donnees_x_plot') and self.donnees_x_plot else 0
        pts = int(temps * freq)
        self.lbl_fileinfo.setText(f"{pts} lignes · {len(voies_a_calibrer)} colonnes · Données directes")
        self.banner_file.show()

        # 3. On génère dynamiquement le tableau avec les vraies voies
        self.populate_calibration_table(voies_a_calibrer)
        self.calib_container.show()

        # 4. On bascule sur la page Calibration (Index 3)
        self.switch_page(3)


    def au_clic_detection(self):
        try:
            self.gestionnaire = GestionnaireKistler()
            if self.gestionnaire.initialiser_systeme():
                QMessageBox.information(self, "Succès", "Boîtier Kistler détecté automatiquement et prêt !")
                # Tu peux ici charger tes listes de voies comme tu le faisais avec le NI

        except BoitierIntrouvableError as e:
            # Affiche le message explicatif dans une belle pop-up Windows
            QMessageBox.critical(self, "Erreur de Détection", str(e))


    def au_clic_lancer_mesure(self):
        # Idéalement exécuté dans un QThread pour ne pas figer la fenêtre
        try:
            voies_choisies = {f"Kistler_LabAmp_5294123": ["Kistler_LabAmp_5294123/Ch1"]}
            self.gestionnaire.lancer_acquisition(dictionnaire_voies=voies_choisies, callback_maj=self.update_graph)

        except (TimeoutReseauError, ConnexionInterrompueError) as e:
            QMessageBox.critical(self, "Coupure Réseau", str(e))
        except KistlerError as e:
            QMessageBox.critical(self, "Erreur Critique", f"Un problème est survenu : {str(e)}")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WaveLabApp()
    window.show()
    sys.exit(app.exec())
