"""Xiaohongshu search queries for CS hiring posts."""

GLOBAL_QUERIES = [
    "CS PhD 招生",
    "新ap招生",
    "新晋AP招生",
    "incoming AP 招生",
    "新博导招生",
    "新AP 招博士",
    "计算机 博士 招生 2026",
    "计算机 博士 招生 2027",
    "招收 PhD intern",
    "组里招 RA",
    "CS 暑研 招生",
    "机器学习 博士 招生",
    "LLM 博士 招生",
    "机器人 博士 招生",
    "系统安全 博士 招生",
    "HCI PhD hiring",
    "computer science PhD opening",
]

AREA_QUERIES = [
    "NLP 博士 招生",
    "计算机视觉 博士 招生",
    "MLSys 博士 招生",
    "Trustworthy AI PhD",
]


def all_queries() -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for query in [*GLOBAL_QUERIES, *AREA_QUERIES]:
        if query not in seen:
            seen.add(query)
            out.append(query)
    return out
