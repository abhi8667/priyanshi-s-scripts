from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from services.export_service import ExportService
from config import EXPORTS_DIR

class ExportView(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header Card
        lbl_title = QLabel("Enterprise Export & Reporting Center")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #F8FAFC;")
        layout.addWidget(lbl_title)

        # Export Options Grid
        grid_layout = QHBoxLayout()

        # Excel Export Card
        excel_card = QFrame()
        excel_card.setProperty("class", "card-widget")
        ec_layout = QVBoxLayout(excel_card)

        lbl_e_title = QLabel("Multi-Tab Excel Workbook")
        lbl_e_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #38BDF8;")
        lbl_e_desc = QLabel("Generates styled multi-sheet workbook (Master, Group A, Group B, Dept & Venue allocations).")
        lbl_e_desc.setWordWrap(True)
        lbl_e_desc.setStyleSheet("color: #94A3B8;")

        btn_exp_excel = QPushButton("Export Master Excel (.xlsx)")
        btn_exp_excel.setProperty("class", "primary-btn")
        btn_exp_excel.clicked.connect(self.export_excel)

        ec_layout.addWidget(lbl_e_title)
        ec_layout.addWidget(lbl_e_desc)
        ec_layout.addStretch()
        ec_layout.addWidget(btn_exp_excel)
        grid_layout.addWidget(excel_card)

        # CSV Export Card
        csv_card = QFrame()
        csv_card.setProperty("class", "card-widget")
        cc_layout = QVBoxLayout(csv_card)

        lbl_c_title = QLabel("Flat CSV Dataset")
        lbl_c_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #10B981;")
        lbl_c_desc = QLabel("Generates lightweight CSV file with formula injection security sanitization.")
        lbl_c_desc.setWordWrap(True)
        lbl_c_desc.setStyleSheet("color: #94A3B8;")

        btn_exp_csv = QPushButton("Export Flat CSV (.csv)")
        btn_exp_csv.setProperty("class", "secondary-btn")
        btn_exp_csv.clicked.connect(self.export_csv)

        cc_layout.addWidget(lbl_c_title)
        cc_layout.addWidget(lbl_c_desc)
        cc_layout.addStretch()
        cc_layout.addWidget(btn_exp_csv)
        grid_layout.addWidget(csv_card)

        # PDF Attendance Sheet Card
        pdf_card = QFrame()
        pdf_card.setProperty("class", "card-widget")
        pc_layout = QVBoxLayout(pdf_card)

        lbl_p_title = QLabel("Printable PDF Attendance Sheets")
        lbl_p_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #8B5CF6;")
        lbl_p_desc = QLabel("Generates print-ready PDF attendance rosters with student signature columns.")
        lbl_p_desc.setWordWrap(True)
        lbl_p_desc.setStyleSheet("color: #94A3B8;")

        btn_exp_pdf = QPushButton("Generate Attendance PDF (.pdf)")
        btn_exp_pdf.setProperty("class", "secondary-btn")
        btn_exp_pdf.clicked.connect(self.export_pdf)

        pc_layout.addWidget(lbl_p_title)
        pc_layout.addWidget(lbl_p_desc)
        pc_layout.addStretch()
        pc_layout.addWidget(btn_exp_pdf)
        grid_layout.addWidget(pdf_card)

        layout.addLayout(grid_layout)

    def export_excel(self):
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save Master Excel Export", str(EXPORTS_DIR / "Master_Allocation_Report.xlsx"), "Excel Files (*.xlsx)"
        )
        if dest:
            try:
                out = ExportService.export_excel_master(Path(dest))
                QMessageBox.information(self, "Export Complete", f"Successfully exported Excel workbook to:\n{out}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def export_csv(self):
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save Flat CSV Export", str(EXPORTS_DIR / "Student_Allocations.csv"), "CSV Files (*.csv)"
        )
        if dest:
            try:
                out = ExportService.export_csv(Path(dest))
                QMessageBox.information(self, "Export Complete", f"Successfully exported CSV file to:\n{out}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def export_pdf(self):
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save Attendance Sheet PDF", str(EXPORTS_DIR / "Attendance_Sheet.pdf"), "PDF Files (*.pdf)"
        )
        if dest:
            try:
                out = ExportService.export_pdf_attendance_sheet(Path(dest))
                QMessageBox.information(self, "Export Complete", f"Successfully generated PDF attendance sheet:\n{out}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))
