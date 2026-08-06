from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableView, QFrame, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from database.connection import SessionLocal
from database.repository import Repository
from database.models import Department, Program, Venue, TimeSlot
from ui.components.student_table_model import StudentTableModel

class StudentView(QWidget):
    def __init__(self):
        super().__init__()
        self.table_model = StudentTableModel()
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.load_data)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Search & Multi-Filter Bar Card
        filter_card = QFrame()
        filter_card.setProperty("class", "card-widget")
        fc_layout = QVBoxLayout(filter_card)

        # Row 1: Search Box & Reset
        r1_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by USN, Student ID, Student Number, or Full Name...")
        self.txt_search.textChanged.connect(lambda: self.search_timer.start(300))

        btn_reset = QPushButton("Reset Filters")
        btn_reset.setProperty("class", "secondary-btn")
        btn_reset.clicked.connect(self.reset_filters)

        r1_layout.addWidget(self.txt_search)
        r1_layout.addWidget(btn_reset)
        fc_layout.addLayout(r1_layout)

        # Row 2: Dropdown Filters
        r2_layout = QHBoxLayout()
        
        self.cmb_dept = QComboBox()
        self.cmb_dept.addItem("All Departments", None)
        self.cmb_dept.currentIndexChanged.connect(self.load_data)

        self.cmb_group = QComboBox()
        self.cmb_group.addItems(["All Groups", "Group A", "Group B", "Unassigned"])
        self.cmb_group.currentIndexChanged.connect(self.load_data)

        self.cmb_venue = QComboBox()
        self.cmb_venue.addItem("All Venues", None)
        self.cmb_venue.currentIndexChanged.connect(self.load_data)

        self.cmb_gender = QComboBox()
        self.cmb_gender.addItems(["All Genders", "Male", "Female", "Other", "Unknown"])
        self.cmb_gender.currentIndexChanged.connect(self.load_data)

        r2_layout.addWidget(QLabel("Dept:"))
        r2_layout.addWidget(self.cmb_dept)
        r2_layout.addWidget(QLabel("Group:"))
        r2_layout.addWidget(self.cmb_group)
        r2_layout.addWidget(QLabel("Venue:"))
        r2_layout.addWidget(self.cmb_venue)
        r2_layout.addWidget(QLabel("Gender:"))
        r2_layout.addWidget(self.cmb_gender)
        
        fc_layout.addLayout(r2_layout)
        layout.addWidget(filter_card)

        # QTableView Table Widget
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setAlternatingRowColors(True)

        layout.addWidget(self.table_view)

        # Footer Record Counter
        self.lbl_count = QLabel("Showing 0 student records")
        self.lbl_count.setStyleSheet("color: #94A3B8; font-weight: bold;")
        layout.addWidget(self.lbl_count)

        self.populate_dropdowns()
        self.load_data()

    def populate_dropdowns(self):
        session = SessionLocal()
        try:
            depts = session.query(Department).all()
            for d in depts:
                self.cmb_dept.addItem(d.name, d.id)

            venues = session.query(Venue).all()
            for v in venues:
                self.cmb_venue.addItem(v.name, v.id)
        finally:
            session.close()

    def reset_filters(self):
        self.txt_search.clear()
        self.cmb_dept.setCurrentIndex(0)
        self.cmb_group.setCurrentIndex(0)
        self.cmb_venue.setCurrentIndex(0)
        self.cmb_gender.setCurrentIndex(0)
        self.load_data()

    def load_data(self):
        session = SessionLocal()
        try:
            search_query = self.txt_search.text().strip()
            dept_id = self.cmb_dept.currentData()
            
            group_sel = self.cmb_group.currentText()
            group_name = None if group_sel == "All Groups" else (group_sel if group_sel != "Unassigned" else None)

            venue_id = self.cmb_venue.currentData()
            
            gender_sel = self.cmb_gender.currentText()
            gender = None if gender_sel == "All Genders" else gender_sel

            students, total_count = Repository.get_students(
                session=session,
                search_query=search_query,
                department_id=dept_id,
                group_name=group_name,
                venue_id=venue_id,
                gender=gender,
                limit=1000  # High limit for desktop table view
            )

            self.table_model.update_data(students)
            self.lbl_count.setText(f"Showing {len(students):,} of {total_count:,} total matching records")
        finally:
            session.close()
