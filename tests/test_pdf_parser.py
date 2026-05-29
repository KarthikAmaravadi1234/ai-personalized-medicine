from backend.ingestion.pdf_parser import parse_lab_text, parse_patient_from_pdf_text

REPORT_TEXT = """
Acme Labs - Patient Report
Patient: Jane Doe

LDL Cholesterol: 142 mg/dL
HDL Cholesterol: 38 mg/dL
Triglycerides - 180 mg/dL
HbA1c 6.1 %
Glucose: 105 mg/dL
Notes: follow up in 3 months
"""


def test_parse_lab_text_extracts_known_labs() -> None:
    labs = parse_lab_text(REPORT_TEXT)
    by_name = {lab.test_name: lab for lab in labs}
    assert by_name["LDL Cholesterol"].value == 142
    assert by_name["HDL Cholesterol"].value == 38
    assert by_name["Triglycerides"].value == 180
    assert by_name["HbA1c"].value == 6.1
    assert by_name["Fasting Glucose"].value == 105  # "Glucose" alias
    assert by_name["LDL Cholesterol"].unit == "mg/dL"


def test_parse_lab_text_ignores_unknown_lines() -> None:
    labs = parse_lab_text("Random text\nBlood Pressure: 120\nFoo: 5")
    # Blood Pressure / Foo are not recognized labs.
    assert labs == []


def test_parse_lab_text_dedupes() -> None:
    text = "HbA1c: 6.1 %\nHbA1c: 7.0 %"
    labs = parse_lab_text(text)
    assert len(labs) == 1
    assert labs[0].value == 6.1


def test_parse_patient_from_pdf_text() -> None:
    patient = parse_patient_from_pdf_text(REPORT_TEXT, name="report_jane")
    assert patient.name == "report_jane"
    assert len(patient.labs) == 5
