import sys
import os
import csv
import math
import pyqtgraph as pg
import ctypes

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                             QVBoxLayout, QPushButton, QLabel, QStackedWidget,
                             QFrame, QGridLayout, QScrollArea, QSpinBox, QProgressBar, QFileDialog, QMessageBox,
                             QComboBox, QLineEdit, QCheckBox)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QCursor

from Aquisition.AquisitionThread import AcquisitionThread
from GestionnaireNI import GestionnaireNI
from GestionnaireKistler import (
    GestionnaireKistler, BoitierIntrouvableError,
    TimeoutReseauError, ConnexionInterrompueError, KistlerError)
from GestionnairePrincipal import GestionnairePrincipal
# Dictionnaire de configuration par type de capteur
# Clé : nom affiché dans le ComboBox
# Valeur : label p1, label p2, défaut p1, défaut p2, unité, formule, description formule
CAPTEURS_CONFIG = {
    "Pression": {
        "p1_label": "Pleine Échelle PE (bar)",
        "p2_label": "Tension zéro V_zéro (V)",
        "p1_default": 10.0,
        "p2_default": 0.0,
        "unite"     : "bar",
        # P = PE × (V - V_ref) / (V_max - V_ref)
        # V_max = 10V (plage capteur 0-10V) ou 5V (4-20mA → 1-5V)
        "formule"   : lambda V, p1, p2: p1 * (V - p2) / (10.0 - p2) if (10.0 - p2) != 0 else 0.0,
        "formule_str": "PE × (V - V_ref) / (10 - V_ref)"
    },
    "Force": {
        "p1_label"  :  "Capacité Nominale CN (N)",
        "p2_label"  : "Sensibilité S (mV/V)",
        "p1_default": 1000.0,
        "p2_default": 2.0,
        "unite"     : "N",
        # F = CN × V / (S/1000 × V_exc)
        # V_exc = 10V (tension d'excitation du pont, fixe)
        "formule"   : lambda V, p1, p2: p1 * V / ((p2 / 1000.0) * 10.0) if p2 != 0 else 0.0,
        "formule_str": "CN × V / (S/1000 × 10)"
    },
    "Accélération": {
        "p1_label"  : "Sensibilité S (mV/g)",
        "p2_label"  : "Tension de biais V_biais (V)",
        "p1_default": 100.0,
        "p2_default": 0.0,
        "unite"     : "m/s²",
        # A = (V - V_bias) × 1000/S × 9.81
        # V_bias : tension DC de repos du capteur IEPE (éliminée par couplage AC)
        "formule"   : lambda V, p1, p2: (V - p2) * 1000.0 / p1 * 9.81 if p1 != 0 else 0.0,
        "formule_str": "(V - V_bias) × 1000/S × 9.81"
    },
    "Vitesse": {
        "p1_label"  :"Sensibilité S (mV/(m/s))",
        "p2_label"  : "Tension offset V_offset (V)",
        "p1_default": 500.0,
        "p2_default": 0.0,
        "unite"     : "m/s",
        # v = (V - V_0) / (S/1000)
        # V_0 : tension à vitesse nulle (offset)
        "formule"   : lambda V, p1, p2: (V - p2) / (p1 / 1000.0) if p1 != 0 else 0.0,
        "formule_str": "(V - V_0) / (S / 1000)"
    },
    "Sonde": {
        "p1_label"  : "Gain conditionneur G (°C/V)",
        "p2_label"  : "Température zéro T_zéro (°C)",
        "p1_default": 10.0,
        "p2_default": 0.0,
        "unite"     : "°C",
        # T = Gain × V + T_0
        # Valable pour tout conditionneur PT100 / thermocouple à sortie linéarisée
        "formule"   : lambda V, p1, p2: p1 * V + p2,
        "formule_str": "Gain × V + T_0"
    },
    "Brut": {
        "p1_label"  :"Gain a",
        "p2_label"  : "Offset b",
        "p1_default": 1.0,
        "p2_default": 0.0,
        "unite"     : "V",
        # y = a × V + b  (aucune conversion physique)
        "formule"   : lambda V, p1, p2: p1 * V + p2,
        "formule_str": "a × V + b"
    }
}
# ==========================================
# 1. CLASSE PERSONNALISÉE POUR LES VOIES
# ==========================================
class VoieButton(QFrame):
    def __init__(self, nom_boitier, nom_voie, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.nom_boitier = nom_boitier
        self.nom_voie = nom_voie
        self.is_checked = False

        self.setMinimumHeight(35)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)

        self.lbl_nom = QLabel(nom_voie)
        self.lbl_tiret = QLabel("—")

        layout.addWidget(self.lbl_nom)
        layout.addStretch()
        layout.addWidget(self.lbl_tiret)
        self.update_style()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_checked(not self.is_checked)
        super().mouseReleaseEvent(event)

    def set_checked(self, state):
        self.is_checked = state
        self.update_style()

    def update_style(self):
        if self.is_checked:
            self.setStyleSheet("""
                VoieButton { background-color: #E6F1FB; border: 1px solid #378ADD; border-radius: 6px; }
            """)
            self.lbl_nom.setStyleSheet("color: #0C447C; font-weight: bold; font-size: 12px; background: transparent;")
            self.lbl_tiret.setStyleSheet("color: #185FA5; font-weight: bold; font-size: 12px; background: transparent;")
        else:
            self.setStyleSheet("""
                VoieButton { background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; }
                VoieButton:hover { background-color: #f3f4f6; }
            """)
            self.lbl_nom.setStyleSheet("color: #1f2937; font-weight: normal; font-size: 12px; background: transparent;")
            self.lbl_tiret.setStyleSheet("color: #9ca3af; font-weight: bold; font-size: 12px; background: transparent;")


