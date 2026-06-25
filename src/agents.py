"""Agent definitions for the multi-platform content planning crew."""

from __future__ import annotations

import os
from functools import lru_cache

from crewai import Agent, LLM
from dotenv import load_dotenv

load_dotenv()


@lru_cache(maxsize=1)
def get_llm() -> LLM:
    """Create one shared DeepSeek LLM configuration for all agents."""
    model = os.getenv("DEEPSEEK_MODEL", "deepseek/deepseek-chat").strip()
    if "/" not in model:
        model = f"deepseek/{model}"

    return LLM(
        model=model,
        api_key=os.getenv("DEEPSEEK_API_KEY", "missing-deepseek-api-key"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        temperature=0.6,
    )


def create_strategy_agent() -> Agent:
    return Agent(
        role="内容选题策划 Agent",
        goal="根据产品、目标用户和营销目标，制定有传播价值且可执行的内容策略",
        backstory=(
            "你是一名熟悉消费品牌和内容电商的资深策略师，擅长提炼用户痛点、"
            "产品卖点、内容角度和转化路径。你拒绝空洞口号，所有选题必须与输入信息一致。"
        ),
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )


def create_copywriter_agent() -> Agent:
    return Agent(
        role="短视频文案创作 Agent",
        goal="将内容策略转化为有吸引力、口语化且能拍摄落地的内容脚本",
        backstory=(
            "你长期为消费品牌创作短视频和种草内容，擅长前三秒钩子、口播节奏、"
            "场景化表达和行动引导。你不会虚构产品参数或使用绝对化承诺。"
        ),
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )


def create_platform_agent() -> Agent:
    return Agent(
        role="平台适配 Agent",
        goal="将统一内容创意分别适配为抖音和小红书的原生表达",
        backstory=(
            "你理解抖音与小红书用户的阅读习惯和内容结构差异。"
            "抖音内容强调强钩子、口播和分镜；小红书内容强调真实体验、标题、正文层次和话题。"
        ),
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )


def create_compliance_agent() -> Agent:
    return Agent(
        role="内容审核 Agent",
        goal="检查内容真实性、合规性、平台适配度和可执行性，并给出明确审核结论",
        backstory=(
            "你是一名严格的内容质检负责人，熟悉常见广告法风险、夸大承诺、"
            "敏感表达和平台内容质量问题。你必须给出 REVIEW_STATUS: PASS 或 REVIEW_STATUS: REVISE。"
        ),
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )


def create_video_producer_agent() -> Agent:
    return Agent(
        role="短视频制片 Agent",
        goal="将审核后的内容方案转化为可执行的视频生产包，覆盖有素材和无素材两种制作路径",
        backstory=(
            "你是一名短视频制片策划，熟悉口播、产品展示、图文快闪和剧情场景视频的制作流程。"
            "你能把营销文案拆成镜头、旁白、字幕、素材清单和 AI 画面提示词，并明确哪些内容需要用户素材。"
        ),
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )


def get_all_agents() -> dict[str, Agent]:
    return {
        "strategy": create_strategy_agent(),
        "copywriter": create_copywriter_agent(),
        "platform": create_platform_agent(),
        "compliance": create_compliance_agent(),
        "video": create_video_producer_agent(),
    }
