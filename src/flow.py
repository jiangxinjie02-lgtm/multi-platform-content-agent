"""Flow orchestration for multi-platform content planning."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from crewai.flow.flow import Flow, listen, or_, router, start
from pydantic import BaseModel, Field

from .crew import ContentPlanningCrew


SUPPORTED_PLATFORMS = {"抖音", "小红书"}


def validate_brief(product: str, audience: str, platforms: str) -> list[str]:
    errors = []
    if len(product.strip()) < 2:
        errors.append("产品名称不能为空或过短")
    if len(audience.strip()) < 2:
        errors.append("目标人群不能为空或过短")
    selected = {p.strip() for p in platforms.replace("，", ",").split(",") if p.strip()}
    if not selected:
        errors.append("至少选择一个目标平台")
    elif not selected.issubset(SUPPORTED_PLATFORMS):
        errors.append("目标平台目前仅支持抖音和小红书")
    return errors


def review_is_passed(review_output: str) -> bool:
    return "REVIEW_STATUS: PASS" in review_output.upper()


def find_risky_claims(content: str, supplied_facts: str) -> list[str]:
    """Detect claims that should not be trusted to an LLM-only reviewer."""
    risks: list[str] = []
    facts = supplied_facts.lower()
    disclaimer_markers = ("删除", "不得", "禁止", "未提供", "风险", "审核意见")
    scannable_content = "\n".join(
        line
        for line in content.splitlines()
        if not any(marker in line for marker in disclaimer_markers)
    )

    metric_pattern = re.compile(
        r"\d+(?:\.\d+)?\s*(?:%|ms|毫秒|小时|h\+?|克|g)",
        re.IGNORECASE,
    )
    for metric in dict.fromkeys(metric_pattern.findall(scannable_content)):
        if metric.lower() not in facts:
            risks.append(f"发现未由用户提供的量化参数：{metric}")

    risky_phrases = (
        "续航天花板",
        "百分百",
        "保证",
        "最轻",
        "最快",
        "最好",
        "完全同步",
        "一点感觉都没有",
        "耳朵不痛",
        "耳朵也不胀痛",
        "亲测不踩雷",
        "直接冲",
        "冲就完了",
        "像没戴一样",
        "从早八到晚十一",
        "从下午打到熄灯",
    )
    for phrase in risky_phrases:
        if phrase in scannable_content and phrase not in supplied_facts:
            risks.append(f"发现需要降级或核实的营销表达：{phrase}")
    return risks


class ContentFlowState(BaseModel):
    product: str = ""
    audience: str = ""
    goal: str = "提升内容互动和购买转化"
    platforms: str = "抖音,小红书"
    style: str = "年轻、真实、自然"
    selling_points: str = ""

    brief_validated: bool = False
    strategy_output: str = ""
    copy_output: str = ""
    platform_output: str = ""
    review_output: str = ""

    review_passed: bool = False
    review_attempts: int = 0
    max_review_attempts: int = 2
    final_content: str = ""
    errors: list[str] = Field(default_factory=list)
    generation_metadata: dict = Field(default_factory=dict)


class ContentPlanningFlow(Flow[ContentFlowState]):
    @start()
    def validate_input(self) -> str:
        self.state.errors = validate_brief(
            self.state.product,
            self.state.audience,
            self.state.platforms,
        )
        if self.state.errors:
            return "invalid"
        self.state.brief_validated = True
        return "valid"

    @router(validate_input)
    def route_validation(self, validation_result: str) -> Literal["valid", "invalid"]:
        return "valid" if validation_result == "valid" else "invalid"

    def _run_crew(self, revision_feedback: str = "") -> None:
        crew = ContentPlanningCrew(
            product=self.state.product,
            audience=self.state.audience,
            goal=self.state.goal,
            platforms=self.state.platforms,
            style=self.state.style,
            selling_points=self.state.selling_points,
            revision_feedback=revision_feedback,
            verbose=True,
        )
        crew.run()
        outputs = crew.get_task_outputs()
        self.state.strategy_output = outputs.get("strategy", "")
        self.state.copy_output = outputs.get("copy", "")
        self.state.platform_output = outputs.get("platform", "")
        self.state.review_output = outputs.get("review", "")
        guardrail_risks = find_risky_claims(
            self.state.platform_output,
            self.state.selling_points,
        )
        if guardrail_risks:
            details = "\n".join(f"- {risk}" for risk in guardrail_risks)
            self.state.review_output = (
                "REVIEW_STATUS: REVISE\n\n"
                "确定性内容安全规则未通过，请删除或改写以下内容：\n"
                f"{details}"
            )

    @listen("valid")
    def generate_content(self) -> None:
        try:
            self._run_crew()
            self.state.review_attempts = 1
        except Exception as exc:
            self.state.errors.append(f"内容生成失败：{exc}")

    @router(generate_content)
    def route_quality(
        self,
    ) -> Literal[
        "quality_passed", "needs_revision", "max_retries", "generation_failed"
    ]:
        if self.state.errors:
            return "generation_failed"
        if review_is_passed(self.state.review_output):
            self.state.review_passed = True
            return "quality_passed"
        if self.state.review_attempts >= self.state.max_review_attempts:
            return "max_retries"
        return "needs_revision"

    @listen("needs_revision")
    def revise_content(self) -> None:
        while self.state.review_attempts < self.state.max_review_attempts:
            feedback = self.state.review_output
            self.state.review_attempts += 1
            try:
                self._run_crew(revision_feedback=feedback)
            except Exception as exc:
                self.state.errors.append(f"第 {self.state.review_attempts} 次重写失败：{exc}")
                return
            if review_is_passed(self.state.review_output):
                self.state.review_passed = True
                return

    @router(revise_content)
    def route_revision(
        self,
    ) -> Literal["quality_passed", "max_retries", "generation_failed"]:
        if self.state.errors:
            return "generation_failed"
        return "quality_passed" if self.state.review_passed else "max_retries"

    @listen(or_("quality_passed", "max_retries", "generation_failed", "invalid"))
    def finalize_content(self) -> str:
        if self.state.errors:
            details = "\n".join(f"- {error}" for error in self.state.errors)
            self.state.final_content = f"""# 内容策划生成失败

## 问题

{details}

请检查产品、目标人群、平台配置和 DeepSeek API Key 后重试。
"""
            return self.state.final_content

        status = (
            "审核通过"
            if self.state.review_passed
            else "达到最大重写次数，建议人工复核"
        )
        self.state.generation_metadata = {
            "product": self.state.product,
            "audience": self.state.audience,
            "goal": self.state.goal,
            "platforms": self.state.platforms,
            "style": self.state.style,
            "generated_at": datetime.now().isoformat(),
            "review_attempts": self.state.review_attempts,
            "review_passed": self.state.review_passed,
        }
        self.state.final_content = f"""# {self.state.product} 多平台内容策划方案

> 目标人群：{self.state.audience}
> 营销目标：{self.state.goal}
> 目标平台：{self.state.platforms}
> 内容风格：{self.state.style}
> 审核状态：{status}
> 审核次数：{self.state.review_attempts}

---

## 一、内容策略

{self.state.strategy_output}

## 二、母版文案

{self.state.copy_output}

## 三、平台适配方案

{self.state.platform_output}

## 四、内容审核报告

{self.state.review_output}
"""
        return self.state.final_content


def create_flow() -> ContentPlanningFlow:
    return ContentPlanningFlow()


def run_flow(**inputs: str) -> str:
    flow = create_flow()
    flow.kickoff(inputs=inputs)
    return flow.state.final_content
