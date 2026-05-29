from backend.ingestion.csv_parser import parse_patients_csv

VALID_CSV = (
    "external_id,name,sex,age,height_cm,weight_kg,LDL Cholesterol,HbA1c,"
    "heart_rate,systolic_bp,diastolic_bp,steps,sleep_hours\n"
    "SYN-0001,Ann Patel,female,34,165,60,140,5.4,72,118,76,8000,7.5\n"
    "SYN-0002,Bob Kim,male,58,178,90,95,6.1,68,135,85,5000,6.0\n"
)


def test_parse_valid_csv() -> None:
    result = parse_patients_csv(VALID_CSV)
    assert result.errors == []
    assert len(result.patients) == 2

    p0 = result.patients[0]
    assert p0.external_id == "SYN-0001"
    assert p0.name == "Ann Patel"
    assert {lab.test_name for lab in p0.labs} == {"LDL Cholesterol", "HbA1c"}
    assert len(p0.vitals) == 1
    assert p0.vitals[0].heart_rate == 72


def test_parse_empty_content() -> None:
    result = parse_patients_csv("")
    assert result.patients == []
    assert result.errors


def test_parse_bytes_with_bom() -> None:
    result = parse_patients_csv(VALID_CSV.encode("utf-8-sig"))
    assert len(result.patients) == 2


def test_parse_skips_blank_lab_cells() -> None:
    csv_text = (
        "external_id,name,sex,age,LDL Cholesterol,HbA1c\n"
        "SYN-1,Cara,female,40,,5.2\n"
    )
    result = parse_patients_csv(csv_text)
    assert result.errors == []
    labs = result.patients[0].labs
    assert [lab.test_name for lab in labs] == ["HbA1c"]


def test_parse_collects_row_errors() -> None:
    csv_text = (
        "external_id,name,sex,age\n"
        "SYN-1,Bad Age,female,999\n"
        "SYN-2,Good,male,30\n"
    )
    result = parse_patients_csv(csv_text)
    assert len(result.patients) == 1
    assert len(result.errors) == 1
    assert "Row 2" in result.errors[0]
