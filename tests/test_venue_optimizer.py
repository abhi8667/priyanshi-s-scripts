import pytest
from database.connection import init_db, SessionLocal
from database.models import Student, Department, Venue, TimeSlot, StudentEventAllocation
from engine.venue_optimizer import VenueOptimizer
from core.exceptions import CapacityExceededError

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    session = SessionLocal()
    session.query(StudentEventAllocation).delete()
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

def test_venue_and_timeslot_deletion():
    from database.repository import Repository
    session = SessionLocal()

    v1 = Venue(name="Venue To Delete", capacity=50, is_active=True)
    ts1 = TimeSlot(slot_name="Slot To Delete", start_time="02:00 PM", end_time="04:00 PM", day_number=1)
    session.add_all([v1, ts1])
    session.commit()

    student = Student(usn="1DS21CS999", full_name="Test Student", venue_id=v1.id, time_slot_id=ts1.id)
    session.add(student)
    session.commit()

    # Delete venue
    ok, msg = Repository.delete_venue(session, v1.id)
    assert ok is True
    assert session.query(Venue).filter(Venue.name == "Venue To Delete").first() is None
    
    session.refresh(student)
    assert student.venue_id is None

    # Delete timeslot
    ok_ts, msg_ts = Repository.delete_time_slot(session, ts1.id)
    assert ok_ts is True
    assert session.query(TimeSlot).filter(TimeSlot.slot_name == "Slot To Delete").first() is None
    
    session.close()

def test_proportional_and_balanced_venue_allocation():
    session = SessionLocal()

    # 1. Setup 5 Departments
    dept_specs = [
        ("CSE", 50, 50),
        ("ISE", 50, 50),
        ("ECE", 50, 50),
        ("AIML", 70, 30),
        ("MECH", 70, 30),
    ]

    depts = {}
    for code, m_cnt, f_cnt in dept_specs:
        d = Department(name=f"Department {code}", code=code)
        session.add(d)
        session.flush()
        depts[code] = d

    # 2. Add 500 Students
    for code, m_cnt, f_cnt in dept_specs:
        d_id = depts[code].id
        for i in range(m_cnt):
            s = Student(usn=f"1DS21{code}M{i:03d}", full_name=f"{code} Male {i}", gender="Male", department_id=d_id, status="Active")
            session.add(s)
        for i in range(f_cnt):
            s = Student(usn=f"1DS21{code}F{i:03d}", full_name=f"{code} Female {i}", gender="Female", department_id=d_id, status="Active")
            session.add(s)

    # 3. Add 2 Venues (ECE Seminar Hall: 500, Civil Hall: 200) & 1 Slot
    v1 = Venue(name="ECE Seminar Hall", capacity=500, is_active=True)
    v2 = Venue(name="Civil Hall", capacity=200, is_active=True)
    ts = TimeSlot(slot_name="Morning Session", start_time="09:00 AM", end_time="11:00 AM", day_number=1)
    session.add_all([v1, v2, ts])
    session.commit()

    # 4. Run Optimization
    res = VenueOptimizer.optimize_allocations(auto_backup=False)
    assert res.newly_allocated_venues == 500

    # 5. Verify Proportionality and Occupancy Balancing
    v1_students = session.query(Student).filter(Student.venue_id == v1.id).all()
    v2_students = session.query(Student).filter(Student.venue_id == v2.id).all()

    # Check Total Counts (Balanced ~357 in V1, ~143 in V2)
    assert len(v1_students) == 357
    assert len(v2_students) == 143

    # Check Department representation (Every dept in both venues)
    for code, _, _ in dept_specs:
        d_id = depts[code].id
        v1_dept_cnt = len([s for s in v1_students if s.department_id == d_id])
        v2_dept_cnt = len([s for s in v2_students if s.department_id == d_id])

        # CSE, ISE, ECE, AIML, MECH each get 71 or 72 in V1, 28 or 29 in V2
        assert 70 <= v1_dept_cnt <= 73
        assert 27 <= v2_dept_cnt <= 30
        assert v1_dept_cnt + v2_dept_cnt == 100

    # Check Gender Proportions (290 Male, 210 Female total -> ~207M / ~150F in V1, ~83M / ~60F in V2)
    v1_males = len([s for s in v1_students if s.gender == "Male"])
    v1_females = len([s for s in v1_students if s.gender == "Female"])
    v2_males = len([s for s in v2_students if s.gender == "Male"])
    v2_females = len([s for s in v2_students if s.gender == "Female"])

    assert 200 <= v1_males <= 215
    assert 140 <= v1_females <= 155
    assert 75 <= v2_males <= 90
    assert 55 <= v2_females <= 65

    session.close()


