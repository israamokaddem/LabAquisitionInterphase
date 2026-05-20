import pyqtgraph as pg
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QComboBox, QLineEdit,
                             QLabel, QFormLayout, QFrame, QCheckBox, QButtonGroup, QRadioButton, QFileDialog,
                             QMessageBox, QGroupBox, QScrollArea)


from Interpretation.Moteur import decomposition
import pandas as pd
import numpy as np
from Interpretation.Moteur.dsp import DSP


class LaboInterface(QMainWindow):
    def __init__(self):

        # On définit la config avant super() pour être sûr qu'elle existe
        self.layout_chks = QHBoxLayout()
        self.param = None
        self.CONFIG_PARAMETRES = {
            "WaveProbeDecomposition": ["ProbeSpacing", "Depth"],  #on definit pout chaque methode les parametres
            "Decomposition_LiuHuang": ["ProbeSpacing", "Depth","Fréquence","order"],
            "Decomposition_EldrupAnderson": ["ProbeSpacing", "Depth","Fréquence","order"],
            "Standard": [],
            "Imagerie": ["Sigma_Flatfield", "Taille_Carre_cm", "Offset_Batteur"]
        }


        super().__init__()
        # Initialisation de tes variables
        self.check_list = []
        self.champs = {}  # Dictionnaire pour stocker les QLineEdit du formulaire
        self.data_columns =[]
        self.irreg_true = None
        self.irreg_false = None
        self.method_selected="menu1"
        self.data=None
        self.legend_object = None

        self.setWindowTitle("Interface de Traitement de Données")
        self.resize(800, 600)


        # --- 1. CONFIGURATION DU SCROLL AREA ---
        self.main_scroll_area = QScrollArea()
        self.main_scroll_area.setWidgetResizable(True)
        self.setCentralWidget(self.main_scroll_area)
        self.container_widget = QWidget()
        self.main_layout = QVBoxLayout(self.container_widget)
        self.main_scroll_area.setWidget(self.container_widget)

        # --- 2. LAYOUT HORIZONTAL PRINCIPAL (Division Gauche/Droite) ---
        self.Horizontal_layout = QHBoxLayout(self.container_widget)



        #-----------------------------------Bouton de Tuto----------------------------------------------
        self.layout_tuto=QHBoxLayout()
        self.btn_tuto = QPushButton("?")

        # Un petit bouton rond ou avec un point d'interrogation
        self.btn_tuto.setFixedSize(30, 30)  # On le fait petit et carré
        self.btn_tuto.setToolTip("Cliquer pour voir le tutoriel")
        self.btn_tuto.clicked.connect(self.afficher_tutoriel)
        self.btn_tuto.click()

        self.layout_tuto.addStretch()  # Pousse le bouton vers la droite
        self.layout_tuto.addWidget(self.btn_tuto)
        self.main_layout.addLayout(self.layout_tuto)


        #---------------------ZONE d'insertion fichier --------------------------------------------------------------

        layout_fichier = QHBoxLayout()
        self.input_fichier = QLineEdit()
        self.input_fichier.setPlaceholderText("Chemin du fichier...")
        self.btn_valider = QPushButton("Parcourrrir")
        self.btn_valider.clicked.connect(self.parcourir_fichier)
        layout_fichier.addWidget(self.input_fichier)
        layout_fichier.addWidget(self.btn_valider)
        self.main_layout.addLayout(layout_fichier)

       #--------------------Insertion des boutons de selection de colonnes -----------------------------------
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)

        self.chks_container=QWidget()
        #ajout du layout au container
        self.chks_container.setLayout(self.layout_chks)
        #ajout du container au scroll Area
        self.scrollArea.setWidget(self.chks_container)
        #ajout du scroll area au main layout
        self.main_layout.addWidget(self.scrollArea)

        # --- Ajout de la Zone Horizontale
        self.main_layout.addLayout(self.Horizontal_layout)

        # --- 3. ZONE GAUCHE (Formulaire et Menus) ---
        self.zone_gauche_widget = QWidget()
        self.layout_gauche = QVBoxLayout(self.zone_gauche_widget)
        self.Horizontal_layout.addWidget(self.zone_gauche_widget)

        # --- 4. ZONE DROITE (Graphique et Visualisation) ---
        self.zone_droite_widget = QWidget()
        self.layout_droite = QVBoxLayout(self.zone_droite_widget)
        self.Horizontal_layout.addWidget(self.zone_droite_widget)  # Plus large

        # ----------------- AJOUT DU WIDGET GRAPHIQUE (Obligatoire pour afficher) -------------------------------------

        self.btn_zoom = QPushButton("Zoomer")  # Ou une icône d'agrandissement
        self.btn_zoom.setFixedWidth(10)
        self.btn_zoom.clicked.connect(self.gerer_clic_graphique)
        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setBackground('w')
        self.graphWidget.setMinimumHeight(200)
        self.layout_droite.addWidget(self.graphWidget)
        self.layout_droite.addWidget(self.btn_zoom)

      # --- AJOUT DU LAYOUT POUR L'ÉCHELLE ---
        self.layout_legende = QHBoxLayout()
        self.layout_droite.addLayout(self.layout_legende)

       # Creation du du layout
        layout_VueSondes = QVBoxLayout()
        #  Bouton: Afficher-sondes
        self.btn_vueSonde = QPushButton("Afficher sondes ")
        self.btn_vueSonde.clicked.connect(self.action_afficher_graphique)
        self.layout_droite.addWidget(self.btn_vueSonde)

        self.layout_droite.addLayout(layout_VueSondes)

        # -------------------------------ZONE HAUT menus ----------------------------------------
        layout_haut = QHBoxLayout()
        self.menu1 = QComboBox()
        self.menu1.addItems(["WaveProbeDecomposition", "Decomposition_EldrupAnderson", "Decomposition_LiuHuang"])
        self.menu1.currentTextChanged.connect(self.update_form)

        self.menu2 = QComboBox()
        self.menu2.addItems([ "Standard", "Conjuguee"])
        # Optionnel : connecter aussi menu2 et menu3 si je veux qu'ils changent le formulaire
        self.menu2.currentTextChanged.connect(self.update_form)
        self.menu3 = QComboBox()
        self.menu3.addItems(["Image1", "Image2", "Image3"])
        self.menu3.currentTextChanged.connect(self.update_form)

        layout_haut.addWidget(self.menu1)
        layout_haut.addWidget(self.menu2)
        layout_haut.addWidget(self.menu3)
        self.layout_gauche.addLayout(layout_haut)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        self.layout_gauche.addWidget(line)


      #-----------------------------------------Zone du Formulaire---------------------------------
        self.form_layout = QFormLayout()
        self.layout_gauche.addLayout(self.form_layout)
        # Appel initial pour remplir le formulaire au démarrage
        self.update_form(self.menu1.currentText())
        self.irregular() # ajout du bouton de selction de l'irregularite

      #--- menu deroulant du formulaire
        # 1. Votre formulaire principal actuel
        self.layout_gauche.addLayout(self.form_layout)

        # 2. Ajout d'une ligne de séparation (optionnel)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        self.layout_gauche.addWidget(line)

        # 3. LE NOUVEAU MENU DÉROULANT (Paramètres additionnels)
        # Dictionnaire pour stocker les nouveaux champs
        self.champs_optionnels = {}
        self.extra_args = {}

        self.layout_gauche.addWidget(QLabel("Paramètres Additionnels :"))
        self.menu_optionnel = QComboBox()
        self.menu_optionnel.addItems(["Gravity", "StartCutIndex", "Intégration"])
        self.menu_optionnel.currentTextChanged.connect(self.update_sous_formulaire)
        self.layout_gauche.addWidget(self.menu_optionnel)

        # 4. LE LAYOUT DYNAMIQUE (C'est ici qu'on ajoutera les QLineEdit)
        self.sous_form_layout = QFormLayout()
        self.layout_gauche.addLayout(self.sous_form_layout)





        #----------------------------ZONE BAS: boutton de traitement -----------------------------------------------
        self.layout_gauche.addStretch()
        self.btn_entree = QPushButton("EXÉCUTER LE TRAITEMENT")
        self.btn_entree.setFixedHeight(50)
        self.layout_gauche.addWidget(self.btn_entree)
        self.btn_entree.clicked.connect(self.lancer_calcul_final)




