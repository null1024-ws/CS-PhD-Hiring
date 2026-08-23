from relevance import classify_relevance


def test_cs_positive_examples() -> None:
    assert classify_relevance("课题组招人，方向 LLM 安全与对齐") == "cs"
    assert classify_relevance("robotics and embodied AI, human-robot interaction") == "cs"
    assert classify_relevance("HCI / 人机交互，招 PhD") == "cs"


def test_notcs_negative_examples() -> None:
    assert classify_relevance("湿实验细胞培养与蛋白质纯化，不涉及计算") == "notcs"
    assert classify_relevance("公司金融与资本市场信息的实际影响") == "notcs"


def test_ambiguous_is_not_cs() -> None:
    assert classify_relevance("欢迎对人工智能感兴趣的同学") == "review"
    assert classify_relevance("人工智能 + 湿实验细胞培养") == "review"