# ==========================================
# 2. FEUILLE DE STYLE GLOBALE
# ==========================================
STYLESHEET = """
    QMainWindow { background-color: #ffffff; }
    #Sidebar { background-color: #ffffff; border-right: 1px solid #e5e7eb; }
    #Sidebar QPushButton { text-align: left; padding: 10px 15px; border: none; border-left: 3px solid transparent; font-size: 13px; color: #4b5563; background-color: transparent; }
    #Sidebar QPushButton:hover { background-color: #f3f4f6; }
    #Sidebar QPushButton:checked { color: #185FA5; border-left: 3px solid #185FA5; background-color: #E6F1FB; font-weight: bold; }
    #Topbar { background-color: #ffffff; border-bottom: 1px solid #e5e7eb; }
    #BtnMenu { border: none; border-right: 1px solid #e5e7eb; background-color: #ffffff; font-size: 18px; }
    #BtnMenu:hover { background-color: #f3f4f6; }
    .SectionTitle { color: #4b5563; font-size: 10px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    .BoxButton { background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; text-align: left; }
    .BoxButton:hover { background-color: #f3f4f6; }
    .BoxButton:checked { border: 1px solid #378ADD; background-color: #E6F1FB; }
    .BoxButton:disabled { background-color: #f9fafb; border: 1px solid #e5e7eb; opacity: 0.6; }
    .BtnPrimary { background-color: #185FA5; color: white; border: none; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
    .BtnPrimary:hover { background-color: #0C447C; }
    .BtnSecondary { background-color: #ffffff; color: #374151; border: 1px solid #d1d5db; border-radius: 4px; padding: 6px 12px; }
    .BtnSecondary:hover { background-color: #f3f4f6; }
    .ParamBox { border: 1px solid #d1d5db; border-radius: 4px; padding: 5px; background-color: #ffffff; }
    .SuccessBanner { background-color: #EAF3DE; border: 1px solid #C0DD97; border-radius: 6px; }
    .BtnSuccess { background-color: #C0DD97; color: #27500A; border: 1px solid #A4C773; border-radius: 4px; padding: 6px 12px; font-weight: bold; }
    .BtnSuccess:hover { background-color: #A4C773; }
    .BtnDanger { background-color: #FCEBEB; color: #791F1F; border: 1px solid #F7C1C1; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
    .BtnDanger:hover { background-color: #F7C1C1; }
    QProgressBar { border: 1px solid #e5e7eb; border-radius: 4px; background-color: #f3f4f6; height: 8px; text-align: center; color: transparent; }
    QProgressBar::chunk { background-color: #378ADD; border-radius: 3px; }
    .DropZone { background-color: #f9fafb; border: 2px dashed #d1d5db; border-radius: 8px; color: #6b7280; text-align: center; font-size: 13px; }
    .DropZone:hover { background-color: #f3f4f6; border-color: #9ca3af; }
    .FileBanner { background-color: #E6F1FB; border: 1px solid #B5D4F4; border-radius: 6px; }
    QComboBox { border: 1px solid #d1d5db; border-radius: 4px; padding: 4px; background-color: #ffffff; }
    .TagPression { background-color: #E6F1FB; color: #0C447C; border-radius: 10px; padding: 2px 8px; font-size: 10px; font-weight: bold; }
    .TagAccel { background-color: #EEEDFE; color: #3C3489; border-radius: 10px; padding: 2px 8px; font-size: 10px; font-weight: bold; }
    .TagTemp { background-color: #FAEEDA; color: #633806; border-radius: 10px; padding: 2px 8px; font-size: 10px; font-weight: bold; }
    .TagDebit { background-color: #EAF3DE; color: #27500A; border-radius: 10px; padding: 2px 8px; font-size: 10px; font-weight: bold; }
    .TagBrut { background-color: #f3f4f6; color: #4b5563; border-radius: 10px; padding: 2px 8px; font-size: 10px; font-weight: bold; }
    .VisuTab { border: none; border-bottom: 2px solid transparent; background: transparent; padding: 6px 12px; font-size: 12px; color: #6b7280; }
    .VisuTab:hover { color: #1f2937; }
    .VisuTab:checked { border-bottom: 2px solid #185FA5; color: #185FA5; font-weight: bold; }
    .MetricBox { background-color: #f9fafb; border-radius: 6px; padding: 10px 15px; }
    .MetricLabel { font-size: 10px; color: #6b7280; text-transform: uppercase; font-weight: bold; letter-spacing: 1px; }
"""


