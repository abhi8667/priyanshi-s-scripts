from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime

class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    UNKNOWN = "Unknown"

    @classmethod
    def parse(cls, val: Any) -> "Gender":
        if not val or not isinstance(val, str):
            return cls.UNKNOWN
        clean = val.strip().lower()
        if clean in ["m", "male", "boy", "man"]:
            return cls.MALE
        elif clean in ["f", "female", "girl", "woman"]:
            return cls.FEMALE
        elif clean in ["o", "other"]:
            return cls.OTHER
        return cls.UNKNOWN

class StudentStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    GRADUATED = "Graduated"
    WITHDRAWN = "Withdrawn"

class ExportFormat(str, Enum):
    EXCEL = "Excel"
    CSV = "CSV"
    PDF = "PDF"

@dataclass
class StudentRecord:
    usn: str
    name: str
    department: str
    program: str = "B.Tech"
    student_id: Optional[str] = None
    student_number: Optional[str] = None
    gender: Gender = Gender.UNKNOWN
    status: StudentStatus = StudentStatus.ACTIVE
    group_name: Optional[str] = None
    venue_name: Optional[str] = None
    time_slot: Optional[str] = None
    allocation_date: Optional[datetime] = None

@dataclass
class AllocationResult:
    total_processed: int
    newly_allocated_groups: int
    newly_allocated_venues: int
    skipped_existing: int
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

@dataclass
class CapacityReport:
    total_students: int
    total_capacity: int
    is_sufficient: bool
    deficiency: int
    suggested_per_slot: Dict[str, int] = field(default_factory=dict)
