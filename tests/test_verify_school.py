from verify_school import verify_school


def test_homepage_same_school_verified() -> None:
    result = verify_school(
        "港科大",
        homepage_text="Chen Siyuan, Assistant Professor, The Hong Kong University of Science and Technology",
        homepage_url="https://www.cs.ust.hk/~siyuan",
    )
    assert result.school_status == "verified"
    assert result.school_canonical == "香港科技大学"
    assert result.evidence


def test_no_evidence_unverified() -> None:
    result = verify_school("港科大")
    assert result.school_status == "unverified"
    assert result.school_canonical == "香港科技大学"


def test_conflict_is_never_verified() -> None:
    result = verify_school(
        "港科大",
        homepage_text="Now at Massachusetts Institute of Technology (MIT)",
        homepage_url="https://people.csail.mit.edu/siyuan",
        openalex_affiliations=["Massachusetts Institute of Technology"],
    )
    assert result.school_status == "conflict"
    assert result.school_status != "verified"
    assert result.suggested_school == "麻省理工学院"
    assert result.school_canonical == "香港科技大学"
