"""
Enterprise Dark Glassmorphism QSS Theme Specification for NexusAllocate Pro.
"""

DARK_STYLESHEET = """
QMainWindow {
    background-color: #0F172A;
    color: #F8FAFC;
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
}

QWidget {
    color: #F8FAFC;
    font-size: 13px;
}

/* Sidebar Styling */
#SidebarWidget {
    background-color: #1E293B;
    border-right: 1px solid #334155;
    min-width: 220px;
    max-width: 220px;
}

#SidebarTitle {
    color: #38BDF8;
    font-size: 16px;
    font-weight: bold;
    padding: 16px 12px;
}

QPushButton.nav-btn {
    background-color: transparent;
    color: #94A3B8;
    text-align: left;
    padding: 12px 16px;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    margin: 2px 8px;
}

QPushButton.nav-btn:hover {
    background-color: #334155;
    color: #F8FAFC;
}

QPushButton.nav-btn:checked {
    background-color: #0284C7;
    color: #FFFFFF;
    font-weight: bold;
}

/* Header Bar */
#HeaderWidget {
    background-color: #1E293B;
    border-bottom: 1px solid #334155;
    padding: 8px 16px;
}

#HeaderTitle {
    font-size: 18px;
    font-weight: bold;
    color: #F8FAFC;
}

/* Cards & Containers */
.card-widget {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 16px;
}

.card-title {
    font-size: 14px;
    font-weight: bold;
    color: #94A3B8;
    margin-bottom: 8px;
}

.stat-value {
    font-size: 26px;
    font-weight: bold;
    color: #38BDF8;
}

/* Primary Action Buttons */
QPushButton.primary-btn {
    background-color: #0284C7;
    color: #FFFFFF;
    font-weight: bold;
    padding: 9px 18px;
    border-radius: 6px;
    border: none;
}

QPushButton.primary-btn:hover {
    background-color: #0369A1;
}

QPushButton.primary-btn:pressed {
    background-color: #075985;
}

QPushButton.secondary-btn {
    background-color: #334155;
    color: #F8FAFC;
    font-weight: 500;
    padding: 9px 18px;
    border-radius: 6px;
    border: 1px solid #475569;
}

QPushButton.secondary-btn:hover {
    background-color: #475569;
}

QPushButton.danger-btn {
    background-color: #DC2626;
    color: #FFFFFF;
    font-weight: bold;
    padding: 9px 18px;
    border-radius: 6px;
    border: none;
}

QPushButton.danger-btn:hover {
    background-color: #B91C1C;
}

/* Data Table Styling */
QTableView {
    background-color: #0F172A;
    gridline-color: #334155;
    border: 1px solid #334155;
    border-radius: 8px;
    selection-background-color: #0284C7;
    selection-color: #FFFFFF;
    font-size: 12px;
}

QHeaderView::section {
    background-color: #1E293B;
    color: #94A3B8;
    padding: 8px 10px;
    font-weight: bold;
    border: none;
    border-bottom: 2px solid #334155;
    border-right: 1px solid #334155;
}

/* Inputs & Combo Boxes */
QLineEdit, QComboBox, QSpinBox {
    background-color: #0F172A;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 7px 12px;
    selection-background-color: #0284C7;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #38BDF8;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #0F172A;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

/* Status Bar */
QStatusBar {
    background-color: #1E293B;
    color: #94A3B8;
    border-top: 1px solid #334155;
}
"""
