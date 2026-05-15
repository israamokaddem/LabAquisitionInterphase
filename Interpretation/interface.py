import os

import cv2
import pyqtgraph as pg
import sys

from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QComboBox, QLineEdit,
                             QLabel, QFormLayout, QFrame, QCheckBox, QButtonGroup, QRadioButton, QFileDialog,
                             QMessageBox, QGroupBox, QScrollArea, QPlainTextEdit)

from Interpretation.Moteur import decomposition
import pandas as pd
import numpy as np
from Interpretation.Moteur.dsp import DSP
from Interpretation.Moteur.Imagerie import Imagerie
import time


class LaboInterface(QMainWindow):
    def __init__(self):

        # On définit la config avant super() pour être sûr qu'elle existe
        self.img_redressee = None
        self.fichier = None
        self.layout_chks = QHBoxLayout()
        self.param = None
        self.CONFIG_PARAMETRES = {
            "WaveProbeDecomposition": ["ProbeSpacing", "Depth"],  # on definit pout chaque methode les parametres
            "Decomposition_LiuHuang": ["ProbeSpacing", "Depth", "Fréquence", "order"],
            "Decomposition_EldrupAnderson": ["ProbeSpacing", "Depth", "Fréquence", "order"],
            "Standard": [],
            "Imagerie": ["Pattern_X", "Pattern_Y", "Sigma_Flatfield"]
        }

        self.UNITES = {
            "Taille_Carre_cm": "cm",
            "Sigma_Flatfield": "σ",
            "Pattern X": "points",
            "Pattern Y": "points",
            "ProbeSpacing": "m",
            "Depth": "m",
            "Fréquence": "Hz",
            "Offset_Batteur": "cm"
        }

        super().__init__()
        # Initialisation de tes variables
        self.check_list = []
        self.champs = {}  # Dictionnaire pour stocker les QLineEdit du formulaire
        self.data_columns = []
        self.irreg_true = None
        self.irreg_false = None
        self.method_selected = "menu1"
        self.data = None
        self.legend_object = None
        self.moteur_imagerie = Imagerie()
        self.image_redressee = None

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

        # -----------------------------------Bouton de Tuto----------------------------------------------
        self.layout_tuto = QHBoxLayout()
        self.btn_tuto = QPushButton("?")

        # Un petit bouton rond ou avec un point d'interrogation
        self.btn_tuto.setFixedSize(30, 30)  # On le fait petit et carré
        self.btn_tuto.setToolTip("Cliquer pour voir le tutoriel")
        self.btn_tuto.clicked.connect(self.afficher_tutoriel)
        self.btn_tuto.click()

        self.layout_tuto.addStretch()  # Pousse le bouton vers la droite
        self.layout_tuto.addWidget(self.btn_tuto)
        self.main_layout.addLayout(self.layout_tuto)

        # ---------------------ZONE d'insertion fichier --------------------------------------------------------------

        layout_fichier = QHBoxLayout()
        self.input_fichier = QLineEdit()
        self.input_fichier.setPlaceholderText("Chemin du fichier...")
        self.btn_valider = QPushButton("Parcourrrir")
        self.btn_valider.clicked.connect(self.parcourir_fichier)
        layout_fichier.addWidget(self.input_fichier)
        layout_fichier.addWidget(self.btn_valider)

        self.main_layout.addLayout(layout_fichier)

        # --------------------Insertion des boutons de selection de colonnes -----------------------------------
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)

        self.scrollArea.setMaximumHeight(60)
        self.chks_container = QWidget()
        # ajout du layout au container
        self.chks_container.setLayout(self.layout_chks)
        # ajout du container au scroll Area
        self.scrollArea.setWidget(self.chks_container)
        # ajout du scroll area au main layout
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

        # ----------------------------ZONE BAS: boutton de traitement -----------------------------------------------
        self.layout_gauche.addStretch()
        self.btn_entree = QPushButton("Spectre")
        self.btn_entree.setFixedHeight(50)

        self.btn_entree.clicked.connect(self.lancer_calcul_final)

        # ----------------- AJOUT DU WIDGET GRAPHIQUE (Obligatoire pour afficher) -------------------------------------

        self.btn_zoom = QPushButton("Zoomer graph")  # Ou une icône d'agrandissement
        self.btn_zoom.setFixedWidth(150)
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
        self.btn_vueSonde = QPushButton("Fréquence temporelle")
        self.btn_vueSonde.clicked.connect(self.action_afficher_graphique)
        self.layout_droite.addWidget(self.btn_vueSonde)

        self.layout_droite.addLayout(layout_VueSondes)
    #-------------------------------------------------------------------------------------------
     #Initialisation de layout et boutons de la methode imagerie
    #--------------------------------------------------------------------------------------------
        self.status_bar = self.statusBar()
        self.btn_calibrer = QPushButton("Calibrer l'image")
        self.btn_calibrer.setFixedHeight(50)
        self.btn_calibrer.hide()
        self.btn_detect_surface = QPushButton("Détection Surface Libre")
        self.btn_detect_surface.hide()

        self.btn_redresser = QPushButton("Redresser l'image")
        self.btn_redresser.setFixedHeight(50)
        self.btn_redresser.hide()

        self.layout_droite.addWidget(self.btn_calibrer)
        self.layout_droite.addWidget(self.btn_redresser)
        self.layout_droite.addWidget(self.btn_detect_surface)



        self.btn_calibrer.clicked.connect(self.lancer_calibration)
        self.btn_redresser.clicked.connect(self.lancer_redressement)
        self.btn_detect_surface.clicked.connect(self.lancer_detection_surface)

        # -------------terminal ----------
        self.console_output = QPlainTextEdit()
        self.console_output.setReadOnly(True)  # On ne veut pas que l'utilisateur écrive dedans
        self.console_output.setMaximumHeight(150)
        self.label_console = QLabel("Logs Console :")
        # Pour qu'elle ne prenne pas toute la place
        self.console_output.setStyleSheet(
            "background-color: black; color: #00FF00; font-family: Courier;")  # Look "Matrix"
        self.layout_droite.addWidget(self.label_console)
        self.layout_droite.addWidget(self.console_output)

        # -------------------------------ZONE HAUT menus ----------------------------------------
        layout_haut = QHBoxLayout()
        self.menu1 = QComboBox()
        self.menu1.setObjectName("menu1")
        self.menu1.addItems(["WaveProbeDecomposition", "Decomposition_EldrupAnderson", "Decomposition_LiuHuang"])
        self.menu1.currentTextChanged.connect(self.update_form)

        self.menu2 = QComboBox()
        self.menu2.addItems(["Standard", "Conjuguee"])
        # Optionnel : connecter aussi menu2 et menu3 si je veux qu'ils changent le formulaire
        self.menu2.currentTextChanged.connect(self.update_form)
        self.menu3 = QComboBox()
        self.menu3.addItems(["Imagerie"])
        self.menu3.textActivated.connect(self.update_form)

        layout_haut.addWidget(self.menu1)
        layout_haut.addWidget(self.menu2)
        layout_haut.addWidget(self.menu3)
        self.layout_gauche.addLayout(layout_haut)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        self.layout_gauche.addWidget(line)

        self.irregular()

        # -----------------------------------------Zone du Formulaire---------------------------------
        self.form_layout = QFormLayout()
        self.layout_gauche.addLayout(self.form_layout)
        # Appel initial pour remplir le formulaire au démarrage
        self.update_form(self.menu1.currentText())

        # --- menu deroulant du formulaire
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

        # Ajout du bouton de d'execution cree auparavant en fin de page
        self.layout_gauche.addWidget(self.btn_entree)

        self.update_form(self.menu1.currentText())

        # Redirection console
        sys.stdout = StreamToConsole(self.console_output)
        self.label_console.hide()
        self.console_output.hide()

    # ----------------------------------------Methodes d'action des boutons------------------------------------------
    def layout_columns(self):
        # 1. On nettoie le layout (on enlève les anciennes colonnes s'il y en a)
        while self.layout_chks.count():
            item = self.layout_chks.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # on cree le layout des colonnes
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
        # 1. Identifier quel menu a envoyé le signal
        emetteur = self.sender()

        # 2. Si l'appel vient d'un clic utilisateur, on met à jour le style
        if isinstance(emetteur, QComboBox):
            self.rafraichir_style_menus(emetteur)

        self.gerer_affichage_droite(choix_menu)

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
            unite = self.UNITES.get(nom, "")
            self.param = QLineEdit()

            if nom == "ProbeSpacing":
                self.param.setText("0.0,0.3,0.7,1.2")
            # Si une unité existe, on l'affiche entre parenthèses dans le placeholder
            if unite:
                self.param.setPlaceholderText(f"Valeur pour {nom} ({unite})")
            else:
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

        if self.method_selected == "Imagerie":
            filtre = "Images (*.png *.jpg *.jpeg *.bmp *.tif)"
            titre = "Sélectionner l'image de calibration"
        else:
            filtre = "Fichiers CSV (*.csv);;Fichiers Excel (*.xlsx *.xls)"
            titre = "Sélectionner le fichier de données"

        self.fichier, _ = QFileDialog.getOpenFileName(self, titre, "", filtre)
        # Si l'utilisateur a choisi un fichier
        if self.fichier:
            self.input_fichier.setText(self.fichier)

            try:
                if self.method_selected == "Imagerie":
                    # Pour l'imagerie, on ne lit pas de colonnes CSV
                    # On réinitialise l'affichage des colonnes (si besoin)
                    self.data_columns = []
                    self.layout_columns()
                    # On pourrait ici afficher un aperçu de l'image si vous le souhaitez
                    print(f"Image chargée pour calibration : {self.fichier}")

                else:  # 1. On lit uniquement la première ligne (l'en-tête) du fichier
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
                       f"1er Ordre - Inc (Ai1): {ai1.real:.4f} / Réf (Ar1): {ar1.real:.4f}\n"
                       f"Lié (Bound) - Inc: {aib.real:.4f} / Réf: {arb.real:.4f}\n"
                       f"Libre (Free) - Inc: {aif.real:.4f} / Réf: {arf.real:.4f}")
                QMessageBox.information(self, "Résultat", msg)

            elif self.method_selected == "Decomposition_EldrupAnderson":
                om = params.get("omega", 1.0)
                ord_val = int(params.get("order", 2))

                ai1, ar1, aib, arb, aif, arf = obj.Decomposition_EldrupAnderson(selected_columns, om, ord_val)

                msg = (f"Méthode : Eldrup & Anderson (Non-linéaire)\n\n"
                       f"1er Ordre - Inc: {ai1.real:.4f} / Réf: {ar1.real:.4f}\n"
                       f"Lié (Bound) - Inc: {aib.real:.4f} / Réf: {arb.real:.4f}")
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
            sondes = [cb.text() for cb in self.check_list if cb.isChecked()]
            for i, col in enumerate(sondes):
                color = colors[i % len(colors)]
                pen = pg.mkPen(color=color, width=2)
                self.graphWidget.plot(x_axis, donnees[col], pen=pen, name=col)
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
        self.graphWidget.setLabel('left', "Fréquence", units="Hz")
        self.graphWidget.setLabel('bottom', "Time", units="s")

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

    def gerer_affichage_droite(self, choix_menu):
        """Affiche le graphique OU les boutons d'imagerie selon le menu sélectionné."""

        # Sécurité si l'interface n'est pas encore totalement chargée
        if not hasattr(self, 'btn_calibrer'):
            return

        if choix_menu == "Imagerie":
            # 1. On cache tout ce qui concerne l'analyse de signaux
            self.btn_entree.hide()
            self.graphWidget.hide()
            self.btn_zoom.hide()
            self.btn_vueSonde.hide()
            self.btn_entree.hide()


            # ---> NOUVEAU : On cache la zone des colonnes <---
            self.scrollArea.hide()

            # 2. On affiche les boutons d'imagerie
            self.btn_calibrer.show()
            self.btn_redresser.show()
            self.btn_detect_surface.show()
            # --- AJOUT : Afficher la console ---
            self.label_console.show()
            self.console_output.show()


        else:
            # 1. On réaffiche les éléments graphiques
            self.graphWidget.show()
            self.btn_zoom.show()
            self.btn_vueSonde.show()
            self.btn_entree.show()

            # --- AJOUT : Cacher la console ---
            self.label_console.hide()
            self.console_output.hide()


            # ---> NOUVEAU : On réaffiche la zone des colonnes <---
            self.scrollArea.show()

            # 2. On cache les boutons d'imagerie
            self.btn_calibrer.hide()
            self.btn_redresser.hide()

    def lancer_calibration(self):
        # vider les anciens points selectionnes chque clique sur le bouton calibrer
        self.moteur_imagerie.polygon_points = []
        self.moteur_imagerie.base_image = None

        if not hasattr(self, 'fichier') or not self.fichier:
            self.status_bar.showMessage("Erreur : Aucun fichier chargé")
            return

        # 1. Charger l'image
        img = cv2.imread(self.fichier)
        if img is None:
            self.status_bar.showMessage("Erreur : Impossible de lire l'image")
            return

        # Récupération dynamique du pattern depuis le formulaire
        try:
            nx = int(self.champs.get("Pattern_X").text())
            ny = int(self.champs.get("Pattern_Y").text())
            pattern = (nx, ny)
        except (ValueError, AttributeError):
            pattern = (9, 6)  # Valeur par défaut si vide

        # 2. Définir un NOM DE FENÊTRE UNIQUE
        nom_fenetre = "Selectionnez la zone du damier"

        # 3. CRÉER la fenêtre d'abord
        cv2.namedWindow(nom_fenetre, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(nom_fenetre, 1000, 700)  # Taille gérable à l'écran

        # 4. LIER la souris à cette fenêtre précise
        # On passe 'img' en paramètre pour que select_zone puisse dessiner dessus
        cv2.setMouseCallback(nom_fenetre, self.moteur_imagerie.select_zone, param=img)

        self.status_bar.showMessage("Cliquez sur les 4 coins, puis CLIC DROIT pour valider.")

        # 5. BOUCLE D'AFFICHAGE (pour voir les points en temps réel)
        while True:
            # On crée une copie pour ne pas dessiner indéfiniment sur l'originale
            img_display = img.copy()

            # Dessiner les points déjà sélectionnés
            for pt in self.moteur_imagerie.polygon_points:
                cv2.circle(img_display, pt, 10, (0, 255, 0), -1)

            # Dessiner la ligne élastique vers le curseur si on sélectionne
            if len(self.moteur_imagerie.polygon_points) > 0 and self.moteur_imagerie.selecting:
                cv2.line(img_display, self.moteur_imagerie.polygon_points[-1],
                         self.moteur_imagerie.current_point, (255, 0, 0), 2)

            cv2.imshow(nom_fenetre, img_display)

            key = cv2.waitKey(1) & 0xFF
            # Sortir si on appuie sur 'Echap' ou si l'utilisateur a fini (clic droit géré dans moteur)
            if key == 27 or not cv2.getWindowProperty(nom_fenetre, cv2.WND_PROP_VISIBLE):
                break
            if not self.moteur_imagerie.selecting and len(self.moteur_imagerie.polygon_points) >= 3:
                # Attend une petite seconde pour voir le dernier point puis ferme
                time.sleep(0.5)
                break

        cv2.destroyAllWindows()
        self.status_bar.showMessage("Zone sélectionnée. Analyse des coins...")

        # 6. Lancer la détection auto
        self.moteur_imagerie.detecter_coins_dans_zone(self.fichier, pattern=pattern)

        self.moteur_imagerie.calculer_coordonnees_physiques(pattern=pattern)

    def lancer_redressement(self):
        img = cv2.imread(self.fichier)
        # Application du flatfield si sigma est renseigné
        sigma = self.champs.get("Sigma_Flatfield").text()
        if sigma:
            img = self.moteur_imagerie.imflatfield(img, float(sigma))

        px = int(self.champs.get("Pattern_X").text()) if self.champs.get("Pattern_X") else 9
        py = int(self.champs.get("Pattern_Y").text()) if self.champs.get("Pattern_Y") else 6

        self.moteur_imagerie.calculer_coordonnees_physiques(spacing_cm=4.0, pattern=(px, py))

        self.img_redressee = self.moteur_imagerie.calculer_homographie_et_redresser(img)

        if self.img_redressee is not None:
            cv2.destroyAllWindows()
            cv2.imshow("Image Redressee", self.img_redressee)
            cv2.waitKey(1)




    def lancer_detection_surface(self):
        try:
            # 1. On vérifie si une image a été redressée au préalable
            if self.img_redressee is None:
                QMessageBox.warning(self, "Erreur", "Veuillez d'abord redresser l'image.")
                return

            print("Lancement de la détection de la surface libre...")

            # 2. On transmet l'image actuelle au moteur pour qu'il travaille dessus
            self.moteur_imagerie.img_redressee = self.img_redressee

            # 3. On appelle la méthode de calcul du moteur
            success= self.moteur_imagerie.detecter_surface_libre_et_recaler()


        except Exception as e:
            # Si tu as encore une erreur de "unpack", vérifie bien que TOUS les
            # return de Imagerie.py ne renvoient qu'une seule valeur.
            QMessageBox.critical(self, "Erreur", f"Erreur : {str(e)}")


    def rafraichir_style_menus(self, menu_actif):
        # Liste de tous vos menus
        tous_les_menus = [self.menu1, self.menu2, self.menu3]

        # Style Vert (Fond vert, Texte noir)
        style_vert = """
            QComboBox { 
                background-color: #00FF00; 
                color: black; 
                font-weight: bold; 
                border: 2px solid #008000; 
                border-radius: 5px;
            }
        """
        # Style Normal (On remet à vide pour que le style.qss reprenne la main)
        style_normal = "QComboBox { background-color: white; color: none; border: none; }"

        for menu in tous_les_menus:
            if menu == menu_actif:
                menu.setStyleSheet(style_vert)
            else:
                # On réinitialise le style pour que le menu redevienne normal
                menu.setStyleSheet(style_normal)


def charger_style(app):
    with open("style.qss", "r") as f:
        app.setStyleSheet(f.read())


import sys


class StreamToConsole:
    def __init__(self, console_widget):
        self.console_widget = console_widget

    def write(self, text):
        if text.strip():  # On ignore les lignes vides
            self.console_widget.appendPlainText(text.strip())

    def flush(self):
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    charger_style(app)
    # Test avec une liste de colonnes
    window = LaboInterface()
    window.show()
    sys.exit(app.exec())
