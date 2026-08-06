from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QInputDialog, QLineEdit
)
from PySide6.QtCore import Qt, Signal
from database.connection import SessionLocal
from database.models import Venue, TimeSlot
from database.repository import Repository
from engine.venue_optimizer import VenueOptimizer
from core.exceptions import CapacityExceededError

class VenueAllocationView(QWidget):
    venue_allocation_done = Signal()

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Diagnostics & Capacity Check Banner Card
        self.diag_card = QFrame()
        self.diag_card.setProperty("class", "card-widget")
        dc_layout = QVBoxLayout(self.diag_card)

        self.lbl_cap_status = QLabel("Checking venue capacities...")
        self.lbl_cap_status.setStyleSheet("font-size: 15px; font-weight: bold; color: #38BDF8;")

        self.lbl_cap_details = QLabel("")
        self.lbl_cap_details.setStyleSheet("color: #94A3B8;")

        dc_layout.addWidget(self.lbl_cap_status)
        dc_layout.addWidget(self.lbl_cap_details)
        layout.addWidget(self.diag_card)

        # Venues & Time Slots Split Layout
        lists_layout = QHBoxLayout()

        # Venues Table Box
        venue_box = QFrame()
        venue_box.setProperty("class", "card-widget")
        vb_layout = QVBoxLayout(venue_box)

        v_head = QHBoxLayout()
        lbl_v_title = QLabel("Configured Venues")
        lbl_v_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F8FAFC;")
        
        btn_add_v = QPushButton("+ Add Venue")
        btn_add_v.setProperty("class", "secondary-btn")
        btn_add_v.clicked.connect(self.add_venue)
        
        v_head.addWidget(lbl_v_title)
        v_head.addStretch()
        v_head.addWidget(btn_add_v)
        vb_layout.addLayout(v_head)

        self.venue_table = QTableWidget(0, 3)
        self.venue_table.setHorizontalHeaderLabels(["Venue Name", "Capacity", "Status"])
        self.venue_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        vb_layout.addWidget(self.venue_table)

        lists_layout.addWidget(venue_box)

        # Time Slots Table Box
        slot_box = QFrame()
        slot_box.setProperty("class", "card-widget")
        sb_layout = QVBoxLayout(slot_box)

        s_head = QHBoxLayout()
        lbl_s_title = QLabel("Configured Time Slots")
        lbl_s_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F8FAFC;")

        btn_add_s = QPushButton("+ Add Time Slot")
        btn_add_s.setProperty("class", "secondary-btn")
        btn_add_s.clicked.connect(self.add_timeslot)

        s_head.addWidget(lbl_s_title)
        s_head.addStretch()
        s_head.addWidget(btn_add_s)
        sb_layout.addLayout(s_head)

        self.slot_table = QTableWidget(0, 3)
        self.slot_table.setHorizontalHeaderLabels(["Slot Name", "Start Time", "End Time"])
        self.slot_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        sb_layout.addWidget(self.slot_table)

        lists_layout.addWidget(slot_box)
        layout.addLayout(lists_layout)

        # Execute Optimization Footer
        footer_layout = QHBoxLayout()
        btn_run_milp = QPushButton("Run MILP Venue & Timeslot Optimization")
        btn_run_milp.setProperty("class", "primary-btn")
        btn_run_milp.clicked.connect(self.run_optimization)

        footer_layout.addStretch()
        footer_layout.addWidget(btn_run_milp)
        layout.addLayout(footer_layout)

        self.refresh_tables()

    def refresh_tables(self):
        session = SessionLocal()
        try:
            # Refresh Venues
            venues = session.query(Venue).all()
            self.venue_table.setRowCount(0)
            for v in venues:
                row = self.venue_table.rowCount()
                self.venue_table.insertRow(row)
                self.venue_table.setItem(row, 0, QTableWidgetItem(v.name))
                self.venue_table.setItem(row, 1, QTableWidgetItem(str(v.capacity)))
                self.venue_table.setItem(row, 2, QTableWidgetItem("Active" if v.is_active else "Inactive"))

            # Refresh Time Slots
            slots = session.query(TimeSlot).all()
            self.slot_table.setRowCount(0)
            for s in slots:
                row = self.slot_table.rowCount()
                self.slot_table.insertRow(row)
                self.slot_table.setItem(row, 0, QTableWidgetItem(s.slot_name))
                self.slot_table.setItem(row, 1, QTableWidgetItem(s.start_time))
                self.slot_table.setItem(row, 2, QTableWidgetItem(s.end_time))

            # Capacity Report
            cap_report = VenueOptimizer.check_capacity(session)
            if cap_report.is_sufficient:
                self.lbl_cap_status.setText("Capacity Check Passed ✓")
                self.lbl_cap_status.setStyleSheet("font-size: 15px; font-weight: bold; color: #10B981;")
                self.lbl_cap_details.setText(
                    f"Total unassigned students: {cap_report.total_students:,} | Total venue capacity available across slots: {cap_report.total_capacity:,}."
                )
            else:
                self.lbl_cap_status.setText("WARNING: Insufficient Venue Capacity! ⚠️")
                self.lbl_cap_status.setStyleSheet("font-size: 15px; font-weight: bold; color: #EF4444;")
                sug_str = ", ".join([f"{k}: +{v}" for k, v in cap_report.suggested_per_slot.items()])
                self.lbl_cap_details.setText(
                    f"Required: {cap_report.total_students:,} | Available: {cap_report.total_capacity:,} | Deficit: {cap_report.deficiency} seats.\n"
                    f"Suggested Capacity Increase: Add at least {sug_str} seats."
                )
        finally:
            session.close()

    def add_venue(self):
        name, ok1 = QInputDialog.getText(self, "Add New Venue", "Venue Name (e.g. Auditorium A):")
        if ok1 and name.strip():
            cap, ok2 = QInputDialog.getInt(self, "Venue Capacity", f"Capacity for '{name.strip()}':", 200, 10, 5000)
            if ok2:
                session = SessionLocal()
                try:
                    Repository.get_or_create_venue(session, name.strip(), cap)
                    session.commit()
                    self.refresh_tables()
                finally:
                    session.close()

    def add_timeslot(self):
        name, ok1 = QInputDialog.getText(self, "Add Time Slot", "Slot Name (e.g. Morning Session):")
        if ok1 and name.strip():
            start, ok2 = QInputDialog.getText(self, "Start Time", "Start Time (e.g. 09:30 AM):")
            if ok2 and start.strip():
                end, ok3 = QInputDialog.getText(self, "End Time", "End Time (e.g. 11:30 AM):")
                if ok3 and end.strip():
                    session = SessionLocal()
                    try:
                        Repository.get_or_create_time_slot(session, name.strip(), start.strip(), end.strip())
                        session.commit()
                        self.refresh_tables()
                    finally:
                        session.close()

    def run_optimization(self):
        try:
            res = VenueOptimizer.optimize_allocations()
            QMessageBox.information(
                self,
                "Venue Optimization Complete",
                f"Successfully assigned {res.newly_allocated_venues} students to venues and time slots!"
            )
            self.refresh_tables()
            self.venue_allocation_done.emit()
        except CapacityExceededError as ce:
            QMessageBox.warning(
                self,
                "Capacity Exceeded Error",
                f"{str(ce)}\n\nPlease add more venues or time slots before running venue allocation."
            )
        except Exception as e:
            QMessageBox.critical(self, "Optimization Error", str(e))
