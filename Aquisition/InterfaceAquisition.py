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


# ==========================================
# 1. CLASSE PERSONNALISÉE POUR LES VOIES
# ==========================================
class VoieButton(QFrame):
    def __init__(self, nom_voie, parent=None):
        super().__init__(parent)

        # CRUCIAL : Force PyQt à dessiner le fond défini dans le CSS
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.nom_voie = nom_voie
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
"""


# ==========================================
# 3. APPLICATION PRINCIPALE
# ==========================================
class WaveLabApp(QMainWindow):
    def __init__(self):
        super().__init__()
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
        self.build_page_detect()

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
        self.build_page_voies()
        self.build_page_acq()
        self.build_page_calib()

        self.stacked_widget.addWidget(self.page_detect)
        self.stacked_widget.addWidget(self.page_voies)
        self.stacked_widget.addWidget(self.page_acq)
        self.stacked_widget.addWidget(self.page_calib)

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
        self.btn_scanner.clicked.connect(self.simulate_scan)

        header_layout.addWidget(lbl_header)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_scanner)
        layout.addLayout(header_layout)

        layout.addSpacing(20)

        self.lbl_online = QLabel("EN LIGNE — 3 TROUVÉS")
        self.lbl_online.setProperty("class", "SectionTitle")
        layout.addWidget(self.lbl_online)

        grid_online = QGridLayout()
        grid_online.setSpacing(15)

        self.box1 = self.create_boitier_btn("NI-DAQ-01", "192.168.1.10 · 8 voies", status="online")
        self.box2 = self.create_boitier_btn("NI-DAQ-02", "192.168.1.11 · 8 voies", status="online")
        self.box3 = self.create_boitier_btn("NI-DAQ-03", "192.168.1.12 · 4 voies", status="online")

        self.box1.setChecked(True)
        self.box2.setChecked(True)

        grid_online.addWidget(self.box1, 0, 0)
        grid_online.addWidget(self.box2, 0, 1)
        grid_online.addWidget(self.box3, 0, 2)
        layout.addLayout(grid_online)

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

    def simulate_scan(self):
        self.lbl_online.setText("EN LIGNE — RECHERCHE...")
        self.btn_scanner.setText("Scan en cours...")
        self.btn_scanner.setEnabled(False)

        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1500, self.finish_scan)

    def finish_scan(self):
        self.lbl_online.setText("EN LIGNE — 3 TROUVÉS")
        self.btn_scanner.setText("Scanner")
        self.btn_scanner.setEnabled(True)

    # ==========================================
    # CONSTRUCTION: PAGE "SÉLECTION VOIES"
    # ==========================================
    def build_page_voies(self, boitiers_actifs=None):
        if boitiers_actifs is None:
            # Génération d'un exemple avec 36 voies pour tester le Scroll
            boitiers_actifs = [
                {"nom": "NI-DAQ-01", "total_voies": 36, "voies_dispos": [f"AI{i}" for i in range(36)]},
                {"nom": "NI-DAQ-02", "total_voies": 16, "voies_dispos": [f"AI{i}" for i in range(16)]}
            ]

        if self.page_voies.layout():
            QWidget().setLayout(self.page_voies.layout())

        main_layout = QVBoxLayout(self.page_voies)
        main_layout.setContentsMargins(40, 20, 40, 20)

        # --- NOUVEAU : Le ScrollArea intégré spécifiquement à cette page ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 15, 0)
        scroll_layout.setSpacing(20)

        for boitier in boitiers_actifs:
            lbl_titre = QLabel(f"{boitier['nom']} · {boitier['total_voies']} voies")
            lbl_titre.setStyleSheet("font-size: 13px; font-weight: bold; color: #374151;")
            scroll_layout.addWidget(lbl_titre)

            grid_voies = QGridLayout()
            grid_voies.setSpacing(8)
            colonnes = 3

            for i, voie_nom in enumerate(boitier['voies_dispos']):
                btn_voie = VoieButton(voie_nom)  # Utilise la classe personnalisée !

                if i < 3:
                    btn_voie.set_checked(True)

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
        self.btn_continuer_acq.clicked.connect(lambda: self.switch_page(2))

        bottom_layout.addWidget(self.btn_retour)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_continuer_acq)

        main_layout.addLayout(bottom_layout)

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
        self.spin_freq.setRange(1, 10000)
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
    # LOGIQUE DE SIMULATION D'ACQUISITION
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

        # Réinitialisation des données
        self.current_time = 0.0
        self.data_x.clear()
        self.data_y1.clear();
        self.data_y2.clear();
        self.data_y3.clear()

        self.target_duree = self.spin_duree.value()

        # Démarrage du chronomètre (mise à jour toutes les 50ms)
        self.timer.start(50)

    def update_acquisition(self):
        # Simulation du temps qui passe
        self.current_time += 0.05

        # Mise à jour des labels et barre
        self.lbl_time_acq.setText(f"{self.current_time:.1f} s / {self.target_duree} s")
        progress = int((self.current_time / self.target_duree) * 100)
        self.progress_bar.setValue(progress)

        # Génération de données sinusoïdales fictives
        self.data_x.append(self.current_time)
        self.data_y1.append(0.08 * math.sin(2 * math.pi * 0.5 * self.current_time))
        self.data_y2.append(0.04 * math.sin(2 * math.pi * 0.8 * self.current_time + 1))
        self.data_y3.append(0.06 * math.sin(2 * math.pi * 0.3 * self.current_time + 2))

        # On ne garde que les 100 derniers points pour l'effet "temps réel" qui défile
        if len(self.data_x) > 100:
            self.data_x.pop(0)
            self.data_y1.pop(0)
            self.data_y2.pop(0)
            self.data_y3.pop(0)

        self.curve1.setData(self.data_x, self.data_y1)
        self.curve2.setData(self.data_x, self.data_y2)
        self.curve3.setData(self.data_x, self.data_y3)

        # Vérification de fin
        if self.current_time >= self.target_duree:
            self.stop_acquisition(manually=False)

    def stop_acquisition(self, manually=False):
        self.timer.stop()

        # Restauration de l'UI
        self.btn_arreter.hide()
        self.btn_lancer.show()
        self.spin_duree.setEnabled(True)
        self.spin_freq.setEnabled(True)

        # Mise à jour des statuts
        if manually:
            self.lbl_status_acq.setText("● Arrêtée")
            self.lbl_status_acq.setStyleSheet("color: #791F1F; font-weight: bold; font-size: 12px;")
            self.lbl_banner_title.setText("Acquisition arrêtée manuellement")
        else:
            self.lbl_status_acq.setText("● Terminée")
            self.lbl_status_acq.setStyleSheet("color: #27500A; font-weight: bold; font-size: 12px;")
            self.lbl_banner_title.setText("Acquisition terminée avec succès")
            self.progress_bar.setValue(100)
            self.lbl_time_acq.setText(f"{self.target_duree:.1f} s / {self.target_duree} s")

        # Préparation du texte de la bannière
        freq = self.spin_freq.value()
        voies = 4  # Paramètre d'exemple
        pts = int(self.current_time * freq)
        self.lbl_banner_sub.setText(f"{self.current_time:.1f} s · {freq} Hz · {voies} voies · {pts} pts")

        # Affichage de la bannière
        self.banner_success.show()

    def save_file(self):
        # Ouvre l'explorateur de fichiers natif de l'OS
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer les données d'acquisition",
            "",
            "Fichiers CSV (*.csv);;Fichiers Texte (*.txt);;Tous les fichiers (*)"
        )

        if file_name:
            # Ici tu mettras la vraie logique d'écriture dans le fichier
            QMessageBox.information(self, "Succès", f"Fichier enregistré sous :\n{file_name}")

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

        # 2. Bannière de fichier chargé (Cachée par défaut)
        self.banner_file = QFrame()
        self.banner_file.setProperty("class", "FileBanner")
        self.banner_file.hide()
        banner_layout = QVBoxLayout(self.banner_file)

        self.lbl_filename = QLabel("nom_du_fichier.csv")
        self.lbl_filename.setStyleSheet("color: #0C447C; font-weight: bold; font-size: 13px;")
        self.lbl_fileinfo = QLabel("X lignes · Y colonnes · chargé")
        self.lbl_fileinfo.setStyleSheet("color: #185FA5; font-size: 11px;")

        banner_layout.addWidget(self.lbl_filename)
        banner_layout.addWidget(self.lbl_fileinfo)
        layout.addWidget(self.banner_file)

        # --- Section : Tableau de calibration (Caché par défaut) ---
        self.calib_container = QWidget()
        self.calib_container.hide()
        self.calib_layout = QVBoxLayout(self.calib_container)
        self.calib_layout.setContentsMargins(0, 20, 0, 0)

        lbl_def = QLabel("Définition des capteurs par voie")
        lbl_def.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.calib_layout.addWidget(lbl_def)

        # En-têtes du tableau
        headers_layout = QGridLayout()
        headers = ["VOIE", "TYPE", "UNITÉ", "VALEUR"]
        for col, text in enumerate(headers):
            lbl = QLabel(text)
            lbl.setProperty("class", "SectionTitle")
            headers_layout.addWidget(lbl, 0, col)

        headers_layout.setColumnStretch(1, 2)  # La colonne "Type" est plus large
        self.calib_layout.addLayout(headers_layout)

        # Layout qui contiendra les lignes dynamiques
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(15)
        self.calib_layout.addLayout(self.rows_layout)

        # Boutons d'action en bas
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 20, 0, 0)

        self.btn_visu = QPushButton("Visualiser calibré")
        self.btn_visu.setProperty("class", "BtnSecondary")
        self.btn_visu.clicked.connect(lambda: self.switch_page(4))  # Va à la page Visu

        self.btn_save_calib = QPushButton("Enregistrer fichier calibré...")
        self.btn_save_calib.setProperty("class", "BtnSuccess")
        self.btn_save_calib.clicked.connect(self.save_calibrated_file)

        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_visu)
        bottom_layout.addWidget(self.btn_save_calib)
        self.calib_layout.addLayout(bottom_layout)

        layout.addWidget(self.calib_container)
        layout.addStretch()

        # Dictionnaires pour stocker les références des UI dynamiques
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WaveLabApp()
    window.show()
    sys.exit(app.exec())