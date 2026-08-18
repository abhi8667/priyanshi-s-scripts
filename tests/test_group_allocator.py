import pytest
from database.connection import init_db, SessionLocal
from database.models import Student, Department, StudentEventAllocation
from engine.group_allocator import GroupAllocator

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    session = SessionLocal()
    session.query(StudentEventAllocation).delete()
    session.query(Student).delete()
    session.query(Department).delete()
    session.commit()
    session.close()

def test_group_allocation_determinism_and_immutability():
    session = SessionLocal()

    d1 = Department(name="Computer Science", code="CSE")
    d2 = Department(name="Mechanical Eng", code="MECH")
    session.add_all([d1, d2])
    session.commit()

    # Add 10 students
    students = []
    for i in range(10):
        s = Student(
            usn=f"1DS21CS{i:03d}",
            full_name=f"Student {i}",
            department_id=d1.id if i < 6 else d2.id,
            gender="Male" if i % 2 == 0 else "Female"
        )
        students.append(s)
    session.add_all(students)
    session.commit()
    d1_id = d1.id
    d2_id = d2.id
    session.close()

    # Run Group Allocation
    res1 = GroupAllocator.allocate_groups(auto_backup=False)
    assert res1.newly_allocated_groups == 10

    session = SessionLocal()
    allocated = session.query(Student).all()
    group_a_count = sum(1 for s in allocated if s.group_name == "Group A")
    group_b_count = sum(1 for s in allocated if s.group_name == "Group B")

    assert group_a_count == 5
    assert group_b_count == 5

    # Store first allocation mapping
    first_map = {s.usn: s.group_name for s in allocated}

    # Add 2 new students
    s_new1 = Student(usn="1DS21CS998", full_name="New Student 1", department_id=d1_id, gender="Female")
    s_new2 = Student(usn="1DS21CS999", full_name="New Student 2", department_id=d2_id, gender="Male")
    session.add_all([s_new1, s_new2])
    session.commit()
    session.close()

    # Re-run allocation
    res2 = GroupAllocator.allocate_groups(auto_backup=False)
    assert res2.newly_allocated_groups == 2

    # Verify IMMUTABILITY: existing students did NOT change groups!
    session = SessionLocal()
    all_stu = session.query(Student).all()
    for s in all_stu:
        if s.usn in first_map:
            assert s.group_name == first_map[s.usn], f"Student {s.usn} group changed from {first_map[s.usn]} to {s.group_name}!"
    session.close()