#----------------------------------------Methodes d'action des boutons------------------------------------------
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

        self.layout_gauche.addLayout(layout_Irregular)


    ''' def parcourir_fichier(self):
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
                self.data = pd.read_csv(self.fichier)


                # 2. On initialise data_columns avec la liste des noms de colonnes
                self.data_columns =self.data.columns.tolist()

                # 3. On appelle ta méthode existante pour mettre à jour l'affichage
                self.layout_columns()

            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Erreur", f"Impossible de lire les colonnes du fichier : {e}")
    '''

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
                self.data = pd.read_csv(self.fichier)

                # 2. On initialise data_columns avec la liste des noms de colonnes
                self.data_columns = self.data.columns.tolist()

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

                else:
                    # Pour les autres champs, on reste sur un float unique
                    params[nom] = float(valeur_texte)
            except ValueError:
                QMessageBox.critical(self, "Erreur", f"Le champ '{nom}' est invalide.")
                return

        self.extra_args = {}
        for nom, widget in self.champs_optionnels.items():
            valeur_texte = widget.text().strip()
            if valeur_texte:
                try:
                    # Mapping des noms de l'interface vers les arguments de decomposition.py
                    if nom == "StartCutIndex":
                        self.extra_args["startCutIndex"] = int(float(valeur_texte))
                    elif nom == "Gravity":
                        self.extra_args["g"] = float(valeur_texte)
                    elif nom == "IntegrationMin":
                        self.extra_args["f_min"] = float(valeur_texte)
                    elif nom == "IntegrationMax":
                        self.extra_args["f_max"] = float(valeur_texte)
                    else:
                        # Pour les autres, on garde le nom tel quel
                        self.extra_args[nom] = float(valeur_texte)
                except ValueError:
                    print(f"Erreur de conversion pour {nom}")

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
            moteur_dsp = DSP(
                data=data_full,
                selected_columns=selected_columns,
                time_column_index=0  # On suppose que le temps est en colonne 0
            )

            # 5. Appel de la méthode spécifique
            # Ici on teste directement WaveProbeDecomposition
            if self.method_selected == "WaveProbeDecomposition":
                ai, ar = obj.WaveProbeDecomposition(selected_columns, **self.extra_args)
                QMessageBox.information(self, "Résultat", f"Incident (Ai): {ai:.4f}\nRéfléchi (Ar): {ar:.4f}")
            elif self.method_selected == "Decomposition_LiuHuang":
                # Récupération de omega et order (valeurs par défaut si vides)
                om = params.get("omega", 1.0)
                ord_val = int(params.get("order", 2))

                ai1, ar1, aib, arb, aif, arf = obj.Decomposition_LiuHuang(selected_columns, om, ord_val)

                msg = (f"Méthode : Liu & Huang (Ordre {ord_val})\n\n"
                       f"1er Ordre - Inc (Ai1): {ai1:.4f} / Réf (Ar1): {ar1:.4f}\n"
                       f"Lié (Bound) - Inc: {aib:.4f} / Réf: {arb:.4f}\n"
                       f"Libre (Free) - Inc: {aif:.4f} / Réf: {arf:.4f}")
                QMessageBox.information(self, "Résultat", msg)

            elif self.method_selected == "Decomposition_EldrupAnderson":
                om = params.get("omega", 1.0)
                ord_val = int(params.get("order", 2))

                ai1, ar1, aib, arb, aif, arf = obj.Decomposition_EldrupAnderson(selected_columns, om, ord_val)

                msg = (f"Méthode : Eldrup & Anderson (Non-linéaire)\n\n"
                       f"1er Ordre - Inc: {ai1:.4f} / Réf: {ar1:.4f}\n"
                       f"Lié (Bound) - Inc: {aib:.4f} / Réf: {arb:.4f}")
                QMessageBox.information(self, "Résultat", msg)

            elif self.method_selected == "Standard":
                freq, resultats = moteur_dsp.executer_calcul(methode='Standard')
                self.afficher_graphique_dsp(freq, resultats)

            elif self.method_selected == "Conjuguee":
                freq, resultats = moteur_dsp.executer_calcul(methode='Conjuguee')
                self.afficher_graphique_dsp(freq, resultats)

            else:
                QMessageBox.information(self, "Info",
                                        f"La méthode {self.method_selected} est reconnue mais le traitement spécifique n'est pas codé.")


        except Exception as e:
            QMessageBox.critical(self, "Erreur de calcul", f"Détails : {str(e)}")

    def show_graph(self, donnees, titre="Graphique"):
        """
        Méthode centrale pour afficher des données.
        donnees : peut être un DataFrame Pandas ou un dictionnaire de listes.
        """
        # On efface tout avant d'afficher
        self.graphWidget.clear()
        if hasattr(self, 'legend_object') and self.legend_object is not None:
            # On retire l'objet du graphique
            self.graphWidget.removeItem(self.legend_object)
            self.legend_object = None

        self.graphWidget.setTitle(titre)
        self.legend_object = self.graphWidget.addLegend(offset=(30, 30))

        # Nettoyage du layout de l'échelle en bas
        while self.layout_legende.count():
            item = self.layout_legende.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Définition de couleurs standards
        colors = ['r', 'g', 'b', 'c', 'm', 'y', 'k']

        # CAS 1 : Si c'est un DataFrame Pandas
        if isinstance(donnees, pd.DataFrame):
            # On cherche une colonne 'Time' ou 't', sinon on utilise l'index
            x_axis = donnees['Time'] if 'Time' in donnees.columns else donnees.index
            sondes=[cb.text() for cb in self.check_list if cb.isChecked()]
            for i, col in enumerate(sondes):
                color = colors[i % len(colors)]
                pen = pg.mkPen(color=color, width=2)
                self.graphWidget.plot(x_axis, donnees[col], pen=pen,name=col)
                # Échelle en dessous
                lbl_color = QFrame()
                lbl_color.setFixedSize(10, 10)
                lbl_color.setStyleSheet(f"background-color: {color};")
                lbl_txt = QLabel(col)
                self.layout_legende.addWidget(lbl_color)
                self.layout_legende.addWidget(lbl_txt)
            self.layout_legende.addStretch()

        # CAS 2 : Si c'est une simple liste ou un array (ex: un résultat de calcul)
        elif isinstance(donnees, (list, np.ndarray)):
            pen = pg.mkPen(color='w', width=2)
            self.graphWidget.plot(donnees, pen=pen, name="Résultat")

    def action_afficher_graphique(self):
        # On appelle ta méthode show_graph en utilisant l'attribut de classe
          self.show_graph(self.data)

    def afficher_tutoriel(self):
        print("on rentre dans la methode")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Guide d'utilisation")

        # Texte du tutoriel (tu peux utiliser du HTML pour la mise en forme)
        tuto_texte = """
        <h2>Bienvenue dans l'interface de traitement</h2>
        <p>Suivez ces étapes pour analyser vos données :</p>
        <ol>
            <li><b>Importer un fichier :</b> Cliquez sur 'Parcourir' pour charger votre CSV.</li>
           <li><b>Visualiser :</b> Cliquez sur 'Afficher sondes' pour vérifier les signaux.</li>
             <li><b>Visualiser :</b> Cliquez sur 'A' en noir a gauche pour remettre a l'echelle.</li>
            <li><b>Sélectionner la méthode :</b> Choisissez votre methode dans le menu.</li>
            <li><b>Paramétrer :</b> Remplissez les champs (Profondeur, Omega, etc.).</li>
            <li><b>Exécuter :</b> Lancez le calcul final pour obtenir un graph ou un resulat</li>
        </ol>
        """
        msg.setText(tuto_texte)
        msg.exec()

    def afficher_graphique_dsp(self, freq, resultats):
        """
        Affiche la Densité Spectrale de Puissance.
        X = Fréquences (Hz)
        Y = Puissance (m²/Hz ou m².s)
        """
        self.graphWidget.clear()
        self.graphWidget.setTitle("Densité Spectrale de Puissance (DSP)")
        self.graphWidget.setLabel('left', "Densité", units="m².s")
        self.graphWidget.setLabel('bottom', "Fréquence", units="Hz")

        if hasattr(self, 'legend_object') and self.legend_object is not None:
            self.graphWidget.removeItem(self.legend_object)
        self.legend_object = self.graphWidget.addLegend()

        colors = ['r', 'g', 'b', 'c', 'm', 'y', 'k']

        for i, (col_name, dsp_values) in enumerate(resultats.items()):
            color = colors[i % len(colors)]
            pen = pg.mkPen(color=color, width=2)

            # On trace DSP en fonction de Freq
            self.graphWidget.plot(freq, dsp_values, pen=pen, name=f"DSP {col_name}")

    def gerer_clic_graphique(self):
            # Créer une nouvelle fenêtre temporaire
            self.zoom_win = QMainWindow()
            self.zoom_win.setWindowTitle("Zoom Graphique")


            # Créer un nouveau widget de graph qui copie les données
            zoom_graph = pg.PlotWidget()
            zoom_graph.setBackground('w')
            # On récupère tous les items du graph original pour les copier
            for item in self.graphWidget.listDataItems():
                zoom_graph.addItem(item)



            self.zoom_win.setCentralWidget(zoom_graph)
            self.zoom_win.resize(1000, 700)
            self.zoom_win.show()

    def update_sous_formulaire(self, choix):
        # 1. Nettoyage du layout précédent
        while self.sous_form_layout.count():
            child = self.sous_form_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.champs_optionnels = {}  # Reset du dictionnaire

        # 2. Définition des champs selon le choix
        nouveaux_champs = []
        if choix == "Intégration":
            nouveaux_champs = ["IntegrationMin", "IntegrationMax"]
        elif choix == "StartCutIndex":
            nouveaux_champs = ["StartCutIndex"]
        elif choix == "Gravity":
            nouveaux_champs = ["Gravity"]



        # 3. Création des widgets
        for nom in nouveaux_champs:
            champ = QLineEdit()
            self.sous_form_layout.addRow(f"{nom} :", champ)
            self.champs_optionnels[nom] = champ

def charger_style(app):
    with open("style.qss", "r") as f:
        app.setStyleSheet(f.read())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    charger_style(app)
    # Test avec une liste de colonnes
    window = LaboInterface()
    window.show()
    sys.exit(app.exec())