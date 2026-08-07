from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QTableWidget, QTableWidgetItem, QProgressBar, QHeaderView,
    QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from database.connection import SessionLocal
from database.repository import Repository

class StatCard(QFrame):
    def __init__(self, title: str, value: str = "0", accent_color: str = "#38BDF8"):
        super().__init__()
        self.setProperty("class", "card-widget")
        self.setFrameShape(QFrame.StyledPanel)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setProperty("class", "card-title")
        
        self.lbl_val = QLabel(value)
        self.lbl_val.setProperty("class", "stat-value")
        self.lbl_val.setStyleSheet(f"color: {accent_color};")
        
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_val)

    def set_value(self, val: str):
        self.lbl_val.setText(str(val))


class DashboardView(QWidget):
    # Navigation signals to request tab changes from main window
    request_nav = Signal(str)
    data_changed = Signal()

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Title Header
        header_layout = QHBoxLayout()
        title_lbl = QLabel("Executive Dashboard")
        title_lbl.setStyleSheet("font-size: 22px; font-weight: bold; color: #F8FAFC;")
        
        self.btn_refresh = QPushButton("Refresh Data")
        self.btn_refresh.setProperty("class", "secondary-btn")
        self.btn_refresh.clicked.connect(self.refresh_dashboard)
        
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_refresh)
        main_layout.addLayout(header_layout)

        # 4 Metric Cards Grid
        grid = QGridLayout()
        grid.setSpacing(16)

        self.card_total = StatCard("Total Students", "0", "#38BDF8")
        self.card_groups = StatCard("Group Allocated", "0", "#10B981")
        self.card_venues = StatCard("Venue Allocated", "0", "#8B5CF6")
        self.card_pending = StatCard("Pending Allocation", "0", "#F59E0B")

        grid.addWidget(self.card_total, 0, 0)
        grid.addWidget(self.card_groups, 0, 1)
        grid.addWidget(self.card_venues, 0, 2)
        grid.addWidget(self.card_pending, 0, 3)
        main_layout.addLayout(grid)

        # Quick Actions Row
        actions_frame = QFrame()
        actions_frame.setProperty("class", "card-widget")
        act_layout = QHBoxLayout(actions_frame)
        
        lbl_act = QLabel("Quick Actions:")
        lbl_act.setStyleSheet("font-weight: bold; color: #94A3B8;")
        
        btn_imp = QPushButton("Upload Excel")
        btn_imp.setProperty("class", "primary-btn")
        btn_imp.clicked.connect(lambda: self.request_nav.emit("import"))

        btn_grp = QPushButton("Allocate Groups")
        btn_grp.setProperty("class", "secondary-btn")
        btn_grp.clicked.connect(lambda: self.request_nav.emit("group"))

        btn_ven = QPushButton("Allocate Venues")
        btn_ven.setProperty("class", "secondary-btn")
        btn_ven.clicked.connect(lambda: self.request_nav.emit("venue"))

        btn_exp = QPushButton("Export Reports")
        btn_exp.setProperty("class", "secondary-btn")
        btn_exp.clicked.connect(lambda: self.request_nav.emit("export"))

        act_layout.addWidget(lbl_act)
        act_layout.addWidget(btn_imp)
        act_layout.addWidget(btn_grp)
        act_layout.addWidget(btn_ven)
        act_layout.addWidget(btn_exp)
        act_layout.addStretch()
        main_layout.addWidget(actions_frame)

        # Recent Imports Table Card
        table_card = QFrame()
        table_card.setProperty("class", "card-widget")
        tc_layout = QVBoxLayout(table_card)

        # Header with Delete Option
        table_header_layout = QHBoxLayout()
        lbl_recent = QLabel("Recent Data Import History")
        lbl_recent.setStyleSheet("font-size: 15px; font-weight: bold; color: #F8FAFC;")
        
        btn_delete_import = QPushButton("🗑️ Delete Selected Import File")
        btn_delete_import.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: #FFFFFF;
                border: none;
                padding: 6px 14px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
            QPushButton:pressed {
                background-color: #B91C1C;
            }
        """)
        btn_delete_import.clicked.connect(self.delete_selected_import)

        table_header_layout.addWidget(lbl_recent)
        table_header_layout.addStretch()
        table_header_layout.addWidget(btn_delete_import)
        tc_layout.addLayout(table_header_layout)
        
        self.recent_table = QTableWidget(0, 5)
        self.recent_table.setHorizontalHeaderLabels(["Import Date", "File Name", "Total Rows", "New Records", "Duplicates"])
        self.recent_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.recent_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recent_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.recent_table.setSelectionMode(QAbstractItemView.SingleSelection)

        tc_layout.addWidget(self.recent_table)
        main_layout.addWidget(table_card)

        self.refresh_dashboard()

    def refresh_dashboard(self):
        session = SessionLocal()
        try:
            stats = Repository.get_dashboard_summary(session)
            self.card_total.set_value(f"{stats['total_students']:,}")
            self.card_groups.set_value(f"{stats['allocated_groups']:,}")
            self.card_venues.set_value(f"{stats['allocated_venues']:,}")
            self.card_pending.set_value(f"{stats['pending_allocation']:,}")

            # Populate recent imports table
            self.recent_table.setRowCount(0)
            for imp in stats['recent_imports']:
                row = self.recent_table.rowCount()
                self.recent_table.insertRow(row)
                
                date_item = QTableWidgetItem(imp.imported_at.strftime("%Y-%m-%d %H:%M"))
                file_item = QTableWidgetItem(imp.file_name)
                file_item.setData(Qt.UserRole, imp.id)  # Store import record ID
                
                self.recent_table.setItem(row, 0, date_item)
                self.recent_table.setItem(row, 1, file_item)
                self.recent_table.setItem(row, 2, QTableWidgetItem(str(imp.total_rows)))
                self.recent_table.setItem(row, 3, QTableWidgetItem(str(imp.new_records)))
                self.recent_table.setItem(row, 4, QTableWidgetItem(str(imp.duplicate_records)))
        finally:
            session.close()

    def delete_selected_import(self):
        selected_rows = self.recent_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No File Selected", "Please click on an imported file row in the table below to select it for deletion.")
            return

        row = selected_rows[0].row()
        file_item = self.recent_table.item(row, 1)
        if not file_item:
            return

        import_id = file_item.data(Qt.UserRole)
        file_name = file_item.text()

        confirm = QMessageBox.question(
            self,
            "Confirm Delete Import File",
            f"Are you sure you want to delete the import record for:\n\n📄 '{file_name}'?\n\n⚠️ WARNING: This will delete the import file record AND remove all students imported from this file from the system database!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            session = SessionLocal()
            try:
                success, msg = Repository.delete_import_history(session, import_id)
                if success:
                    QMessageBox.information(self, "Delete Successful", msg)
                    self.refresh_dashboard()
                    self.data_changed.emit()
                else:
                    QMessageBox.warning(self, "Delete Failed", msg)
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error Deleting Import Record", str(e))
            finally:
                session.close()
