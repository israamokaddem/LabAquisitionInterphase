import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QComboBox, QLineEdit,
                             QLabel, QFormLayout, QFrame, QCheckBox, QButtonGroup, QRadioButton, QFileDialog)


class LaboInterface(QMainWindow):
    def __init__(self, data_columns):
        # On définit la config avant super() pour être sûr qu'elle existe
        self.param = None
        self.CONFIG_PARAMETRES = {
            "Decomposition1": ["ProbeSpacing", "Depth", "Gain"],
            "Decomposition2": ["Frequency", "Amplitude", "Offset"],
            "Decomposition3": ["Seuil_Min", "Seuil_Max"],
            "Dsp1": ["Window_Size", "Overlap"],
            "Image1": ["Contrast", "Brightness", "Zoom"]
        }
        super().__init__()

        # Initialisation de tes variables
        self.check_list = []
        self.champs = {}  # Dictionnaire pour stocker les QLineEdit du formulaire
        self.data_columns = data_columns
        self.irreg_true = None
        self.irreg_false = None
        

        self.setWindowTitle("Interface de Traitement de Données")
        self.resize(800, 600)

        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(10)

        # ZONE HAUT
        layout_haut = QHBoxLayout()
        self.menu1 = QComboBox()
        self.menu1.addItems(["Decomposition1", "Decomposition2", "Decomposition3"])
        self.menu1.currentTextChanged.connect(self.update_form)

        self.menu2 = QComboBox()
        self.menu2.addItems(["Dsp1", "Dsp2", "Dsp3"])
        # Optionnel : connecter aussi menu2 et menu3 si tu veux qu'ils changent le formulaire
        self.menu2.currentTextChanged.connect(self.update_form)
        self.menu3 = QComboBox()
        self.menu3.addItems(["Image1", "Image2", "Image3"])
        self.menu3.currentTextChanged.connect(self.update_form)

        layout_haut.addWidget(self.menu1)
        layout_haut.addWidget(self.menu2)
        layout_haut.addWidget(self.menu3)
        self.main_layout.addLayout(layout_haut)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        self.main_layout.addWidget(line)

        # ZONE CENTRE
        layout_fichier = QHBoxLayout()
        self.input_fichier = QLineEdit()
        self.input_fichier.setPlaceholderText("Chemin du fichier...")
        self.btn_valider = QPushButton("Parcourrrir")
        self.btn_valider.clicked.connect(self.parcourir_fichier)
        layout_fichier.addWidget(self.input_fichier)
        layout_fichier.addWidget(self.btn_valider)
        self.main_layout.addLayout(layout_fichier)

        self.layout_columns()

        self.form_layout = QFormLayout()
        self.main_layout.addLayout(self.form_layout)

        # Appel initial pour remplir le formulaire au démarrage
        self.update_form(self.menu1.currentText())

        self.irregular()

        # ZONE BAS
        self.main_layout.addStretch()
        self.btn_entree = QPushButton("EXÉCUTER LE TRAITEMENT")
        self.btn_entree.setFixedHeight(50)
        self.main_layout.addWidget(self.btn_entree)

        container = QWidget()
        container.setLayout(self.main_layout)
        self.setCentralWidget(container)

    def layout_columns(self):
        layout_columns = QHBoxLayout()
        self.check_list = []
        # split permet de transformer ta string de test en vraie liste si besoin
        cols = self.data_columns.split(",") if isinstance(self.data_columns, str) else self.data_columns
        for name in cols:
            btn = QCheckBox(name.strip())
            layout_columns.addWidget(btn)
            self.check_list.append(btn)
        self.main_layout.addLayout(layout_columns)

    def update_form(self, choix_menu):
        # 1. Nettoyage
        while self.form_layout.count():
            child = self.form_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # 2. Récupération des attributs
        attributs = self.CONFIG_PARAMETRES.get(choix_menu, [])

        # 3. Création des champs
        self.champs = {}  # On vide le dico pour la nouvelle sélection
        for nom in attributs:
            self.param = QLineEdit()
            self.param.setPlaceholderText(f"Valeur pour {nom}")
            self.form_layout.addRow(f"{nom} :", self.param)
            self.champs[nom] = self.param

    def irregular(self):
        layout_Irregular = QHBoxLayout()
        # On attache 'irregular' à self pour qu'il ne disparaisse pas de la mémoire
        irregular_group = QButtonGroup(self)
        self.irreg_true = QRadioButton("YES")
        self.irreg_false = QRadioButton("NO")
        self.irreg_false.setChecked(True)

        irregular_group.addButton(self.irreg_true)
        irregular_group.addButton(self.irreg_false)

        layout_Irregular.addWidget(QLabel("Irregular:"))
        layout_Irregular.addWidget(self.irreg_true)
        layout_Irregular.addWidget(self.irreg_false)

        self.main_layout.addLayout(layout_Irregular)

    def parcourir_fichier(self):
        # QFileDialog.getOpenFileName(parent, titre, dossier_par_defaut, filtre)
        fichier, _ = QFileDialog.getOpenFileName(self,
            "Sélectionner le fichier CSV",
            "",
            "Fichiers CSV (*.csv)"
        )
        # Si l'utilisateur a choisi un fichier
        if fichier:
            self.input_fichier.setText(fichier)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Test avec une liste de colonnes
    window = LaboInterface(["Température", "Pression", "Vitesse"])
    window.show()
    sys.exit(app.exec())