from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PySide6.QtCore import Qt, Signal
from database.backup_manager import BackupManager

class BackupRollbackView(QWidget):
    db_restored = Signal()

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header Card
        header_card = QFrame()
        header_card.setProperty("class", "card-widget")
        hc_layout = QHBoxLayout(header_card)

        lbl_title = QLabel("Database Safety Backup & Version Rollback Manager")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #F8FAFC;")

        btn_manual_backup = QPushButton("+ Create Manual Backup Now")
        btn_manual_backup.setProperty("class", "primary-btn")
        btn_manual_backup.clicked.connect(self.create_manual_backup)

        hc_layout.addWidget(lbl_title)
        hc_layout.addStretch()
        hc_layout.addWidget(btn_manual_backup)
        layout.addWidget(header_card)

        # Backup History Table Card
        table_card = QFrame()
        table_card.setProperty("class", "card-widget")
        tc_layout = QVBoxLayout(table_card)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Timestamp", "Trigger Action", "Student Count", "SHA-256 Checksum", "File Name"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        tc_layout.addWidget(self.table)
        layout.addWidget(table_card)

        # Footer Action Row
        footer_layout = QHBoxLayout()
        btn_rollback = QPushButton("Rollback Database to Selected Backup")
        btn_rollback.setProperty("class", "danger-btn")
        btn_rollback.clicked.connect(self.rollback_to_selected)

        footer_layout.addStretch()
        footer_layout.addWidget(btn_rollback)
        layout.addLayout(footer_layout)

        self.refresh_backups()

    def refresh_backups(self):
        try:
            backups = BackupManager.list_backups()
            self.table.setRowCount(0)
            for b in backups:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(b["id"])))
                self.table.setItem(row, 1, QTableWidgetItem(b["created_at"].strftime("%Y-%m-%d %H:%M:%S")))
                self.table.setItem(row, 2, QTableWidgetItem(b["trigger_action"]))
                self.table.setItem(row, 3, QTableWidgetItem(f"{b['student_count']:,}"))
                self.table.setItem(row, 4, QTableWidgetItem(b["checksum"][:12] + "..."))
                self.table.setItem(row, 5, QTableWidgetItem(b["filename"]))
        except Exception as e:
            QMessageBox.critical(self, "Backup Manager Error", str(e))

    def create_manual_backup(self):
        try:
            b = BackupManager.create_backup(trigger_action="USER_MANUAL_BACKUP")
            QMessageBox.information(self, "Backup Created", f"Successfully created backup '{b.filename}'!")
            self.refresh_backups()
        except Exception as e:
            QMessageBox.critical(self, "Backup Error", str(e))

    def rollback_to_selected(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a backup row to restore.")
            return

        backup_id = int(self.table.item(selected, 0).text())
        filename = self.table.item(selected, 5).text()

        reply = QMessageBox.question(
            self,
            "Confirm Database Rollback",
            f"ARE YOU SURE you want to rollback the database to backup #{backup_id} ({filename})?\n\n"
            "A safety snapshot of your current database state will be saved automatically prior to rollback.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                BackupManager.restore_backup(backup_id)
                QMessageBox.information(self, "Rollback Successful", "Database restored successfully!")
                self.refresh_backups()
                self.db_restored.emit()
            except Exception as e:
                QMessageBox.critical(self, "Rollback Error", str(e))
