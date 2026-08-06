import pytest
from engine.column_mapper import ColumnMapper

def test_column_mapper_exact_and_fuzzy():
    headers = [
        "Candidate Name",
        "Univ USN",
        "Branch / Department",
        "M/F",
        "College ID",
        "Extra Random Column"
    ]
    mapping, unmapped, missing_required = ColumnMapper.map_columns(headers)

    assert mapping["Candidate Name"] == "full_name"
    assert mapping["Univ USN"] == "usn"
    assert mapping["Branch / Department"] == "department"
    assert mapping["M/F"] == "gender"
    assert mapping["College ID"] == "student_id"
    assert "Extra Random Column" in unmapped
    assert len(missing_required) == 0

def test_column_mapper_missing_required():
    headers = ["Candidate Name", "Random Header"]
    mapping, unmapped, missing_required = ColumnMapper.map_columns(headers)

    assert "USN / Registration No" in missing_required
