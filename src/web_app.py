"""Streamlit interface for the multi-platform content planning Agent."""

from __future__ import annotations

import os
from datetime import datetime

import streamlit as st

from src.flow import ContentPlanningFlow, validate_brief


PAGE_CSS = """
<style>
    .stApp {
        background:
            radial-gradient(circle at 8% 2%, rgba(120, 92, 255, .13), transparent 25rem),
            radial-gradient(circle at 96% 12%, rgba(0, 190, 170, .10), transparent 28rem),
            #f7f8fc;
    }
    .block-container {max-width: 1280px; padding-top: 2.2rem;}
    [data-testid="stSidebar"] {
        background: rgba(255,255,255,.88);
        border-right: 1px solid #e8e8f1;
    }
    .hero {
        padding: 1.6rem 1.8rem;
        border-radius: 24px;
        color: white;
        background: linear-gradient(125deg, #17162d 0%, #4433a8 55%, #087f7a 120%);
        box-shadow: 0 18px 50px rgba(35, 31, 91, .18);
        margin-bottom: 1.2rem;
    }
    .hero h1 {margin: 0 0 .35rem 0; font-size: 2rem;}
    .hero p {margin: 0; opacity: .84;}
    .agent-strip {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: .65rem;
        margin: .9rem 0 1.2rem;
    }
    .agent-card {
        background: white;
        border: 1px solid #ebeaf3;
        border-radius: 16px;
        padding: .85rem;
        box-shadow: 0 7px 22px rgba(31, 30, 62, .05);
    }
    .agent-card b {color: #292550;}
    .agent-card span {display:block;color:#77738f;font-size:.82rem;margin-top:.2rem;}
    .result-card {
        background: white;
        border: 1px solid #ebeaf3;
        border-radius: 18px;
        padding: 1rem 1.2rem;
        margin-bottom: .75rem;
    }
    @media (max-width: 850px) {
        .agent-strip {grid-template-columns: repeat(2, 1fr);}
    }
</style>
"""


def init_state() -> None:
    defaults = {
        "result": "",
        "strategy": "",
        "copy": "",
        "platform": "",
        "review": "",
        "review_passed": False,
        "review_attempts": 0,
        "errors": [],
        "last_product": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_header() -> None:
    st.markdown(PAGE_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <section class="hero">
          <h1>Multi-Platform Content Agent</h1>
          <p>输入一个产品 Brief，由四个 Agent 协作生成抖音与小红书内容方案，并自动完成审核与返工。</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="agent-strip">
          <div class="agent-card"><b>01 选题策划</b><span>用户洞察、卖点、内容方向</span></div>
          <div class="agent-card"><b>02 文案创作</b><span>标题、钩子、口播与分镜</span></div>
          <div class="agent-card"><b>03 平台适配</b><span>抖音与小红书原生表达</span></div>
          <div class="agent-card"><b>04 内容审核</b><span>LLM 审核 + 确定性 Guardrail</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def run_agent(inputs: dict) -> None:
    flow = ContentPlanningFlow()
    flow.kickoff(inputs=inputs)
    st.session_state.result = flow.state.final_content
    st.session_state.strategy = flow.state.strategy_output
    st.session_state.copy = flow.state.copy_output
    st.session_state.platform = flow.state.platform_output
    st.session_state.review = flow.state.review_output
    st.session_state.review_passed = flow.state.review_passed
    st.session_state.review_attempts = flow.state.review_attempts
    st.session_state.errors = flow.state.errors
    st.session_state.last_product = inputs["product"]


def render_sidebar() -> dict | None:
    with st.sidebar:
        st.subheader("内容 Brief")
        with st.form("brief_form"):
            product = st.text_input("产品或服务", value="无线蓝牙耳机")
            audience = st.text_input("目标人群", value="大学生")
            goal = st.text_input("营销目标", value="提升购买转化")
            platforms = st.multiselect(
                "目标平台",
                ["抖音", "小红书"],
                default=["抖音", "小红书"],
            )
            style = st.selectbox(
                "内容风格",
                ["年轻、真实、自然", "专业、可信、克制", "轻松、幽默、有梗", "温暖、生活化"],
            )
            selling_points = st.text_area(
                "已知卖点",
                value="低延迟、续航时间长、佩戴轻便",
                help="只填写能够确认的事实，Guardrail 会拦截模型虚构的量化参数。",
            )
            max_retries = st.slider("最大审核次数", 1, 3, 2)
            submitted = st.form_submit_button(
                "生成多平台方案",
                type="primary",
                use_container_width=True,
            )

        st.caption(
            "DeepSeek Key："
            + ("已配置" if os.getenv("DEEPSEEK_API_KEY") else "未配置")
        )

    if not submitted:
        return None

    platform_text = ",".join(platforms)
    errors = validate_brief(product, audience, platform_text)
    if errors:
        for error in errors:
            st.error(error)
        return None

    return {
        "product": product,
        "audience": audience,
        "goal": goal,
        "platforms": platform_text,
        "style": style,
        "selling_points": selling_points,
        "max_review_attempts": max_retries,
    }


def render_result() -> None:
    if not st.session_state.result:
        st.info("在左侧填写内容 Brief，点击“生成多平台方案”开始运行。")
        with st.expander("这个系统会怎样工作？", expanded=True):
            st.markdown(
                "Flow 先校验输入，再依次调用选题、文案、平台适配和审核 Agent。"
                "若审核或 Guardrail 不通过，系统会带着问题自动重写，直到通过或达到最大次数。"
            )
        return

    if st.session_state.errors:
        st.error("运行失败：" + "；".join(st.session_state.errors))
        return

    status_col, attempts_col, time_col = st.columns(3)
    status_col.metric(
        "审核状态",
        "通过" if st.session_state.review_passed else "需要人工复核",
    )
    attempts_col.metric("审核次数", st.session_state.review_attempts)
    time_col.metric("生成时间", datetime.now().strftime("%H:%M"))

    tabs = st.tabs(["内容策略", "母版文案", "平台方案", "审核报告", "完整 Markdown"])
    values = [
        st.session_state.strategy,
        st.session_state.copy,
        st.session_state.platform,
        st.session_state.review,
        st.session_state.result,
    ]
    for tab, value in zip(tabs, values):
        with tab:
            st.markdown('<div class="result-card">', unsafe_allow_html=True)
            st.markdown(value or "暂无内容")
            st.markdown("</div>", unsafe_allow_html=True)

    filename = f"{st.session_state.last_product or 'content-plan'}-内容策划.md"
    st.download_button(
        "下载完整 Markdown",
        data=st.session_state.result,
        file_name=filename,
        mime="text/markdown",
        use_container_width=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="多平台内容策划 Agent",
        page_icon="✦",
        layout="wide",
    )
    init_state()
    render_header()
    inputs = render_sidebar()
    if inputs:
        with st.status("Agent 团队正在协作生成内容……", expanded=True) as status:
            st.write("校验 Brief 与平台配置")
            st.write("运行选题、文案、平台适配和审核 Agent")
            run_agent(inputs)
            if st.session_state.errors:
                status.update(label="生成失败", state="error")
            elif st.session_state.review_passed:
                status.update(label="生成完成，审核通过", state="complete")
            else:
                status.update(label="生成完成，建议人工复核", state="complete")
    render_result()


if __name__ == "__main__":
    main()
