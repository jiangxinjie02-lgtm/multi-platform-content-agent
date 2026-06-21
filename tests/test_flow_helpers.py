from src.flow import find_risky_claims, review_is_passed, validate_brief


def test_valid_brief():
    assert validate_brief("无线蓝牙耳机", "大学生", "抖音,小红书") == []


def test_invalid_product():
    assert "产品名称不能为空或过短" in validate_brief("", "大学生", "抖音")


def test_invalid_platform():
    assert "目标平台目前仅支持抖音和小红书" in validate_brief(
        "耳机", "大学生", "微博"
    )


def test_review_status():
    assert review_is_passed("REVIEW_STATUS: PASS\n审核通过") is True
    assert review_is_passed("REVIEW_STATUS: REVISE\n需要修改") is False


def test_guardrail_rejects_unverified_metrics_and_claims():
    risks = find_risky_claims(
        "续航12h+，电量还有80%，音画完全同步，直接冲。",
        "续航时间长、低延迟",
    )
    assert any("12h+" in risk for risk in risks)
    assert any("80%" in risk for risk in risks)
    assert any("完全同步" in risk for risk in risks)


def test_guardrail_allows_supplied_metric():
    risks = find_risky_claims("单次续航12小时。", "官方参数：单次续航12小时")
    assert risks == []


def test_guardrail_ignores_removed_metric_explanation():
    risks = find_risky_claims(
        "已删除所有未由用户提供的量化参数（80%、12h）。",
        "续航时间长",
    )
    assert risks == []
