import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QComboBox, QLineEdit,
                             QLabel, QFormLayout, QFrame, QCheckBox, QButtonGroup, QRadioButton)
from qfluentwidgets import PushButton, ComboBox, LineEdit  # Optionnel pour le look


class LaboInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interface de Traitement de Données")
        self.resize(800, 600)

        # --- LAYOUT PRINCIPAL (Vertical) ---
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(10)

        # ==========================================
        # ZONE HAUT : 3 Menus déroulants
        # ==========================================
        layout_haut = QHBoxLayout()
        self.menu1 = QComboBox()
        self.menu1.addItems(["Decomposition1", "Decomposition2","Decomposition3" ])
        self.menu2 = QComboBox()
        self.menu2.addItems(["Dsp1", "Dsp2","Dsp3"])
        self.menu3 = QComboBox()
        self.menu3.addItems(["Image1", "Image2" ,"Image3"])

        layout_haut.addWidget(self.menu1)
        layout_haut.addWidget(self.menu2)
        layout_haut.addWidget(self.menu3)
        self.main_layout.addLayout(layout_haut)

        # Petit trait de séparation visuel
        line = QFrame();
        line.setFrameShape(QFrame.Shape.HLine);
        self.main_layout.addWidget(line)

        # ==========================================
        # ZONE CENTRE : Fichier, Colonnes et Formulaire
        # ==========================================
        # 1. Entrée fichier
        layout_fichier = QHBoxLayout()
        self.input_fichier = QLineEdit()
        self.input_fichier.setPlaceholderText("Chemin du fichier...")
        self.btn_valider = QPushButton("Valider")
        layout_fichier.addWidget(self.input_fichier)
        layout_fichier.addWidget(self.btn_valider)
        self.main_layout.addLayout(layout_fichier)

        # 2. Boutons de colonnes (5 boutons)
        layout_colonnes = QHBoxLayout()
        for i in range(5):
            btn = QCheckBox(f"Col {i+1}")
            btn.setChecked(False)
            layout_colonnes.addWidget(btn)
        self.main_layout.addLayout(layout_colonnes)

        # 3. Formulaire de paramétrage (4 zones)
        self.form_layout = QFormLayout()
        self.param1 = QLineEdit()
        self.param2 = QLineEdit()
        self.param3 = QLineEdit()
        self.form_layout.addRow("ProbeSpacing:", self.param1)
        self.form_layout.addRow("Depth (Pa):", self.param2)
        self.form_layout.addRow("Gain:", self.param3)
        self.main_layout.addLayout(self.form_layout)

        #4 zone de Bonton precisant l'irregularite oui ou non
        self.layout_Irregular = QHBoxLayout()
        self.Irregular= QButtonGroup()
        self.Irreg_True=QRadioButton("YES")
        self.Irreg_False= QRadioButton("NO")
        self.Irreg_False.setChecked(False)

        #Ajout des boutons au groupe de boutons
        self.Irregular.addButton(self.Irreg_True)
        self.Irregular.addButton(self.Irreg_False)

        #Ajout des boutons au layout de Irregular
        self.layout_Irregular.addWidget(QLabel("Irregular:"))
        self.layout_Irregular.addWidget(self.Irreg_True)
        self.layout_Irregular.addWidget(self.Irreg_False)

        self.main_layout.addLayout(self.layout_Irregular)


        # ==========================================
        # ZONE BAS : Bouton Entrée
        # ==========================================
        self.main_layout.addStretch()  # Pousse tout vers le haut
        self.btn_entree = QPushButton("EXÉCUTER LE TRAITEMENT")
        self.btn_entree.setFixedHeight(50)  # Plus gros pour le distinguer
        self.main_layout.addWidget(self.btn_entree)

        # --- APPLIQUER LE LAYOUT ---
        container = QWidget()
        container.setLayout(self.main_layout)
        self.setCentralWidget(container)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LaboInterface()
    window.show()
    sys.exit(app.exec())