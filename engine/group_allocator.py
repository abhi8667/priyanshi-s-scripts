import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import Student, Department, AuditLog
from database.backup_manager import BackupManager
from core.domain_models import AllocationResult
from config import DEFAULT_GROUPS

class GroupAllocator:
    """
    Stratified, deterministic Group Allocator (Group A / Group B).
    Guarantees:
      1. Absolute Immutability: Previously allocated students NEVER move.
      2. Strict Determinism: SHA-256 USN hashing guarantees exact same results across runs.
      3. Department Splitting: Each department is split as evenly as possible.
      4. Optional Gender Balance: Stratifies within (Department, Gender) buckets.
    """

    @classmethod
    def allocate_groups(
        cls,
        group_names: Optional[List[str]] = None,
        enable_gender_balance: bool = True,
        auto_backup: bool = True
    ) -> AllocationResult:
        groups = group_names or DEFAULT_GROUPS
        num_groups = len(groups)
        if num_groups < 2:
            raise ValueError("At least 2 target groups are required for allocation.")

        if auto_backup:
            BackupManager.create_backup(trigger_action="PRE_GROUP_ALLOCATION")

        session: Session = SessionLocal()
        try:
            # Query unallocated active students
            unallocated_students = session.query(Student).filter(
                Student.is_deleted == False,
                Student.status == "Active",
                Student.group_name.is_(None)
            ).all()

            if not unallocated_students:
                return AllocationResult(
                    total_processed=0,
                    newly_allocated_groups=0,
                    newly_allocated_venues=0,
                    skipped_existing=session.query(Student).filter(Student.group_name.isnot(None)).count(),
                    warnings=["All active students already have assigned groups. No new allocations needed."]
                )

            # Group unallocated students by Department ID -> Gender (if enabled)
            buckets: Dict[Any, List[Student]] = {}
            for stu in unallocated_students:
                dept_key = stu.department_id or 0
                gender_key = stu.gender if enable_gender_balance else "ALL"
                key = (dept_key, gender_key)
                if key not in buckets:
                    buckets[key] = []
                buckets[key].append(stu)

            allocated_count = 0
            now = datetime.utcnow()

            # Pre-load department group counts in memory to handle sub-buckets accurately
            dept_group_counts: Dict[int, Dict[str, int]] = {}

            # For each bucket, sort deterministically by deterministic hash of USN
            for key, stu_list in buckets.items():
                dept_id = key[0]
                
                if dept_id not in dept_group_counts:
                    dept_group_counts[dept_id] = {
                        g: session.query(Student).filter(
                            Student.department_id == dept_id,
                            Student.group_name == g,
                            Student.is_deleted == False
                        ).count() for g in groups
                    }

                existing_counts = dept_group_counts[dept_id]

                # Sort by SHA-256 digest of clean USN for stable deterministic order
                stu_list.sort(key=lambda s: hashlib.sha256(s.usn.strip().upper().encode()).hexdigest())

                # Round-robin assign starting with the group currently having the lowest count
                for stu in stu_list:
                    sorted_groups_by_fill = sorted(groups, key=lambda g: existing_counts[g])
                    assigned_group = sorted_groups_by_fill[0]
                    stu.group_name = assigned_group
                    stu.group_allocated_at = now
                    existing_counts[assigned_group] += 1
                    allocated_count += 1

            # Log audit
            audit = AuditLog(
                action="GROUP_ALLOCATION_COMPLETED",
                entity_type="GroupAllocation",
                details=f"Allocated {allocated_count} new students across groups: {', '.join(groups)} (Gender balancing: {enable_gender_balance})"
            )
            session.add(audit)
            session.commit()

            return AllocationResult(
                total_processed=len(unallocated_students),
                newly_allocated_groups=allocated_count,
                newly_allocated_venues=0,
                skipped_existing=session.query(Student).filter(Student.group_name.isnot(None)).count() - allocated_count
            )

        except Exception as e:
            session.rollback()
            raise RuntimeError(f"Group allocation failed: {str(e)}")
        finally:
            session.close()
