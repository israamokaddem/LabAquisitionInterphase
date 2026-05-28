import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                             QVBoxLayout, QPushButton, QLabel, QStackedWidget,
                             QFrame, QGridLayout, QScrollArea)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QCursor


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

        self.stacked_widget.addWidget(self.page_detect)
        self.stacked_widget.addWidget(self.page_voies)
        self.stacked_widget.addWidget(self.page_acq)

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WaveLabApp()
    window.show()
    sys.exit(app.exec())