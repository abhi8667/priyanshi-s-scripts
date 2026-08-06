import pulp
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from sqlalchemy.orm import Session, joinedload

from database.connection import SessionLocal
from database.models import Student, Department, Venue, TimeSlot, AuditLog
from database.backup_manager import BackupManager
from core.domain_models import AllocationResult, CapacityReport
from core.exceptions import CapacityExceededError

class VenueOptimizer:
    """
    Mixed-Integer Linear Programming (MILP) Venue & Timeslot Optimization Engine.
    Uses PuLP solver to assign students/departments to Venues and Time Slots.
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
    def optimize_allocations(
        cls,
        target_group: Optional[str] = None,
        allow_department_splits: bool = True,
        auto_backup: bool = True
    ) -> AllocationResult:
        """Runs the MILP solver to allocate unassigned students to venues and time slots."""
        if auto_backup:
            BackupManager.create_backup(trigger_action="PRE_VENUE_ALLOCATION")

        session: Session = SessionLocal()
        try:
            # Capacity check
            cap_report = cls.check_capacity(session, target_group)
            if not cap_report.is_sufficient:
                raise CapacityExceededError(
                    f"Insufficient total venue capacity! Total students needing allocation: {cap_report.total_students}, Total available capacity: {cap_report.total_capacity}. Shortfall: {cap_report.deficiency} seats.",
                    required_capacity=cap_report.total_students,
                    available_capacity=cap_report.total_capacity
                )

            # Query target unallocated students
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

            # Group unallocated students into Department & Group blocks for cohesion
            # Block key: (department_id, group_name)
            blocks: Dict[Tuple[int, str], List[Student]] = {}
            for s in unallocated_students:
                key = (s.department_id or 0, s.group_name or "Unassigned")
                if key not in blocks:
                    blocks[key] = []
                blocks[key].append(s)

            # Formulate MILP Problem
            prob = pulp.LpProblem("Venue_TimeSlot_Allocation", pulp.LpMinimize)

            b_keys = list(blocks.keys())
            b_counts = [len(blocks[k]) for k in b_keys]
            v_ids = [venue_item.id for venue_item in venues]
            v_caps = {venue_item.id: venue_item.capacity for venue_item in venues}
            t_ids = [slot_item.id for slot_item in time_slots]

            x = {}
            y = {}

            for i in range(len(b_keys)):
                for v_id in v_ids:
                    for t_id in t_ids:
                        x[i, v_id, t_id] = pulp.LpVariable(f"x_{i}_{v_id}_{t_id}", lowBound=0, cat=pulp.LpInteger)
                        y[i, v_id, t_id] = pulp.LpVariable(f"y_{i}_{v_id}_{t_id}", cat=pulp.LpBinary)

            # Constraint 1: Every student in block i must be allocated
            for i in range(len(b_keys)):
                prob += pulp.lpSum(x[i, v_id, t_id] for v_id in v_ids for t_id in t_ids) == b_counts[i]

            # Constraint 2: Venue capacity per time slot must not be exceeded
            for v_id in v_ids:
                for t_id in t_ids:
                    prob += pulp.lpSum(x[i, v_id, t_id] for i in range(len(b_keys))) <= v_caps[v_id]

            # Link x and y: x[i, v, t] <= b_counts[i] * y[i, v, t]
            for i in range(len(b_keys)):
                for v_id in v_ids:
                    for t_id in t_ids:
                        prob += x[i, v_id, t_id] <= b_counts[i] * y[i, v_id, t_id]

            # Objective: Minimize number of split slices
            prob += pulp.lpSum(y[i, v_id, t_id] for i in range(len(b_keys)) for v_id in v_ids for t_id in t_ids)

            # Solve problem with default solver
            status = prob.solve(pulp.PULP_CBC_CMD(msg=False))

            if status != pulp.LpStatusOptimal and status != 1:
                return cls._greedy_fallback_allocation(session, unallocated_students, venues, time_slots)

            # Apply solution to database
            allocated_count = 0
            now = datetime.utcnow()

            for i, b_key in enumerate(b_keys):
                students_in_block = blocks[b_key]
                curr_idx = 0

                for v_id in v_ids:
                    for t_id in t_ids:
                        alloc_num = int(pulp.value(x[i, v_id, t_id]) or 0)
                        if alloc_num > 0:
                            sub_list = students_in_block[curr_idx : curr_idx + alloc_num]
                            for s in sub_list:
                                s.venue_id = v_id
                                s.time_slot_id = t_id
                                s.venue_allocated_at = now
                                allocated_count += 1
                            curr_idx += alloc_num

            # Log audit
            audit = AuditLog(
                action="VENUE_OPTIMIZATION_SUCCESS",
                entity_type="VenueAllocation",
                details=f"Optimally allocated {allocated_count} students to {len(venues)} venues across {len(time_slots)} slots using MILP solver."
            )
            session.add(audit)
            session.commit()

            return AllocationResult(
                total_processed=len(unallocated_students),
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

    @classmethod
    def _greedy_fallback_allocation(
        cls,
        session: Session,
        unallocated_students: List[Student],
        venues: List[Venue],
        time_slots: List[TimeSlot]
    ) -> AllocationResult:
        """Deterministic Greedy bin-packing fallback for massive student numbers."""
        now = datetime.utcnow()
        allocated_count = 0

        # Create slots with available capacities
        slot_caps: Dict[Tuple[int, int], int] = {}
        for t in time_slots:
            for v in venues:
                slot_caps[(v.id, t.id)] = v.capacity

        # Sort students by department to keep departments together
        unallocated_students.sort(key=lambda s: (s.department_id or 0, s.group_name or ""))

        current_pair_idx = 0
        pairs = list(slot_caps.keys())

        for s in unallocated_students:
            while current_pair_idx < len(pairs):
                v_id, t_id = pairs[current_pair_idx]
                if slot_caps[(v_id, t_id)] > 0:
                    s.venue_id = v_id
                    s.time_slot_id = t_id
                    s.venue_allocated_at = now
                    slot_caps[(v_id, t_id)] -= 1
                    allocated_count += 1
                    break
                else:
                    current_pair_idx += 1

        session.commit()
        return AllocationResult(
            total_processed=len(unallocated_students),
            newly_allocated_groups=0,
            newly_allocated_venues=allocated_count,
            skipped_existing=0,
            warnings=["Used deterministic greedy fallback for venue allocation."]
        )
