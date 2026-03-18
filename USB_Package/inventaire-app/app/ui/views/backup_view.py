"""
backup_view.py — Vue de sauvegarde et restauration intégrée.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFileDialog, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView,
)

from ...core.backup_manager import (
    create_backup, restore_backup, verify_backup, list_backups,
)


class BackupView(QWidget):
    """Écran de sauvegarde / restauration."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        title = QLabel("Sauvegarde & Restauration")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        desc = QLabel(
            "Sauvegardez votre base de données et vos paramètres dans un fichier ZIP. "
            "Restaurez à tout moment depuis une sauvegarde précédente. "
            "Une sauvegarde automatique est créée à chaque lancement."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # ── Actions ──
        grp_actions = QGroupBox("Actions")
        actions_layout = QHBoxLayout(grp_actions)

        btn_save = QPushButton("  Sauvegarder maintenant")
        btn_save.setMinimumHeight(44)
        btn_save.setMinimumWidth(200)
        btn_save.clicked.connect(self._manual_backup)
        actions_layout.addWidget(btn_save)

        btn_save_as = QPushButton("  Sauvegarder vers…")
        btn_save_as.setObjectName("btnSecondary")
        btn_save_as.setMinimumHeight(44)
        btn_save_as.setMinimumWidth(200)
        btn_save_as.clicked.connect(self._save_as)
        actions_layout.addWidget(btn_save_as)

        btn_restore = QPushButton("  Restaurer depuis…")
        btn_restore.setObjectName("btnFlat")
        btn_restore.setMinimumHeight(44)
        btn_restore.setMinimumWidth(200)
        btn_restore.clicked.connect(self._restore)
        actions_layout.addWidget(btn_restore)

        actions_layout.addStretch()
        layout.addWidget(grp_actions)

        # ── Liste des sauvegardes ──
        grp_list = QGroupBox("Sauvegardes disponibles")
        list_layout = QVBoxLayout(grp_list)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Nom", "Date", "Taille", "Type"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        list_layout.addWidget(self.table)

        btn_bar = QHBoxLayout()
        btn_refresh = QPushButton("Actualiser")
        btn_refresh.setObjectName("btnFlat")
        btn_refresh.clicked.connect(self._refresh_list)
        btn_bar.addWidget(btn_refresh)

        btn_restore_sel = QPushButton("Restaurer la sélection")
        btn_restore_sel.clicked.connect(self._restore_selected)
        btn_bar.addWidget(btn_restore_sel)

        btn_bar.addStretch()
        list_layout.addLayout(btn_bar)
        layout.addWidget(grp_list)

        # ── Status ──
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addStretch()
        self._refresh_list()

    def refresh(self):
        self._refresh_list()

    def _refresh_list(self):
        backups = list_backups()
        self.table.setRowCount(len(backups))
        self._backups = backups
        for i, b in enumerate(backups):
            self.table.setItem(i, 0, QTableWidgetItem(b["name"]))
            self.table.setItem(i, 1, QTableWidgetItem(b["date"]))
            self.table.setItem(i, 2, QTableWidgetItem(b["size"]))
            self.table.setItem(i, 3, QTableWidgetItem("Auto" if b["is_auto"] else "Manuel"))

    def _manual_backup(self):
        try:
            path = create_backup()
            self.status_label.setText(f"✅  Sauvegarde créée : {path.name}")
            self._refresh_list()
            QMessageBox.information(self, "Succès", f"Sauvegarde créée :\n{path}")
        except Exception as e:
            self.status_label.setText(f"❌  Erreur : {e}")
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la sauvegarde :\n{e}")

    def _save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer la sauvegarde", "backup_inventaire.zip",
            "Fichiers ZIP (*.zip)",
        )
        if not path:
            return
        try:
            result = create_backup(path)
            self.status_label.setText(f"✅  Sauvegarde : {result.name}")
            QMessageBox.information(self, "Succès", f"Sauvegarde créée :\n{result}")
        except Exception as e:
            self.status_label.setText(f"❌  Erreur : {e}")
            QMessageBox.critical(self, "Erreur", f"Erreur :\n{e}")

    def _restore(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner la sauvegarde", "",
            "Fichiers ZIP (*.zip)",
        )
        if not path:
            return
        self._do_restore(path)

    def _restore_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une sauvegarde.")
            return
        idx = rows[0].row()
        path = self._backups[idx]["path"]
        self._do_restore(path)

    def _do_restore(self, path: str):
        # Vérification d'abord
        ok, msg = verify_backup(path)
        if not ok:
            QMessageBox.critical(self, "Sauvegarde invalide", msg)
            return

        reply = QMessageBox.question(
            self, "Confirmer la restauration",
            f"Restaurer depuis cette sauvegarde ?\n\n{msg}\n\n"
            "Une sauvegarde de sécurité sera créée avant la restauration.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        ok, msg = restore_backup(path)
        if ok:
            self.status_label.setText(f"✅  {msg}")
            QMessageBox.information(
                self, "Restauration réussie",
                f"{msg}\n\nRedémarrez l'application pour appliquer les changements.",
            )
        else:
            self.status_label.setText(f"❌  {msg}")
            QMessageBox.critical(self, "Erreur", msg)
        self._refresh_list()
