from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from database.connection import SessionLocal
from database.models import AuditLog

class LogsSettingsView(QWidget):
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

        lbl_title = QLabel("System Audit Logs & Security Trails")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #F8FAFC;")

        btn_refresh = QPushButton("Refresh Logs")
        btn_refresh.setProperty("class", "secondary-btn")
        btn_refresh.clicked.connect(self.refresh_logs)

        hc_layout.addWidget(lbl_title)
        hc_layout.addStretch()
        hc_layout.addWidget(btn_refresh)
        layout.addWidget(header_card)

        # Logs Table
        table_card = QFrame()
        table_card.setProperty("class", "card-widget")
        tc_layout = QVBoxLayout(table_card)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Action", "Entity Type", "Details"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        tc_layout.addWidget(self.table)
        layout.addWidget(table_card)

        self.refresh_logs()

    def refresh_logs(self):
        session = SessionLocal()
        try:
            logs = session.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()
            self.table.setRowCount(0)

            for log in logs:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(log.created_at.strftime("%Y-%m-%d %H:%M:%S")))
                self.table.setItem(row, 1, QTableWidgetItem(log.action))
                self.table.setItem(row, 2, QTableWidgetItem(log.entity_type))
                self.table.setItem(row, 3, QTableWidgetItem(log.details or ""))
        finally:
            session.close()