# ==========================================
# 3. APPLICATION PRINCIPALE
# ==========================================
class WaveLabApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Initialisation par défaut sur National Instruments
        self.input_ip_manuelle = None
        self.mode_simulation_mcc = False
        self.gestionnaire = GestionnairePrincipal()

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

        self.lbl_top_status = QLabel("0 boîtier trouvé")
        self.lbl_top_status.setStyleSheet("color: #6b7280; font-size: 11px;")

        self.topbar_layout.addWidget(self.btn_toggle_menu)
        self.topbar_layout.addWidget(self.lbl_title)
        self.topbar_layout.addStretch()
        self.topbar_layout.addWidget(self.lbl_top_status)

        self.stacked_widget = QStackedWidget()
        self.content_layout.addWidget(self.topbar)
        self.content_layout.addWidget(self.stacked_widget)

        self.setup_pages()

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.content_area)

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

        # NOUVEAU : Menu déroulant pour le choix de la technologie matérielle
        selector_layout = QHBoxLayout()
        lbl_select = QLabel("Matériel de l'essai :")
        lbl_select.setStyleSheet("font-size: 13px; font-weight: bold; color: #374151;")

        self.check_ni = QCheckBox("National Instruments (USB / Chassis)")
        self.check_ni.setChecked(True)

        self.check_kistler = QCheckBox("Kistler LabAmp (Réseau TCP/IP)")
        self.check_kistler.stateChanged.connect(self.toggle_champ_ip)

        # Après self.chk_kistler = ... ajouter :
        mcc_row = QHBoxLayout()
        self.chk_mcc = QCheckBox("MCC USB-1808X")
        self.chk_mcc_sim = QCheckBox("Simulation")
        self.chk_mcc_sim.setChecked(True)
        self.chk_mcc_sim.setEnabled(False)
        self.chk_mcc_sim.setStyleSheet("color: #6b7280; font-size: 11px;")
        self.chk_mcc.toggled.connect(lambda on: self.chk_mcc_sim.setEnabled(on))
        mcc_row.addWidget(self.chk_mcc)
        mcc_row.addSpacing(20)
        mcc_row.addWidget(self.chk_mcc_sim)
        mcc_row.addStretch()

        selector_layout.addWidget(lbl_select)
        selector_layout.addWidget(self.check_ni)
        selector_layout.addWidget(self.check_kistler)
        selector_layout.addStretch()



        layout.addLayout(selector_layout)
        layout.addLayout(mcc_row)
        layout.addSpacing(20)

        header_layout = QHBoxLayout()
        lbl_header = QLabel("Recherche des périphériques physiques")
        lbl_header.setStyleSheet("font-size: 15px; font-weight: 500;")

        # Champ pour entrer les IPs manuelles (stocké en tant qu'attribut de classe self.)
        self.input_ip_manuelle = QLineEdit()
        self.input_ip_manuelle.setPlaceholderText("IPs manuelles Kistler (ex: 169.254.77.238, 169.254.12.5)")
        self.input_ip_manuelle.setMinimumWidth(320)
        self.input_ip_manuelle.setStyleSheet("padding: 4px; border: 1px solid #d1d5db; border-radius: 4px;")
        self.input_ip_manuelle.hide()  # 🎯 CACHÉ PAR DÉFAUT

        self.btn_scanner = QPushButton("Scanner")
        self.btn_scanner.setProperty("class", "BtnSecondary")
        self.btn_scanner.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_scanner.clicked.connect(self.lancer_scan_materiel)

        header_layout.addWidget(lbl_header)
        header_layout.addStretch()
        header_layout.addWidget(self.input_ip_manuelle)
        header_layout.addWidget(self.btn_scanner)
        layout.addLayout(header_layout)

        layout.addSpacing(20)

        self.lbl_online = QLabel("STATUT — EN ATTENTE DE SCAN")
        self.lbl_online.setProperty("class", "SectionTitle")
        layout.addWidget(self.lbl_online)

        self.grid_online = QGridLayout()
        self.grid_online.setSpacing(15)
        layout.addLayout(self.grid_online)

        layout.addSpacing(30)
        lbl_offline = QLabel("HORS LIGNE (HISTORIQUE)")
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
        self.btn_continuer.clicked.connect(self.valider_selection_boitiers)

        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_continuer)
        layout.addLayout(bottom_layout)

    def toggle_champ_ip(self):
        if self.check_kistler.isChecked():
            self.input_ip_manuelle.show()
        else:
            self.input_ip_manuelle.hide()
            self.input_ip_manuelle.clear()

    def changer_backend_materiel(self):
        """Bascule de manière transparente entre les deux gestionnaires sans casser l'UI"""
        if self.combo_choix_materiel.currentIndex() == 0:
            self.gestionnaire = GestionnaireNI()
            self.input_ip_manuelle.hide()  # Masque le champ pour National Instruments
            self.input_ip_manuelle.clear() # Nettoie le texte écrit pour éviter les conflits
            print("🔀 Passage sur le système National Instruments (Champ IP masqué)")
        else:
            self.gestionnaire = GestionnaireKistler()
            self.input_ip_manuelle.show()  # affiche le champ UNIQUEMENT pour Kistler LabAmp
            print("🔀 Passage sur le système Kistler LabAmp (Champ IP visible)")

        # Réinitialisation propre des labels
        self.lbl_online.setText("STATUT — EN ATTENTE DE SCAN")
        self.lbl_top_status.setText("0 boîtier")
        self.nettoyer_grille_online()

    def nettoyer_grille_online(self):
        while self.grid_online.count():
            item = self.grid_online.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def create_boitier_btn(self, name, desc, status, simule=False):
        btn = QPushButton()
        is_online = (status == "online")
        btn.setCheckable(is_online)
        btn.setMinimumHeight(60)

        # Style jaune si simulé, sinon style normal
        if simule:
            btn.setStyleSheet("""
                QPushButton { background-color: #FFFBEB; border: 1px solid #F59E0B;
                              border-radius: 6px; text-align: left; }
                QPushButton:checked { background-color: #FEF3C7; border: 1px solid #D97706; }
            """)
        else:
            btn.setProperty("class", "BoxButton")

        if is_online:
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        else:
            btn.setEnabled(False)

        btn_layout = QHBoxLayout(btn)
        btn_layout.setContentsMargins(15, 10, 15, 10)

        dot = QLabel("●")
        dot_color = "#F59E0B" if simule else ("#639922" if is_online else "#B4B2A9")
        dot.setStyleSheet(f"color: {dot_color}; font-size: 16px;")
        dot.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Ajout du badge "SIMULATION" si besoin
        badge_simulation = ""
        if simule:
            badge_simulation = " <span style='background:#F59E0B; color:white; border-radius:4px; padding: 1px 6px; font-size:10px; font-weight:bold;'>SIMULATION</span>"

        info = QLabel(
            f"<span style='font-size: 13px; font-weight: 600; color: #1f2937;'>"
            f"{name}{badge_simulation}</span><br>"
            f"<span style='font-size: 11px; color: #6b7280;'>{desc}</span>"
        )
        info.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        btn_layout.addWidget(dot)
        btn_layout.addWidget(info)
        btn_layout.addStretch()
        return btn

    def lancer_scan_materiel(self):
        scan_ni = self.check_ni.isChecked()
        scan_kistler = self.check_kistler.isChecked()
        scan_mcc = self.chk_mcc.isChecked()  # ← ajouter

        if not scan_ni and not scan_kistler and not scan_mcc:  # ← ajouter scan_mcc
            QMessageBox.warning(self, "Attention", "Veuillez cocher au moins un type de matériel à scanner.")
            return

        self.lbl_online.setText("STATUT — RECHERCHE EN COURS...")
        self.btn_scanner.setText("Scan...")
        self.btn_scanner.setEnabled(False)

        self.nettoyer_grille_online()
        self._boitiers_affiches = 0
        self.boutons_boitiers = []  # Essentiel pour la page des voies !

        liste_ips_manuelles = None
        if scan_kistler:
            texte_ip = self.input_ip_manuelle.text().strip()
            if texte_ip:
                liste_ips_manuelles = [ip.strip() for ip in texte_ip.split(",") if ip.strip()]

        # Lancement asynchrone pour ne pas figer l'interface
        self.thread_scan = ScanThread(
            self.gestionnaire,
            scan_ni=self.check_ni.isChecked(),
            scan_kistler=self.check_kistler.isChecked(),
            scan_mcc=self.chk_mcc.isChecked(),
            mode_simulation_mcc=self.chk_mcc_sim.isChecked(),
            ips_manuelles=liste_ips_manuelles,
        )
        self.thread_scan.boitier_trouve.connect(self._afficher_boitier_en_direct)
        self.thread_scan.scan_termine.connect(self.finaliser_scan_materiel)
        self.thread_scan.start()

    def _afficher_boitier_en_direct(self, boitier):
        """Appelé dès qu'un boîtier est confirmé, avant la fin du scan total."""
        idx = self._boitiers_affiches
        desc = f"{boitier['modele']} · {boitier['total_voies']} voies"
        btn_box = self.create_boitier_btn(boitier['nom'], desc, status="online", simule=boitier.get("simule", False))
        if idx == 0:
            btn_box.setChecked(True)

        # <-- AJOUT : On attache les données et on sauvegarde le bouton
        btn_box.boitier_data = boitier
        self.boutons_boitiers.append(btn_box)

        self.grid_online.addWidget(btn_box, idx // 3, idx % 3)
        self._boitiers_affiches += 1
        self.lbl_online.setText(f"EN LIGNE — {self._boitiers_affiches} DISPOSITIF(S) TROUVÉ(S)")
        self.lbl_top_status.setText(f"{self._boitiers_affiches} boîtier(s) trouvé(s)")

    def finaliser_scan_materiel(self, succes, message_erreur):
        boitiers = self.gestionnaire.boitiers_detectes

        # On ne construit plus la page ici ! On gère juste les erreurs.
        if not succes or not boitiers:
            if message_erreur:
                QMessageBox.critical(self, "Erreur de Connexion", message_erreur)

            self.lbl_online.setText("EN LIGNE — Aucun appareil détecté")
            self.lbl_top_status.setText("0 boîtier")
            lbl_erreur = QLabel("Aucun matériel détecté. Vérifiez l'alimentation et la connectique.")
            lbl_erreur.setStyleSheet("color: #791F1F; font-weight: bold;")
            self.grid_online.addWidget(lbl_erreur, 0, 0)
            self.build_page_voies([])

        self.btn_scanner.setText("Scanner")
        self.btn_scanner.setEnabled(True)

    # ==========================================
    # CONSTRUCTION: PAGE "SÉLECTION VOIES"
    # ==========================================

    def valider_selection_boitiers(self):
        """Filtre les boîtiers cochés et construit la page des voies sur mesure"""
        boitiers_selectionnes = []

        # On inspecte tous les boutons mémorisés
        if hasattr(self, 'boutons_boitiers'):
            for btn in self.boutons_boitiers:
                if btn.isChecked():
                    boitiers_selectionnes.append(btn.boitier_data)

        # Sécurité anti-clic vide
        if not boitiers_selectionnes:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner au moins un boîtier pour continuer.")
            return

        # On génère la page 2 UNIQUEMENT avec la sélection
        self.build_page_voies(boitiers_selectionnes)

        # Et on y va !
        self.switch_page(1)


    def build_page_voies(self, boitiers_actifs=None):
        if boitiers_actifs is None:
            boitiers_actifs = []

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
                btn_voie = VoieButton(nom_b, voie_nom)
                if i < 2:  # Coche par défaut les premières voies pour fluidifier l'essai
                    btn_voie.set_checked(True)

                self.tous_les_boutons.append(btn_voie)
                grid_voies.addWidget(btn_voie, i // colonnes, i % colonnes)

            scroll_layout.addLayout(grid_voies)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 15, 0, 0)

        self.btn_retour = QPushButton("Retour")
        self.btn_retour.setProperty("class", "BtnSecondary")
        self.btn_retour.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_retour.clicked.connect(lambda: self.switch_page(0))

        self.btn_continuer_acq = QPushButton("Continuer → Acquisition")
        self.btn_continuer_acq.setProperty("class", "BtnPrimary")
        self.btn_continuer_acq.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_continuer_acq.clicked.connect(self.valider_selection_voies)

        bottom_layout.addWidget(self.btn_retour)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_continuer_acq)
        main_layout.addLayout(bottom_layout)

    def valider_selection_voies(self):
        self.dico_voies = {}
        total_coche = 0

        for btn in self.tous_les_boutons:
            if btn.is_checked:
                total_coche += 1
                if btn.nom_boitier not in self.dico_voies:
                    self.dico_voies[btn.nom_boitier] = []
                self.dico_voies[btn.nom_boitier].append(btn.nom_voie)

        if total_coche == 0:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner au moins une voie pour continuer.")
            return

        self.lbl_voies_val.setText(f"{total_coche} sélectionnées")
        self.switch_page(2)
        print(f"Dictionnaire prêt pour le matériel : {self.dico_voies}")

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
    def build_page_acq(self, duree_defaut=10, freq_defaut=500, voies_actives=0):
        if self.page_acq.layout():
            QWidget().setLayout(self.page_acq.layout())

        layout = QVBoxLayout(self.page_acq)
        layout.setContentsMargins(40, 20, 40, 20)
        layout.setSpacing(20)

        lbl_params = QLabel("Paramètres de l'essai")
        lbl_params.setProperty("class", "SectionTitle")
        layout.addWidget(lbl_params)

        grid_params = QGridLayout()
        grid_params.setSpacing(20)

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

        lbl_voies = QLabel("VOIES ACTIVES")
        lbl_voies.setProperty("class", "SectionTitle")
        self.lbl_voies_val = QLabel(f"{voies_actives} sélectionnées")
        self.lbl_voies_val.setStyleSheet("padding: 5px; color: #6b7280;")

        layout_voies = QVBoxLayout()
        layout_voies.addWidget(lbl_voies)
        layout_voies.addWidget(self.lbl_voies_val)
        grid_params.addLayout(layout_voies, 0, 2)

        layout.addLayout(grid_params)
        lbl_note = QLabel(
            "ℹ️  Nombre de points enregistrés = Durée × Fréquence  (ex: 10 s × 1000 Hz = 10 000 pts/voie)")
        lbl_note.setStyleSheet("color: #6b7280; font-size: 11px; font-style: italic;")
        layout.addWidget(lbl_note)

        layout.addSpacing(10)
        layout.addSpacing(10)

        ctrl_layout = QHBoxLayout()
        self.lbl_status_acq = QLabel("● En attente")
        self.lbl_status_acq.setStyleSheet("color: #6b7280; font-weight: bold; font-size: 12px;")

        self.lbl_time_acq = QLabel(f"0.0 s / {duree_defaut} s")
        self.lbl_time_acq.setStyleSheet("color: #6b7280; font-size: 11px;")

        self.btn_lancer = QPushButton("Lancer l'essai")
        self.btn_lancer.setProperty("class", "BtnPrimary")
        self.btn_lancer.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_lancer.clicked.connect(self.start_acquisition)

        self.btn_arreter = QPushButton("Arrêter")
        self.btn_arreter.setProperty("class", "BtnDanger")
        self.btn_arreter.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_arreter.clicked.connect(lambda: self.stop_acquisition(manually=True))
        self.btn_arreter.hide()

        ctrl_layout.addWidget(self.lbl_status_acq)
        ctrl_layout.addWidget(self.lbl_time_acq)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.btn_lancer)
        ctrl_layout.addWidget(self.btn_arreter)
        layout.addLayout(ctrl_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', '#6b7280')
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        layout.addWidget(self.plot_widget, stretch=1)

        self.banner_success = QFrame()
        self.banner_success.setProperty("class", "SuccessBanner")
        self.banner_success.hide()
        banner_layout = QHBoxLayout(self.banner_success)

        info_layout = QVBoxLayout()
        self.lbl_banner_title = QLabel("Acquisition terminée")
        self.lbl_banner_title.setStyleSheet("color: #27500A; font-weight: bold; font-size: 13px;")
        self.lbl_banner_sub = QLabel("Détails...")
        info_layout.addWidget(self.lbl_banner_title)
        info_layout.addWidget(self.lbl_banner_sub)

        self.btn_calibrer = QPushButton("Calibrer ce fichier")
        self.btn_calibrer.setProperty("class", "BtnSecondary")
        self.btn_calibrer.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_calibrer.clicked.connect(self.basculer_vers_calibration)

        self.btn_enregistrer = QPushButton("Enregistrer sous...")
        self.btn_enregistrer.setProperty("class", "BtnSuccess")
        self.btn_enregistrer.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_enregistrer.clicked.connect(self.save_file)

        banner_layout.addLayout(info_layout)
        banner_layout.addStretch()
        banner_layout.addWidget(self.btn_calibrer)
        banner_layout.addWidget(self.btn_enregistrer)
        layout.addWidget(self.banner_success)

        self.donnees_x_plot = []
        self.donnees_y_plot = []

    # ==========================================
    # LOGIQUE D'ACQUISITION (TEMPS RÉEL MULTI-MATÉRIEL)
    # ==========================================
    def start_acquisition(self):
        self.banner_success.hide()
        self.btn_lancer.hide()
        self.btn_arreter.show()
        self.spin_duree.setEnabled(False)
        self.spin_freq.setEnabled(False)

        self.lbl_status_acq.setText("● En cours")
        self.lbl_status_acq.setStyleSheet("color: #185FA5; font-weight: bold; font-size: 12px;")
        self.progress_bar.setValue(0)

        self.target_duree = self.spin_duree.value()

        # Configuration uniforme via l'interface du pattern Stratégie
        self.gestionnaire.definir_parametres(
            duree=self.target_duree,
            frequence=self.spin_freq.value()
        )

        self.plot_widget.clear()
        self.courbes_actives = []
        couleurs = ['#185FA5', '#993556', '#854F0B', '#3B6D11', '#5B3256', '#212121']

        index = 0
        if hasattr(self, 'dico_voies'):
            for boitier, voies in self.dico_voies.items():
                for voie in voies:
                    c = self.plot_widget.plot(pen=pg.mkPen(couleurs[index % len(couleurs)], width=2),
                                              name=f"{voie}")
                    self.courbes_actives.append(c)
                    index += 1

        self.donnees_x_plot = [[] for _ in range(index)]
        self.donnees_y_plot = [[] for _ in range(index)]

        # Lancement du Thread d'acquisition générique
        self.thread_acq = AcquisitionThread(self.gestionnaire, getattr(self, 'dico_voies', {}))
        self.thread_acq.maj_graphique.connect(self.update_acquisition)
        self.thread_acq.acquisition_terminee.connect(
            lambda succes: self.stop_acquisition(manually=False, succes=succes))
        self.thread_acq.start()

    def update_acquisition(self, nouveaux_temps, nouvelles_donnees, indices_courbes=None):
        # Si aucun indice n'est fourni, on met à jour dans l'ordre (sécurité)
        if indices_courbes is None:
            indices_courbes = range(len(nouvelles_donnees))

        # On met à jour UNIQUEMENT les courbes concernées par ce paquet (soit NI, soit Kistler)
        for i, idx_global in enumerate(indices_courbes):
            self.donnees_x_plot[idx_global].extend(nouveaux_temps)
            self.donnees_y_plot[idx_global].extend(nouvelles_donnees[i])

            # Anti-lag : on ne garde que les 2000 derniers points sur l'écran
            if len(self.donnees_x_plot[idx_global]) > 2000:
                self.donnees_x_plot[idx_global] = self.donnees_x_plot[idx_global][-2000:]
                self.donnees_y_plot[idx_global] = self.donnees_y_plot[idx_global][-2000:]

            # Dessin de la courbe spécifique
            self.courbes_actives[idx_global].setData(self.donnees_x_plot[idx_global], self.donnees_y_plot[idx_global])

        # Mise à jour de la barre de progression globale
        if self.donnees_x_plot[0]:
            temps_actuel = self.donnees_x_plot[0][-1]
            self.lbl_time_acq.setText(f"{temps_actuel:.1f} s / {self.target_duree} s")
            self.progress_bar.setValue(min(int((temps_actuel / self.target_duree) * 100), 100))



    def stop_acquisition(self, manually=False, succes=True):
        if manually and hasattr(self, 'thread_acq'):
            self.thread_acq.stop()
            # On attend max 2 secondes — si le thread ne s'arrête pas,
            # on continue quand même pour ne pas figer l'UI
            if not self.thread_acq.wait(2000):
                print("[UI] Thread d'acquisition forcé à l'arrêt.")
                self.thread_acq.terminate()

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
            self.lbl_banner_title.setText("Erreur matérielle / Déconnexion du flux")

        freq = self.spin_freq.value()
        voies = len(getattr(self, 'courbes_actives', []))

        temps = 0
        # On va chercher le dernier point de la première courbe [0][-1]
        if hasattr(self, 'donnees_x_plot') and self.donnees_x_plot and self.donnees_x_plot[0]:
            temps = self.donnees_x_plot[0][-1]

        pts = int(temps * freq)
        self.lbl_banner_sub.setText(f"{temps:.1f} s · {freq} Hz · {voies} voies · {pts} pts")
        self.banner_success.show()

    def save_file(self):
        import shutil

        chemin_auto_sauvegarde = os.path.join(
            self.gestionnaire.parametres.get("dossier_sortie", "."),
            self.gestionnaire.parametres.get("nom_fichier", "donnees.csv")
        )

        if not os.path.exists(chemin_auto_sauvegarde):
            QMessageBox.critical(self, "Erreur", "Le fichier temporaire d'acquisition est introuvable.")
            return

        nom_defaut = self.gestionnaire.parametres.get("nom_fichier", "donnees_brutes.csv")
        file_name, _ = QFileDialog.getSaveFileName(self, "Enregistrer les données d'acquisition", nom_defaut,
                                                   "Fichiers CSV (*.csv)")

        if file_name:
            try:
                shutil.copy(chemin_auto_sauvegarde, file_name)
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

        lbl_source = QLabel("Fichier source")
        lbl_source.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(lbl_source)

        self.btn_dropzone = QPushButton("Glisser un fichier ou cliquer pour importer\n\n.csv · données brutes")
        self.btn_dropzone.setProperty("class", "DropZone")
        self.btn_dropzone.setMinimumHeight(120)
        self.btn_dropzone.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_dropzone.clicked.connect(self.simulate_file_import)
        layout.addWidget(self.btn_dropzone)

        self.banner_file = QFrame()
        self.banner_file.setProperty("class", "FileBanner")
        self.banner_file.hide()
        banner_layout = QHBoxLayout(self.banner_file)

        info_layout = QVBoxLayout()
        self.lbl_filename = QLabel("nom_du_fichier.csv")
        self.lbl_filename.setStyleSheet("color: #0C447C; font-weight: bold; font-size: 13px;")
        self.lbl_fileinfo = QLabel("X lignes · Y colonnes")
        self.lbl_fileinfo.setStyleSheet("color: #185FA5; font-size: 11px;")
        info_layout.addWidget(self.lbl_filename)
        info_layout.addWidget(self.lbl_fileinfo)

        self.btn_parcourir = QPushButton("Parcourir...")
        self.btn_parcourir.setProperty("class", "BtnSecondary")
        self.btn_parcourir.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_parcourir.clicked.connect(self.simulate_file_import)

        banner_layout.addLayout(info_layout)
        banner_layout.addStretch()
        banner_layout.addWidget(self.btn_parcourir)
        layout.addWidget(self.banner_file)

        self.calib_container = QWidget()
        self.calib_container.hide()
        self.calib_layout = QVBoxLayout(self.calib_container)
        self.calib_layout.setContentsMargins(0, 20, 0, 0)

        lbl_def = QLabel("Définition des capteurs par voie")
        lbl_def.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.calib_layout.addWidget(lbl_def)

        headers_layout = QGridLayout()
        headers =  ["VOIE", "TYPE", "UNITÉ", "a  (pente)", "c  (offset)", "FORMULE"]

        for col, text in enumerate(headers):
            lbl = QLabel(text)
            lbl.setProperty("class", "SectionTitle")
            headers_layout.addWidget(lbl, 0, col)
        headers_layout.setColumnStretch(1, 2)
        self.calib_layout.addLayout(headers_layout)

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(15)
        self.calib_layout.addLayout(self.rows_layout)

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 20, 0, 0)

        self.btn_visu = QPushButton("Visualiser calibré")
        self.btn_visu.setProperty("class", "BtnSecondary")
        self.btn_visu.clicked.connect(self.process_and_visualize)

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
        self.dynamic_p1 = {}  # SpinBox paramètre 1
        self.dynamic_p2 = {}  # SpinBox paramètre 2
        self.dynamic_lbl_p1 = {}  # Label du paramètre 1 (nom physique)
        self.dynamic_lbl_p2 = {}  # Label du paramètre 2 (nom physique)
        self.dynamic_cols = {}  # nom de colonne CSV
        self.dynamic_combos = {}  # combo type par ligne (pour save_calibrated_file)
        self.calib_fichier_source = None

    def simulate_file_import(self):

        file_name, _ = QFileDialog.getOpenFileName(self, "Importer un fichier d'acquisition",
                                                   "", "Fichiers CSV (*.csv);;Tous les fichiers (*)")
        if file_name:
            try:
                import pandas as pd
                df = pd.read_csv(file_name)
                # On exclut la colonne temps(s) — ce sont les colonnes de données
                colonnes_data = [c for c in df.columns if c != "temps(s)"]
                nb_lignes = len(df)
                nb_cols = len(colonnes_data)

                self.calib_fichier_source = file_name
                self.btn_dropzone.hide()
                self.lbl_filename.setText(os.path.basename(file_name))
                self.lbl_fileinfo.setText(f"{nb_lignes:,} lignes · {nb_cols} colonnes de données".replace(",", " "))
                self.banner_file.show()
                self.populate_calibration_table(colonnes_data)
                self.calib_container.show()

            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible de lire le fichier :\n{e}")

    def populate_calibration_table(self, colonnes):
        from PyQt6.QtWidgets import QDoubleSpinBox

        # Nettoyage des lignes précédentes
        for i in reversed(range(self.rows_layout.count())):
            w = self.rows_layout.itemAt(i).widget()
            if w: w.deleteLater()

        self.dynamic_tags.clear()
        self.dynamic_units.clear()
        self.dynamic_p1.clear()
        self.dynamic_p2.clear()
        self.dynamic_lbl_p1.clear()
        self.dynamic_lbl_p2.clear()
        self.dynamic_cols.clear()
        self.dynamic_combos.clear()

        for row_index, voie in enumerate(colonnes):
            self.dynamic_cols[row_index] = voie
            cfg = CAPTEURS_CONFIG["Pression"]  # config par défaut

            row_widget = QWidget()
            row_grid = QGridLayout(row_widget)
            row_grid.setContentsMargins(0, 5, 0, 5)
            row_grid.setSpacing(10)

            # ── Col 0 : Nom de voie ──────────────────────────────
            lbl_voie = QLabel(voie.split('/')[-1].split('(')[0])
            lbl_voie.setStyleSheet("font-weight: bold; font-size: 12px;")
            row_grid.addWidget(lbl_voie, 0, 0)

            # ── Col 1 : Type + badge ─────────────────────────────
            combo_type = QComboBox()
            combo_type.addItems(list(CAPTEURS_CONFIG.keys()))
            lbl_tag = QLabel("pression")
            lbl_tag.setProperty("class", "TagPression")
            lbl_tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_tag.setFixedWidth(80)
            type_layout = QVBoxLayout()
            type_layout.addWidget(combo_type)
            type_layout.addWidget(lbl_tag)
            row_grid.addLayout(type_layout, 0, 1)

            # ── Col 2 : Unité résultat ───────────────────────────
            lbl_unite = QLabel(cfg["unite"])
            lbl_unite.setStyleSheet("font-family: monospace; color: #4b5563;")
            row_grid.addWidget(lbl_unite, 0, 2)

            # ── Col 3 : Paramètre 1 (label + spinbox) ───────────
            lbl_p1 = QLabel(cfg["p1_label"])
            lbl_p1.setStyleSheet("font-size: 10px; color: #6b7280;")
            spin_p1 = QDoubleSpinBox()
            spin_p1.setRange(-1_000_000, 1_000_000)
            spin_p1.setDecimals(4)
            spin_p1.setValue(cfg["p1_default"])
            spin_p1.setProperty("class", "ParamBox")
            layout_p1 = QVBoxLayout()
            layout_p1.setSpacing(2)
            layout_p1.addWidget(lbl_p1)
            layout_p1.addWidget(spin_p1)
            row_grid.addLayout(layout_p1, 0, 3)

            # ── Col 4 : Paramètre 2 (label + spinbox) ───────────
            lbl_p2 = QLabel(cfg["p2_label"])
            lbl_p2.setStyleSheet("font-size: 10px; color: #6b7280;")
            spin_p2 = QDoubleSpinBox()
            spin_p2.setRange(-1_000_000, 1_000_000)
            spin_p2.setDecimals(4)
            spin_p2.setValue(cfg["p2_default"])
            spin_p2.setProperty("class", "ParamBox")
            layout_p2 = QVBoxLayout()
            layout_p2.setSpacing(2)
            layout_p2.addWidget(lbl_p2)
            layout_p2.addWidget(spin_p2)
            row_grid.addLayout(layout_p2, 0, 4)

            # ── Col 5 : Formule affichée ─────────────────────────
            lbl_formule = QLabel(f"y = {cfg['formule_str']}  [{cfg['unite']}]")
            lbl_formule.setStyleSheet("color: #185FA5; font-family: monospace; font-size: 10px;")
            row_grid.addWidget(lbl_formule, 0, 5)

            # Stockage
            self.dynamic_tags[row_index] = lbl_tag
            self.dynamic_units[row_index] = lbl_unite
            self.dynamic_p1[row_index] = spin_p1
            self.dynamic_p2[row_index] = spin_p2
            self.dynamic_lbl_p1[row_index] = lbl_p1
            self.dynamic_lbl_p2[row_index] = lbl_p2
            self.dynamic_combos[row_index] = combo_type

            # Mise à jour dynamique de la formule quand p1 ou p2 change
            def make_formule_updater(lf, idx):
                def update():
                    t = self.dynamic_combos[idx].currentText()
                    cfg = CAPTEURS_CONFIG.get(t, CAPTEURS_CONFIG["Brut"])
                    p1 = self.dynamic_p1[idx].value()
                    p2 = self.dynamic_p2[idx].value()
                    lf.setText(f"y = {cfg['formule_str']}  [{cfg['unite']}]"
                               f"\n   p1={p1}  p2={p2}")

                return update

            updater = make_formule_updater(lbl_formule, row_index)
            spin_p1.valueChanged.connect(lambda _, u=updater: u())
            spin_p2.valueChanged.connect(lambda _, u=updater: u())
            combo_type.currentIndexChanged.connect(
                lambda _, idx=row_index, cb=combo_type: self.update_row_type(idx, cb.currentText())
            )

            combo_type.setCurrentText("Pression")
            row_grid.setColumnStretch(1, 2)
            row_grid.setColumnStretch(5, 3)
            self.rows_layout.addWidget(row_widget)

    def update_row_type(self, row_index, selected_type):
        cfg = CAPTEURS_CONFIG.get(selected_type, CAPTEURS_CONFIG["Brut"])

        # ── Badge couleur ────────────────────────────────────────
        tag_classes = {
            "Pression": ("pression", "TagPression"),
            "Force": ("force", "TagAccel"),
            "Accélération": ("accél.", "TagAccel"),
            "Vitesse": ("vitesse", "TagDebit"),
            "Sonde": ("sonde", "TagTemp"),
            "Brut": ("brut", "TagBrut"),
        }
        tag_txt, tag_cls = tag_classes.get(selected_type, ("brut", "TagBrut"))
        tag = self.dynamic_tags[row_index]
        tag.setText(tag_txt)
        tag.setProperty("class", tag_cls)
        tag.style().unpolish(tag)
        tag.style().polish(tag)

        # ── Unité résultat ───────────────────────────────────────
        self.dynamic_units[row_index].setText(cfg["unite"])

        # ── Labels des paramètres ────────────────────────────────
        self.dynamic_lbl_p1[row_index].setText(cfg["p1_label"])
        self.dynamic_lbl_p2[row_index].setText(cfg["p2_label"])

        # ── Valeurs par défaut ───────────────────────────────────
        self.dynamic_p1[row_index].setValue(cfg["p1_default"])
        self.dynamic_p2[row_index].setValue(cfg["p2_default"])

    def save_calibrated_file(self):
        if not self.calib_fichier_source:
            QMessageBox.warning(self, "Attention", "Aucun fichier source chargé.")
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer fichier calibré",
            "donnees_calibrees.csv", "Fichiers CSV (*.csv)"
        )
        if not file_name:
            return

        try:
            import pandas as pd
            df = pd.read_csv(self.calib_fichier_source)
            colonnes_data = [c for c in df.columns if c != "temps(s)"]

            # Construction des dicts gain et offset pour calibrate()
            gain_dict = {}
            offset_dict = {}
            renommage = {}  # ancien nom → nouveau nom avec unité

            for row_index, col in enumerate(colonnes_data):
                if row_index not in self.dynamic_combos:
                    continue

                type_capteur = self.dynamic_combos[row_index].currentText()
                cfg = CAPTEURS_CONFIG.get(type_capteur, CAPTEURS_CONFIG["Brut"])
                p1 = self.dynamic_p1[row_index].value()
                p2 = self.dynamic_p2[row_index].value()
                unite = cfg["unite"]

                # Conversion des paramètres physiques (p1, p2) en gain/offset
                # pour que calibrate() puisse faire simplement g*x + b
                # Chaque formule est ramenée à la forme y = g*x + b :
                #
                # Pression    : PE*(V-Vref)/(10-Vref) = [PE/(10-Vref)]*V + [-PE*Vref/(10-Vref)]
                # Force       : CN*V/(S/1000*10)      = [CN/(S/1000*10)]*V + 0
                # Accélération: (V-Vbias)*1000/S*9.81 = [1000*9.81/S]*V + [-Vbias*1000*9.81/S]
                # Vitesse     : (V-V0)/(S/1000)       = [1000/S]*V + [-V0*1000/S]
                # Sonde       : Gain*V + T0            = Gain*V + T0
                # Brut        : a*V + b                = a*V + b

                if type_capteur == "Pression":
                    denom = (10.0 - p2) if (10.0 - p2) != 0 else 1.0
                    g = p1 / denom
                    b = -p1 * p2 / denom

                elif type_capteur == "Force":
                    denom = (p2 / 1000.0) * 10.0 if p2 != 0 else 1.0
                    g = p1 / denom
                    b = 0.0

                elif type_capteur == "Accélération":
                    facteur = (1000.0 * 9.81 / p1) if p1 != 0 else 1.0
                    g = facteur
                    b = -p2 * facteur

                elif type_capteur == "Vitesse":
                    denom = p1 / 1000.0 if p1 != 0 else 1.0
                    g = 1.0 / denom
                    b = -p2 / denom

                elif type_capteur == "Sonde":
                    g = p1
                    b = p2

                else:  # Brut
                    g = p1
                    b = p2

                gain_dict[col] = g
                offset_dict[col] = b
                renommage[col] = f"{col.split('(')[0]}({unite})"

            # Appel de la fonction calibrate() des chercheurs
            df_calibre = self.calibrate(df, gain_dict, offset_dict)

            # Renommage des colonnes avec la bonne unité
            df_calibre.rename(columns=renommage, inplace=True)

            df_calibre.to_csv(file_name, index=False, float_format="%.6f")

            QMessageBox.information(
                self, "Calibration réussie",
                f"Fichier calibré enregistré :\n{file_name}\n\n"
                f"{len(df_calibre):,} points · {len(colonnes_data)} voies calibrées".replace(",", " ")
            )

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de la calibration :\n{e}")

    # ==========================================
    # CONSTRUCTION: PAGE "VISUALISATION"
    # ==========================================
    def build_page_visu(self):
        self.page_visu = QWidget()
        layout = QVBoxLayout(self.page_visu)
        layout.setContentsMargins(40, 20, 40, 20)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        lbl_title = QLabel("Visualisation des données")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.combo_visu_voies = QComboBox()
        self.combo_visu_voies.setMinimumWidth(150)
        self.combo_visu_voies.addItem("Aucune donnée chargée")
        self.combo_visu_voies.currentTextChanged.connect(self.filter_visu_channels)

        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.combo_visu_voies)
        layout.addLayout(header_layout)

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

        metrics_layout = QGridLayout()
        metrics_layout.setSpacing(10)
        self.lbl_metric_hs = self.create_metric_box("HS", "0.000", "m", metrics_layout, 0)
        self.lbl_metric_tp = self.create_metric_box("TP", "0.00", "s", metrics_layout, 1)
        self.lbl_metric_hmax = self.create_metric_box("HMAX", "0.000", "m", metrics_layout, 2)
        self.lbl_metric_duree = self.create_metric_box("DURÉE", "0", "s", metrics_layout, 3)
        layout.addLayout(metrics_layout)

        self.visu_plot = pg.PlotWidget()
        self.visu_plot.setBackground('w')
        self.visu_plot.showGrid(x=True, y=True, alpha=0.3)
        layout.addWidget(self.visu_plot, stretch=1)

        self.visu_curves = {}
        self.visu_current_data = {}

    def switch_visu_tab(self, mode):
        self.btn_tab_brut.setChecked(mode == "Brut")
        self.btn_tab_calib.setChecked(mode == "Calibré")
        print(f"Demande d'affichage des données : {mode}")

    def create_metric_box(self, label, val, unit, layout, col):
        box = QFrame()
        box.setProperty("class", "MetricBox")
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(15, 10, 15, 10)

        lbl_title = QLabel(label)
        lbl_title.setProperty("class", "MetricLabel")
        lbl_val = QLabel(
            f"<span style='font-size: 18px; font-weight: bold; font-family: monospace;'>{val}</span> <span style='font-size: 11px; color: #6b7280;'>{unit}</span>")

        box_layout.addWidget(lbl_title)
        box_layout.addWidget(lbl_val)
        layout.addWidget(box, 0, col)
        return lbl_val

    def load_visu_data(self, time_array, channels_dict, metrics_dict):
        self.visu_current_data = channels_dict

        # ── Métriques ────────────────────────────────────────────
        self.lbl_metric_hs.setText(
            f"<span style='font-size: 18px; font-weight: bold; font-family: monospace;'>"
            f"{metrics_dict.get('HS', '0')}</span> "
            f"<span style='font-size: 11px; color: #6b7280;'></span>")
        self.lbl_metric_tp.setText(
            f"<span style='font-size: 18px; font-weight: bold; font-family: monospace;'>"
            f"{metrics_dict.get('TP', '0')}</span> "
            f"<span style='font-size: 11px; color: #6b7280;'>s</span>")
        self.lbl_metric_hmax.setText(
            f"<span style='font-size: 18px; font-weight: bold; font-family: monospace;'>"
            f"{metrics_dict.get('HMAX', '0')}</span> "
            f"<span style='font-size: 11px; color: #6b7280;'></span>")
        self.lbl_metric_duree.setText(
            f"<span style='font-size: 18px; font-weight: bold; font-family: monospace;'>"
            f"{metrics_dict.get('DUREE', '0')}</span> "
            f"<span style='font-size: 11px; color: #6b7280;'>s</span>")

        # ── Combo voies ──────────────────────────────────────────
        self.combo_visu_voies.blockSignals(True)
        self.combo_visu_voies.clear()
        self.combo_visu_voies.addItem("Toutes les voies")
        for key, info in channels_dict.items():
            self.combo_visu_voies.addItem(info.get('name', key))
        self.combo_visu_voies.blockSignals(False)

        # ── Graphique ────────────────────────────────────────────
        self.visu_plot.clear()
        self.visu_curves.clear()

        # Légende
        self.visu_plot.addLegend(offset=(10, 10))

        # Label axe X
        self.visu_plot.setLabel('bottom', 'Temps', units='s')

        # Label axe Y — unité de la première voie
        # (si toutes les voies ont la même unité, sinon on laisse générique)
        unites = list({info.get("unite", "V") for info in channels_dict.values()})
        axe_y = unites[0] if len(unites) == 1 else "valeur"
        self.visu_plot.setLabel('left', 'Amplitude', units=axe_y)

        for key, info in channels_dict.items():
            curve = self.visu_plot.plot(
                time_array,
                info["data"],
                pen=pg.mkPen(info.get("color", "#000000"), width=1.5),
                name=info.get("name", key)  # ← affiché dans la légende avec l'unité
            )
            self.visu_curves[key] = curve

        self.combo_visu_voies.setCurrentIndex(0)

    def filter_visu_channels(self, selected_text):
        for key, curve in self.visu_curves.items():
            name = self.visu_current_data[key].get("name", key)
            if selected_text == "Toutes les voies" or selected_text == name:
                curve.setVisible(True)
            else:
                curve.setVisible(False)


    def process_and_visualize(self):
        import pandas as pd
        import numpy as np

        # ── Parcourir le fichier calibré ────────────────────────
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir fichier calibré", "",
            "Fichiers CSV (*.csv)"
        )
        if not file_name:
            return

        try:
            df = pd.read_csv(file_name)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de lire le fichier :\n{e}")
            return

        if "temps(s)" not in df.columns:
            QMessageBox.critical(self, "Erreur",
                                 "Colonne 'temps(s)' introuvable — ce n'est pas un fichier WaveLab.")
            return

        time_array = df["temps(s)"].values
        colonnes_data = [c for c in df.columns if c != "temps(s)"]

        if not colonnes_data:
            QMessageBox.warning(self, "Attention", "Aucune colonne de données trouvée.")
            return

        # ── Couleurs par voie ────────────────────────────────────
        couleurs = ['#185FA5', '#993556', '#854F0B',
                    '#3B6D11', '#5B3256', '#212121',
                    '#0E7C7B', '#C84B31']

        # ── Construction du dict channels pour load_visu_data ───
        # Format attendu : {key: {"data": array, "color": hex, "name": str, "unite": str}}
        channels_dict = {}
        for i, col in enumerate(colonnes_data):
            # Extraction de l'unité depuis le nom de colonne
            # ex: "ai0(bar)" → nom="ai0", unite="bar"
            if "(" in col and col.endswith(")"):
                nom_voie = col.split("(")[0]
                unite = col.split("(")[1].rstrip(")")
            else:
                nom_voie = col
                unite = "V"

            channels_dict[f"ch{i}"] = {
                "data": df[col].values,
                "color": couleurs[i % len(couleurs)],
                "name": f"{nom_voie} [{unite}]",
                "unite": unite
            }

        # ── Métriques globales ───────────────────────────────────
        duree = round(float(time_array[-1] - time_array[0]), 2)
        # Max absolu toutes voies confondues
        val_max = max(abs(df[c]).max() for c in colonnes_data)
        # Valeur RMS de la première voie
        rms = round(float(np.sqrt(np.mean(df[colonnes_data[0]].values ** 2))), 4)

        metriques = {
            "HS": round(val_max, 4),
            "TP": round(duree / len(colonnes_data), 3),
            "HMAX": round(float(max(df[c].max() for c in colonnes_data)), 4),
            "DUREE": duree
        }

        # ── Chargement et navigation ─────────────────────────────
        self.load_visu_data(time_array, channels_dict, metriques)
        self.switch_page(4)

    def basculer_vers_calibration(self):
        if hasattr(self.gestionnaire, 'chemins_voies_actives') and self.gestionnaire.chemins_voies_actives:
            voies_a_calibrer = self.gestionnaire.chemins_voies_actives
        else:
            voies_a_calibrer = ["Ch1", "Ch2"]

        chemin = os.path.join(
            self.gestionnaire.parametres.get("dossier_sortie", "."),
            self.gestionnaire.parametres.get("nom_fichier", "donnees.csv")
        )
        self.calib_fichier_source = chemin if os.path.exists(chemin) else None
        self.btn_dropzone.hide()
        self.lbl_filename.setText(self.gestionnaire.parametres.get("nom_fichier", "donnees.csv"))

        freq = self.spin_freq.value()

        temps = 0
        if hasattr(self, 'donnees_x_plot') and self.donnees_x_plot and self.donnees_x_plot[0]:
            temps = self.donnees_x_plot[0][-1]

        pts = int(temps * freq)

        self.lbl_fileinfo.setText(f"{pts} lignes · {len(voies_a_calibrer)} colonnes · Données directes")
        self.banner_file.show()

        self.populate_calibration_table(voies_a_calibrer)
        self.calib_container.show()
        self.switch_page(3)

    def closeEvent(self, event):
        self.gestionnaire.mcc.liberer()
        super().closeEvent(event)

    def calibrate(self,df, gain, offset):
        result = df.copy()
        for col in df.columns:
            g = gain.get(col, 1.0)
            b = offset.get(col, 0.0)
            result[col] = g * df[col] + b
        return result

