from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from typing import List, Any
from database.models import Student

class StudentTableModel(QAbstractTableModel):
    """High performance QAbstractTableModel for PySide6 QTableView."""

    COLUMNS = [
        "USN", "Student ID", "Full Name", "Gender",
        "Department", "Program", "Group", "Venue", "Time Slot", "Status"
    ]

    def __init__(self, students: List[Student] = None):
        super().__init__()
        self._students: List[Student] = students or []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._students)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._students)):
            return None

        stu = self._students[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0: return stu.usn
            elif col == 1: return stu.student_id or "-"
            elif col == 2: return stu.full_name
            elif col == 3: return stu.gender
            elif col == 4: return stu.department.name if stu.department else "-"
            elif col == 5: return stu.program.name if stu.program else "-"
            elif col == 6: return stu.group_name or "Unassigned"
            elif col == 7: return stu.venue.name if stu.venue else "Unassigned"
            elif col == 8: return stu.time_slot.slot_name if stu.time_slot else "Unassigned"
            elif col == 9: return stu.status

        elif role == Qt.TextAlignmentRole:
            if col in [0, 1, 3, 6, 9]:
                return int(Qt.AlignCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section]
        return None

    def update_data(self, new_students: List[Student]):
        self.beginResetModel()
        self._students = new_students
        self.endResetModel()

    def get_student_at(self, row: int) -> Student:
        if 0 <= row < len(self._students):
            return self._students[row]
        return None
