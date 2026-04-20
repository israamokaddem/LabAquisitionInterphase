import pyqtgraph as pg
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QComboBox, QLineEdit,
                             QLabel, QFormLayout, QFrame, QCheckBox, QButtonGroup, QRadioButton, QFileDialog,
                             QMessageBox)

from Interpretation.Moteur import decomposition


class LaboInterface(QMainWindow):
    def __init__(self):
        # On définit la config avant super() pour être sûr qu'elle existe
        self.layout_chks = QHBoxLayout()
        self.param = None
        self.CONFIG_PARAMETRES = {
            "WaveProbeDecomposition": ["ProbeSpacing", "Depth", "Gain","StartCutIndex"],  #on definit pout chaque methode les parametres
            "Decomposition_LiuHuang": ["ProbeSpacing", "Depth", "Gain","omega","order"],
            "Decomposition_EldrupAnderson": ["ProbeSpacing", "Depth", "Gain","omega","order"],
            "Dsp1": ["Window_Size", "Overlap"],
            "Image1": ["Contrast", "Brightness", "Zoom"]
        }
        super().__init__()

        # Initialisation de tes variables
        self.check_list = []
        self.champs = {}  # Dictionnaire pour stocker les QLineEdit du formulaire
        self.data_columns =[]
        self.irreg_true = None
        self.irreg_false = None
        self.method_selected="menu1"


        self.setWindowTitle("Interface de Traitement de Données")
        self.resize(800, 600)

        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(10)
        self.main_layout.addLayout(self.layout_chks)

        # ZONE HAUT
        layout_haut = QHBoxLayout()
        self.menu1 = QComboBox()
        self.menu1.addItems(["WaveProbeDecomposition", "Decomposition_EldrupAnderson", "Decomposition_LiuHuang"])
        self.menu1.currentTextChanged.connect(self.update_form)

        self.menu2 = QComboBox()
        self.menu2.addItems(["Dsp1", "Dsp2", "Dsp3"])
        # Optionnel : connecter aussi menu2 et menu3 si je veux qu'ils changent le formulaire
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
        self.btn_entree.clicked.connect(self.lancer_calcul_final)
        container = QWidget()
        container.setLayout(self.main_layout)
        self.setCentralWidget(container)

    def layout_columns(self):
        # 1. On nettoie le layout (on enlève les anciennes colonnes s'il y en a)
        while self.layout_chks.count():
            item = self.layout_chks.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


       #on cree le layout des colonnes
        self.check_list = []
        # split permet de transformer la string de test en vraie liste si besoin
        cols = self.data_columns.split(",") if isinstance(self.data_columns, str) else self.data_columns
        for name in cols:
            if ('t' in name.strip().lower()):
                btn = QCheckBox(name.strip())
                self.layout_chks.addWidget(btn)
                btn.setChecked(True)  # On le coche par défaut
                btn.setEnabled(False)
            else:
                btn = QCheckBox(name.strip())
                self.layout_chks.addWidget(btn)
                self.check_list.append(btn)

        self.main_layout.addLayout(self.layout_chks)

    def update_form(self, choix_menu):
        # 1. Nettoyage
        while self.form_layout.count():
            child = self.form_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


        # 2. Récupération des attributs
        attributs = self.CONFIG_PARAMETRES.get(choix_menu, [])
        self.method_selected = choix_menu
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
        import pandas as pd
        # QFileDialog.getOpenFileName(parent, titre, dossier_par_defaut, filtre)
        self.fichier, _ = QFileDialog.getOpenFileName(self,
                                                      "Sélectionner le fichier CSV",
                                                      "",
                                                      "Fichiers CSV (*.csv)"
                                                      )
        # Si l'utilisateur a choisi un fichier
        if self.fichier:
            self.input_fichier.setText(self.fichier)

            try:
                # 1. On lit uniquement la première ligne (l'en-tête) du fichier
                columns_title = pd.read_csv(self.fichier, nrows=0)

                # 2. On initialise data_columns avec la liste des noms de colonnes
                self.data_columns = columns_title.columns.tolist()

                # 3. On appelle ta méthode existante pour mettre à jour l'affichage
                self.layout_columns()

            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Erreur", f"Impossible de lire les colonnes du fichier : {e}")





    def lancer_calcul_final(self):
        import pandas as pd
        from Interpretation.Moteur.decomposition import Decomposition

        # 1. Vérification du fichier d'entree
        if not self.fichier:
            QMessageBox.critical(self, "Erreur", "Veuillez sélectionner un fichier CSV.")
            return

        # 2. Extraction et vérification des paramètres numériques du formulaire
        params = {}

        for nom, widget in self.champs.items():
            valeur_texte = widget.text().strip()
            try:
                if nom == "ProbeSpacing":
                    # On transforme la chaîne "1, 2, 3" en liste de floats [1.0, 2.0, 3.0]
                    # On sépare par virgule, on nettoie les espaces et on convertit
                    params[nom] = [float(x) for x in valeur_texte.split(",") if x.strip()]
                elif nom == "StartCutIndex":
                    # ON FORCE L'ENTIER ICI
                    params[nom] = int(float(valeur_texte))
                else:
                    # Pour les autres champs, on reste sur un float unique
                    params[nom] = float(valeur_texte)
            except ValueError:
                QMessageBox.critical(self, "Erreur", f"Le champ '{nom}' est invalide.")
                return

        # 3. Récupération des colonnes sélectionnées (Checkboxes)
        selected_columns = [cb.text() for cb in self.check_list if cb.isChecked()]
        if not selected_columns:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner au moins une sonde.")
            return

        # 4. Chargement des données et instanciation de la classe Decomposition
        try:
            data_full = pd.read_csv(self.fichier)
            col_temps = data_full.columns[0]
            data = data_full[[col_temps] + selected_columns]
            print(f"Colonnes envoyées : {selected_columns}")
            # On crée l'objet en passant les arguments attendus par ton __init__
            # Note: J'utilise .get() pour éviter les erreurs si la clé n'existe pas dans le formulaire
            obj = Decomposition(
                data=data,
                ProbeSpacing=params.get("ProbeSpacing"),
                depth=params.get("Depth", 2.0),  # Valeur par défaut si absent
                Irreg=self.irreg_true.isChecked()
            )


            # 5. Appel de la méthode spécifique
            # Ici on teste directement WaveProbeDecomposition
            if self.method_selected == "WaveProbeDecomposition":
                ai, ar = obj.WaveProbeDecomposition(selected_columns,params.get("StartCutIndex"))
                QMessageBox.information(self, "Résultat", f"Incident (Ai): {ai:.4f}\nRéfléchi (Ar): {ar:.4f}")
            else:
                QMessageBox.information(self, "Info", f"La méthode {self.method_selected} n'est pas encore liée.")

        except Exception as e:
            QMessageBox.critical(self, "Erreur de calcul", f"Détails : {str(e)}")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Test avec une liste de colonnes
    window = LaboInterface()
    window.show()
    sys.exit(app.exec())