from PyQt6.QtCore import QThread, pyqtSignal


class ScanThread(QThread):
    # Signal émis dès qu'un boîtier est confirmé
    boitier_trouve = pyqtSignal(dict)
    # Signal émis à la fin avec (succès global, message d'erreur éventuel)
    scan_termine = pyqtSignal(bool, str)

    # AJOUT DES PARAMÈTRES : scan_ni et scan_kistler
    def __init__(self, gestionnaire, scan_ni=True, scan_kistler=False,
                 scan_mcc=False, mode_simulation_mcc=False,  # ← ajouter
                 ips_manuelles=None):
        super().__init__()
        self.gestionnaire = gestionnaire
        self.scan_ni = scan_ni
        self.scan_kistler = scan_kistler
        self.ips_manuelles = ips_manuelles
        self.scan_mcc = scan_mcc  # ← ajouter
        self.mode_simulation_mcc = mode_simulation_mcc


    def run(self):
        if hasattr(self.gestionnaire, '_on_boitier_detecte'):
            self.gestionnaire._on_boitier_detecte = lambda info: self.boitier_trouve.emit(info)

        erreur_message = ""
        try:
            succes = self.gestionnaire.initialiser_systeme(
                scan_ni=self.scan_ni,
                scan_kistler=self.scan_kistler,
                scan_mcc=self.scan_mcc,
                mode_simulation_mcc=self.mode_simulation_mcc,
                ips_manuelles=self.ips_manuelles
            )
        except Exception as e:
            erreur_message = str(e)
            succes = False

        # Toujours émettre les boîtiers trouvés, même en cas d'erreur partielle
        for info in getattr(self.gestionnaire, 'boitiers_detectes', []):
            self.boitier_trouve.emit(info)

        # Récupère l'erreur Kistler stockée si elle existe
        if not erreur_message and hasattr(self.gestionnaire, '_erreur_kistler'):
            erreur_message = f"Kistler introuvable :\n{self.gestionnaire._erreur_kistler}"
            del self.gestionnaire._erreur_kistler

        self.scan_termine.emit(succes, erreur_message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WaveLabApp()
    window.show()
    sys.exit(app.exec())