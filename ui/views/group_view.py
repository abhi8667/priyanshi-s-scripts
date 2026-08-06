from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame, QMessageBox, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from database.connection import SessionLocal
from database.models import Student, Department
from engine.group_allocator import GroupAllocator

class GroupAllocationView(QWidget):
    allocation_done = Signal()

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Config Card
        config_card = QFrame()
        config_card.setProperty("class", "card-widget")
        cc_layout = QVBoxLayout(config_card)

        lbl_title = QLabel("Stratified Group Split Engine (Group A / Group B)")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #F8FAFC;")

        lbl_desc = QLabel(
            "Splits each department into Group A and Group B. Preserves existing allocations strictly. Uses SHA-256 deterministic hashing."
        )
        lbl_desc.setStyleSheet("color: #94A3B8;")

        self.chk_gender_balance = QCheckBox("Enable Gender Ratio Balancing within each Department")
        self.chk_gender_balance.setChecked(True)

        btn_run = QPushButton("Execute Deterministic Group Allocation")
        btn_run.setProperty("class", "primary-btn")
        btn_run.clicked.connect(self.run_allocation)

        cc_layout.addWidget(lbl_title)
        cc_layout.addWidget(lbl_desc)
        cc_layout.addWidget(self.chk_gender_balance)
        cc_layout.addWidget(btn_run)
        layout.addWidget(config_card)

        # Department Preview Table
        dept_card = QFrame()
        dept_card.setProperty("class", "card-widget")
        dc_layout = QVBoxLayout(dept_card)

        lbl_dept_title = QLabel("Department-Wise Group Distribution Breakdown")
        lbl_dept_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F8FAFC;")

        self.dept_table = QTableWidget(0, 4)
        self.dept_table.setHorizontalHeaderLabels(["Department Name", "Total Students", "Group A Count", "Group B Count"])
        self.dept_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dept_table.setEditTriggers(QTableWidget.NoEditTriggers)

        dc_layout.addWidget(lbl_dept_title)
        dc_layout.addWidget(self.dept_table)
        layout.addWidget(dept_card)

        self.refresh_preview()

    def refresh_preview(self):
        session = SessionLocal()
        try:
            depts = session.query(Department).all()
            self.dept_table.setRowCount(0)

            for d in depts:
                total = session.query(Student).filter(Student.department_id == d.id, Student.is_deleted == False).count()
                cnt_a = session.query(Student).filter(Student.department_id == d.id, Student.group_name == "Group A", Student.is_deleted == False).count()
                cnt_b = session.query(Student).filter(Student.department_id == d.id, Student.group_name == "Group B", Student.is_deleted == False).count()

                row = self.dept_table.rowCount()
                self.dept_table.insertRow(row)
                self.dept_table.setItem(row, 0, QTableWidgetItem(d.name))
                self.dept_table.setItem(row, 1, QTableWidgetItem(str(total)))
                self.dept_table.setItem(row, 2, QTableWidgetItem(str(cnt_a)))
                self.dept_table.setItem(row, 3, QTableWidgetItem(str(cnt_b)))
        finally:
            session.close()

    def run_allocation(self):
        try:
            res = GroupAllocator.allocate_groups(
                enable_gender_balance=self.chk_gender_balance.isChecked()
            )
            QMessageBox.information(
                self,
                "Group Allocation Complete",
                f"Successfully allocated {res.newly_allocated_groups} new students into Group A and Group B!\n"
                f"Skipped {res.skipped_existing} previously allocated students."
            )
            self.refresh_preview()
            self.allocation_done.emit()
        except Exception as e:
            QMessageBox.critical(self, "Group Allocation Error", str(e))
