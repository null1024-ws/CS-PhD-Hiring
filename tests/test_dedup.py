from dedup import identity_key, merge_records


def test_same_pi_two_posts_merge() -> None:
    records = [
        {
            "pi_name": "陈思远",
            "school_canonical": "香港科技大学",
            "school_country": "中国香港",
            "school_status": "verified",
            "types": ["phd"],
            "source": {"url": "https://xhs.example/1", "note_id": "n1"},
        },
        {
            "pi_name": "陈思远",
            "school_canonical": "香港科技大学",
            "school_country": "中国香港",
            "school_status": "verified",
            "types": ["intern"],
            "source": {"url": "https://xhs.example/2", "note_id": "n2"},
        },
    ]
    merged = merge_records(records)
    assert len(merged) == 1
    assert set(merged[0].opportunity_types) == {"phd", "intern"}
    assert len(merged[0].sources) == 2


def test_same_name_different_school_not_merged() -> None:
    records = [
        {"pi_name": "陈思远", "school_canonical": "香港科技大学", "types": ["phd"], "source": {"url": "a"}},
        {"pi_name": "陈思远", "school_canonical": "麻省理工学院", "types": ["phd"], "source": {"url": "b"}},
    ]
    assert len(merge_records(records)) == 2


def test_unknown_school_same_name_not_merged() -> None:
    records = [
        {"pi_name": "张三", "school_canonical": "未知", "types": ["phd"], "source": {"url": "a"}},
        {"pi_name": "张三", "school_canonical": None, "types": ["ra"], "source": {"url": "b"}},
    ]
    assert identity_key("张三", "未知") is None
    assert len(merge_records(records)) == 2
