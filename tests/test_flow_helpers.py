from src.flow import (
    ContentPlanningFlow,
    find_risky_claims,
    review_is_passed,
    validate_brief,
    validate_video_options,
)


def test_valid_brief():
    assert validate_brief("无线蓝牙耳机", "大学生", "抖音,小红书") == []


def test_invalid_product():
    assert "产品名称不能为空或过短" in validate_brief("", "大学生", "抖音")


def test_invalid_platform():
    assert "目标平台目前仅支持抖音和小红书" in validate_brief(
        "耳机", "大学生", "微博"
    )


def test_valid_video_options():
    assert validate_video_options("用户提供素材", "产品展示", "30 秒") == []


def test_invalid_video_options():
    errors = validate_video_options("素材随便来", "长纪录片", "5 分钟")

    assert "素材来源选项不受支持" in errors
    assert "视频类型选项不受支持" in errors
    assert "视频时长目前支持 15 秒、30 秒和 60 秒" in errors


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


def test_final_content_includes_video_package():
    flow = ContentPlanningFlow()
    flow.state.product = "无线蓝牙耳机"
    flow.state.audience = "大学生"
    flow.state.platforms = "抖音"
    flow.state.strategy_output = "策略"
    flow.state.copy_output = "文案"
    flow.state.platform_output = "平台"
    flow.state.review_output = "REVIEW_STATUS: PASS"
    flow.state.video_output = "分镜表\nSRT 字幕草稿"
    flow.state.review_passed = True
    flow.state.review_attempts = 1

    content = flow.finalize_content()

    assert "## 五、视频生产包" in content
    assert "素材来源：用户不提供素材，由 AI 生成素材建议" in content
    assert "视频类型：图文快闪" in content
    assert "分镜表" in content
