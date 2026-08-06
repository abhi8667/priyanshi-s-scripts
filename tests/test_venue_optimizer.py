import pytest
from database.connection import init_db, SessionLocal
from database.models import Student, Department, Venue, TimeSlot
from engine.venue_optimizer import VenueOptimizer
from core.exceptions import CapacityExceededError

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    session = SessionLocal()
    session.query(Student).delete()
    session.query(Department).delete()
    session.query(Venue).delete()
    session.query(TimeSlot).delete()
    session.commit()
    session.close()

def test_venue_capacity_check_and_optimization():
    session = SessionLocal()

    v1 = Venue(name="Auditorium 1", capacity=10, is_active=True)
    v2 = Venue(name="Seminar Hall B", capacity=10, is_active=True)
    ts1 = TimeSlot(slot_name="Slot 1", start_time="09:00 AM", end_time="11:00 AM", day_number=1)
    session.add_all([v1, v2, ts1])
    
    dept = Department(name="Computer Science", code="CSE")
    session.add(dept)
    session.commit()

    # Add 25 students (Total capacity = 20) -> Should fail capacity check!
    for i in range(25):
        s = Student(usn=f"1DS21CS{i:03d}", full_name=f"Stu {i}", department_id=dept.id, group_name="Group A")
        session.add(s)
    session.commit()

    report = VenueOptimizer.check_capacity(session)
    assert report.is_sufficient is False
    assert report.deficiency == 5

    with pytest.raises(CapacityExceededError):
        VenueOptimizer.optimize_allocations(auto_backup=False)

    # Increase capacity to 30 by adding another Time Slot
    ts2 = TimeSlot(slot_name="Slot 2", start_time="11:30 AM", end_time="01:30 PM", day_number=1)
    session.add(ts2)
    session.commit()

    # Now total capacity = 2 venues * 2 slots * 10 cap = 40 >= 25 -> Should succeed!
    res = VenueOptimizer.optimize_allocations(auto_backup=False)
    assert res.newly_allocated_venues == 25
    session.close()
