import math
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import Student, Department, Venue, TimeSlot, AuditLog
from database.backup_manager import BackupManager
from core.domain_models import AllocationResult, CapacityReport
from core.exceptions import CapacityExceededError

class VenueOptimizer:
    """
    Proportional Stratified Multi-Criteria Optimization & Occupancy Balancing Engine.
    
    Ensures:
    1. Proportional representation of every Department across all venues.
    2. Proportional Gender ratios matching overall population per venue.
    3. Balanced occupancy rates across available venues (no under-utilized venues).
    4. Strict adherence to max venue capacities.
    5. Deterministic placement based on student USN / ID.
    6. Efficient scalability to 10,000+ students.
    """

    @classmethod
    def check_capacity(cls, session: Session, target_group: Optional[str] = None) -> CapacityReport:
        """Evaluates whether current active venues and time slots have sufficient capacity."""
        query = session.query(Student).filter(
            Student.is_deleted == False,
            Student.status == "Active",
            Student.venue_id.is_(None)
        )
        if target_group:
            query = query.filter(Student.group_name == target_group)

        total_students = query.count()

        active_venues = session.query(Venue).filter(Venue.is_active == True).all()
        time_slots = session.query(TimeSlot).all()

        total_capacity_per_slot = sum(v.capacity for v in active_venues)
        total_capacity = total_capacity_per_slot * len(time_slots)

        is_sufficient = total_capacity >= total_students
        deficiency = max(0, total_students - total_capacity)

        suggested_per_slot = {}
        if deficiency > 0 and len(time_slots) > 0:
            extra_per_slot = (deficiency + len(time_slots) - 1) // len(time_slots)
            for ts in time_slots:
                suggested_per_slot[ts.slot_name] = extra_per_slot

        return CapacityReport(
            total_students=total_students,
            total_capacity=total_capacity,
            is_sufficient=is_sufficient,
            deficiency=deficiency,
            suggested_per_slot=suggested_per_slot
        )

    @classmethod
    def _distribute_venue_capacities(
        cls,
        venues: List[Venue],
        slot_student_count: int
    ) -> Dict[int, int]:
        """
        Calculates balanced target student capacities per venue for a given slot
        using Hamilton-Hare (Largest Remainder) proportional distribution.
        """
        total_slot_capacity = sum(v.capacity for v in venues)
        if total_slot_capacity == 0 or slot_student_count == 0:
            return {v.id: 0 for v in venues}

        ratio = min(1.0, slot_student_count / total_slot_capacity)
        
        base_alloc: Dict[int, int] = {}
        remainders: List[Tuple[float, int, int]] = [] # (remainder, max_cap, venue_id)

        for v in venues:
            exact = v.capacity * ratio
            base = min(int(exact), v.capacity)
            base_alloc[v.id] = base
            rem = exact - base
            remainders.append((rem, v.capacity, v.id))

        assigned = sum(base_alloc.values())
        deficit = slot_student_count - assigned

        # Sort by remainder descending, then capacity descending
        remainders.sort(key=lambda x: (x[0], x[1]), reverse=True)

        idx = 0
        while deficit > 0 and remainders:
            rem, max_cap, v_id = remainders[idx % len(remainders)]
            if base_alloc[v_id] < max_cap:
                base_alloc[v_id] += 1
                deficit -= 1
            idx += 1
            if idx > len(remainders) * 100: # Safety break
                break

        return base_alloc

    @classmethod
    def _allocate_strata_matrix(
        cls,
        venue_targets: Dict[int, int],
        strata_students: Dict[Tuple[int, str], List[Student]]
    ) -> Dict[Tuple[int, Tuple[int, str]], int]:
        """
        Uses 2D Largest Remainder matrix rounding to allocate stratum counts (department, gender)
        to venues, maintaining exact row sums (venue targets) and col sums (stratum counts).
        
        Returns dict mapping (venue_id, (department_id, gender)) -> int count.
        """
        v_ids = list(venue_targets.keys())
        strata_keys = list(strata_students.keys())
        total_students = sum(len(s_list) for s_list in strata_students.values())

        if total_students == 0 or not v_ids:
            return {}

        # 1. Continuous ideal matrix Q[v, k]
        # Q[v, k] = T_v * (N_k / Total)
        exact_matrix: Dict[Tuple[int, Tuple[int, str]], float] = {}
        base_matrix: Dict[Tuple[int, Tuple[int, str]], int] = {}
        remainders: List[Tuple[float, int, Tuple[int, str]]] = []

        for v_id in v_ids:
            t_v = venue_targets[v_id]
            for s_key in strata_keys:
                n_k = len(strata_students[s_key])
                exact = (t_v * n_k) / total_students
                base = int(exact)
                exact_matrix[(v_id, s_key)] = exact
                base_matrix[(v_id, s_key)] = base
                remainders.append((exact - base, v_id, s_key))

        # Check deficits
        row_deficits = {v_id: venue_targets[v_id] - sum(base_matrix[(v_id, k)] for k in strata_keys) for v_id in v_ids}
        col_deficits = {k: len(strata_students[k]) - sum(base_matrix[(v, k)] for v in v_ids) for k in strata_keys}

        # Sort remainders descending
        remainders.sort(key=lambda item: item[0], reverse=True)

        for rem, v_id, s_key in remainders:
            if row_deficits[v_id] > 0 and col_deficits[s_key] > 0:
                base_matrix[(v_id, s_key)] += 1
                row_deficits[v_id] -= 1
                col_deficits[s_key] -= 1

        # Residual sweep if any remain due to zero remainders
        for v_id in v_ids:
            while row_deficits[v_id] > 0:
                allocated = False
                for s_key in strata_keys:
                    if col_deficits[s_key] > 0:
                        base_matrix[(v_id, s_key)] += 1
                        row_deficits[v_id] -= 1
                        col_deficits[s_key] -= 1
                        allocated = True
                        break
                if not allocated:
                    break

        return base_matrix

    @classmethod
    def optimize_allocations(
        cls,
        target_group: Optional[str] = None,
        allow_department_splits: bool = True,
        auto_backup: bool = True
    ) -> AllocationResult:
        """
        Executes Proportional Stratified Occupancy Balancing optimization to assign unassigned
        students to venues and time slots proportionally across departments and genders.
        """
        if auto_backup:
            BackupManager.create_backup(trigger_action="PRE_VENUE_ALLOCATION")

        session: Session = SessionLocal()
        try:
            # 1. Check Capacity
            cap_report = cls.check_capacity(session, target_group)
            if not cap_report.is_sufficient:
                raise CapacityExceededError(
                    f"Insufficient total venue capacity! Total students needing allocation: {cap_report.total_students}, Total available capacity: {cap_report.total_capacity}. Shortfall: {cap_report.deficiency} seats.",
                    required_capacity=cap_report.total_students,
                    available_capacity=cap_report.total_capacity
                )

            # 2. Query target unallocated active students
            query = session.query(Student).filter(
                Student.is_deleted == False,
                Student.status == "Active",
                Student.venue_id.is_(None)
            )
            if target_group:
                query = query.filter(Student.group_name == target_group)

            unallocated_students = query.all()
            if not unallocated_students:
                return AllocationResult(
                    total_processed=0,
                    newly_allocated_groups=0,
                    newly_allocated_venues=0,
                    skipped_existing=0,
                    warnings=["No unallocated students found for venue assignment."]
                )

            venues = session.query(Venue).filter(Venue.is_active == True).all()
            time_slots = session.query(TimeSlot).all()

            if not venues:
                raise ValueError("No active venues found. Please configure venues first.")
            if not time_slots:
                raise ValueError("No time slots found. Please configure time slots first.")

            # Sort venues and time slots deterministically by ID
            venues.sort(key=lambda v: v.id)
            time_slots.sort(key=lambda t: t.id)

            # Sort unallocated students deterministically by USN / ID
            unallocated_students.sort(key=lambda s: (s.usn or "", s.full_name or "", s.id))

            total_unallocated = len(unallocated_students)
            allocated_count = 0
            now = datetime.utcnow()

            student_pool_idx = 0

            import math

            num_slots = len(time_slots)
            # Process Slot by Slot, balancing student load across all configured time slots
            for slot_idx, t_slot in enumerate(time_slots):
                if student_pool_idx >= total_unallocated:
                    break

                slot_capacity = sum(v.capacity for v in venues)
                remaining_students = total_unallocated - student_pool_idx
                num_remaining_slots = num_slots - slot_idx

                # Balance load across all configured time slots
                target_for_slot = math.ceil(remaining_students / num_remaining_slots) if num_remaining_slots > 0 else remaining_students
                slot_student_count = min(remaining_students, slot_capacity, target_for_slot)

                # Slice pool of students for this time slot
                slot_students = unallocated_students[student_pool_idx : student_pool_idx + slot_student_count]
                student_pool_idx += slot_student_count

                # Step A: Proportional Balanced Venue Capacities for this Slot
                venue_targets = cls._distribute_venue_capacities(venues, slot_student_count)

                # Step B: Stratify slot students by (department_id, gender)
                strata_students: Dict[Tuple[int, str], List[Student]] = {}
                for s in slot_students:
                    s_key = (s.department_id or 0, s.gender or "Unknown")
                    if s_key not in strata_students:
                        strata_students[s_key] = []
                    strata_students[s_key].append(s)

                # Step C: Generate Proportional Stratum Matrix
                matrix_alloc = cls._allocate_strata_matrix(venue_targets, strata_students)

                # Step D: Deterministically assign students to venues based on matrix counts
                # Track assigned index per stratum
                strata_indices: Dict[Tuple[int, str], int] = {k: 0 for k in strata_students}

                for v in venues:
                    v_id = v.id
                    for s_key, s_list in strata_students.items():
                        count_to_assign = matrix_alloc.get((v_id, s_key), 0)
                        if count_to_assign > 0:
                            curr_start = strata_indices[s_key]
                            sub_group = s_list[curr_start : curr_start + count_to_assign]
                            strata_indices[s_key] += count_to_assign

                            for s in sub_group:
                                s.venue_id = v_id
                                s.time_slot_id = t_slot.id
                                s.venue_allocated_at = now
                                allocated_count += 1

            # Log audit
            audit = AuditLog(
                action="VENUE_OPTIMIZATION_SUCCESS",
                entity_type="VenueAllocation",
                details=f"Proportionally allocated {allocated_count} students to {len(venues)} venues across {len(time_slots)} slots with balanced occupancy."
            )
            session.add(audit)
            session.commit()

            return AllocationResult(
                total_processed=total_unallocated,
                newly_allocated_groups=0,
                newly_allocated_venues=allocated_count,
                skipped_existing=0
            )

        except CapacityExceededError:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Venue optimization failed: {str(e)}")
        finally:
            session.close()

