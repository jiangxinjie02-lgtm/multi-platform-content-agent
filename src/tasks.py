"""Task definitions for the multi-platform content planning crew."""

from __future__ import annotations

from crewai import Agent, Task


def _brief(
    product: str,
    audience: str,
    goal: str,
    platforms: str,
    style: str,
    selling_points: str,
    revision_feedback: str = "",
) -> str:
    brief = f"""
产品：{product}
目标人群：{audience}
营销目标：{goal}
目标平台：{platforms}
内容风格：{style}
已知卖点：{selling_points or "未提供，请只根据产品常识提出谨慎建议，不得虚构参数"}
"""
    if revision_feedback:
        brief += f"""
上次审核返工意见（本轮必须逐项修正）：
{revision_feedback}
"""
    return brief


def create_strategy_task(agent: Agent, **inputs: str) -> Task:
    brief = _brief(**inputs)
    return Task(
        description=f"""
根据以下需求制定内容策略：
{brief}

请完成：
1. 提炼目标用户的核心痛点和使用场景。
2. 梳理 3 个可以被内容表达的产品卖点。
3. 设计 3 个选题方向，并为每个选题说明内容角度、情绪价值和转化路径。
4. 选择一个主选题供后续 Agent 执行。
5. 明确禁止虚构的参数和需要谨慎表达的内容。
""",
        expected_output=(
            "中文内容策略，包括用户洞察、卖点、三个选题、主选题、核心信息和风险边界。"
        ),
        agent=agent,
    )


def create_copy_task(agent: Agent, strategy_task: Task, **inputs: str) -> Task:
    brief = _brief(**inputs)
    return Task(
        description=f"""
根据输入需求和上游内容策略创作一套母版内容：
{brief}

必须包含：
1. 主标题和一句话内容定位。
2. 3 秒开场钩子。
3. 60 秒以内的完整口播稿。
4. 6 个以内的分镜建议（画面、台词、时长）。
5. 清晰但不过度营销的行动引导。
6. 不得增加输入中没有的具体参数、功效数据或绝对化结论。
""",
        expected_output="可直接拍摄的中文母版文案，包含标题、钩子、口播、分镜和 CTA。",
        agent=agent,
        context=[strategy_task],
    )


def create_platform_task(agent: Agent, copy_task: Task, **inputs: str) -> Task:
    brief = _brief(**inputs)
    return Task(
        description=f"""
将上游母版内容适配到目标平台：
{brief}

如果目标平台包含抖音，输出：
- 抖音标题
- 3 秒钩子
- 口播稿
- 分镜表
- 5 个以内话题标签

如果目标平台包含小红书，输出：
- 3 个种草标题
- 封面文案
- 分段正文
- 卖点清单
- 8 个以内话题标签

两个平台必须有明显表达差异，不能只是换标题。
最终答案只输出可发布内容，不要复述审核意见、被删除的参数或修改过程。
""",
        expected_output="按平台分区的最终内容方案，结构清晰，可直接复制使用。",
        agent=agent,
        context=[copy_task],
    )


def create_review_task(agent: Agent, platform_task: Task, **inputs: str) -> Task:
    brief = _brief(**inputs)
    return Task(
        description=f"""
审核上游平台内容：
{brief}

逐项检查：
1. 是否虚构产品参数或用户未提供的信息。
2. 是否包含“最好、第一、百分百、保证”等绝对化或高风险承诺。
3. 是否存在敏感、歧视、攻击或不适合公开发布的表达。
4. 抖音与小红书内容是否有真实的平台差异。
5. 是否包含标题、钩子、正文/口播、CTA 和标签。
6. 内容是否可拍摄、可理解、与营销目标一致。

输出必须以以下一行开头：
REVIEW_STATUS: PASS
或
REVIEW_STATUS: REVISE

如果需要修改，列出具体问题和逐条修改建议；如果通过，也要说明通过原因。
""",
        expected_output="带 REVIEW_STATUS 的中文审核报告和明确修改建议。",
        agent=agent,
        context=[platform_task],
    )


def get_all_tasks(agents: dict[str, Agent], **inputs: str) -> list[Task]:
    strategy = create_strategy_task(agents["strategy"], **inputs)
    copy = create_copy_task(agents["copywriter"], strategy, **inputs)
    platform = create_platform_task(agents["platform"], copy, **inputs)
    review = create_review_task(agents["compliance"], platform, **inputs)
    return [strategy, copy, platform, review]
