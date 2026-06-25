"""Streamlit interface for the multi-platform content planning Agent."""

from __future__ import annotations

import io
import os
import re
import zipfile
from datetime import datetime

import streamlit as st

from src.flow import ContentPlanningFlow, validate_brief, validate_video_options
from src.video_render import can_render_preview, render_preview_video


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
        grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
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


def safe_asset_name(name: str, fallback: str = "asset") -> str:
    clean = os.path.basename(name).replace("\\", "-").replace("/", "-").strip()
    return clean or fallback


def build_uploaded_asset_records(uploaded_files: list) -> list[dict]:
    records = []
    for index, uploaded_file in enumerate(uploaded_files, start=1):
        filename = safe_asset_name(uploaded_file.name, f"asset-{index}")
        records.append(
            {
                "name": filename,
                "type": uploaded_file.type or "application/octet-stream",
                "size": uploaded_file.size,
                "bytes": uploaded_file.getvalue(),
            }
        )
    return records


def build_material_asset_index(asset_records: list[dict]) -> str:
    if not asset_records:
        return ""

    lines = []
    for index, asset in enumerate(asset_records, start=1):
        lines.append(
            f"{index}. 文件名：{asset['name']}；类型：{asset['type']}；大小：{asset['size']} bytes"
        )
    return "\n".join(lines)


def extract_section(text: str, keyword: str) -> str:
    pattern = re.compile(
        rf"(?ims)(?:^|\n)(?:#+\s*)?(?:\d+[\.、]\s*)?.*{re.escape(keyword)}.*?\n(.*?)(?=\n(?:#+\s*)?(?:\d+[\.、]\s*)?.+：|\n#+\s|\Z)"
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else f"请参考 video_package.md 中的“{keyword}”部分。"


def build_video_project_zip(
    plan_markdown: str,
    video_package: str,
    asset_records: list[dict],
) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("plan.md", plan_markdown)
        archive.writestr("video_package.md", video_package)
        archive.writestr("voiceover.txt", extract_section(video_package, "TTS 配音稿"))
        archive.writestr("subtitles.srt", extract_section(video_package, "SRT 字幕草稿"))
        archive.writestr("prompts.md", extract_section(video_package, "AI 画面提示词"))
        archive.writestr("assets/README.md", build_material_asset_index(asset_records) or "未上传素材。")

        used_names: set[str] = set()
        for index, asset in enumerate(asset_records, start=1):
            filename = safe_asset_name(asset["name"], f"asset-{index}")
            if filename in used_names:
                stem, ext = os.path.splitext(filename)
                filename = f"{stem}-{index}{ext}"
            used_names.add(filename)
            archive.writestr(f"assets/{filename}", asset["bytes"])

    return buffer.getvalue()


def init_state() -> None:
    defaults = {
        "result": "",
        "strategy": "",
        "copy": "",
        "platform": "",
        "review": "",
        "video": "",
        "review_passed": False,
        "review_attempts": 0,
        "errors": [],
        "last_product": "",
        "uploaded_assets": [],
        "material_assets_text": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_header() -> None:
    st.markdown(PAGE_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <section class="hero">
          <h1>Multi-Platform Video Agent</h1>
          <p>输入一个产品 Brief，由 Agent 团队生成多平台内容方案、完成审核，并输出可执行的视频生产包。</p>
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
          <div class="agent-card"><b>05 视频制片</b><span>分镜、素材、提示词、配音与字幕</span></div>
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
    st.session_state.video = flow.state.video_output
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
            st.divider()
            st.caption("视频生成设置")
            material_source = st.radio(
                "素材来源",
                ["用户不提供素材，由 AI 生成素材建议", "用户提供素材"],
                horizontal=False,
            )
            video_type = st.selectbox(
                "视频类型",
                ["图文快闪", "产品展示", "口播讲解", "剧情场景"],
            )
            video_duration = st.select_slider(
                "视频时长",
                options=["15 秒", "30 秒", "60 秒"],
                value="30 秒",
            )
            material_notes = st.text_area(
                "素材说明",
                value="",
                placeholder="例如：已有 3 张产品图、1 段开箱视频、品牌 Logo；或希望画面偏校园场景。",
            )
            uploaded_files = st.file_uploader(
                "上传素材",
                type=["png", "jpg", "jpeg", "webp", "mp4", "mov", "m4v", "avi", "pdf", "txt"],
                accept_multiple_files=True,
                help="可上传产品图、视频片段、Logo、卖点文档或过往内容，系统会把素材索引交给视频 Agent。",
            )
            max_retries = st.slider("最大审核次数", 1, 3, 2)
            submitted = st.form_submit_button(
                "生成视频方案",
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
    errors.extend(validate_video_options(material_source, video_type, video_duration))
    if errors:
        for error in errors:
            st.error(error)
        return None

    asset_records = build_uploaded_asset_records(uploaded_files or [])
    material_assets = build_material_asset_index(asset_records)
    st.session_state.uploaded_assets = asset_records
    st.session_state.material_assets_text = material_assets

    return {
        "product": product,
        "audience": audience,
        "goal": goal,
        "platforms": platform_text,
        "style": style,
        "selling_points": selling_points,
        "material_source": material_source,
        "video_type": video_type,
        "video_duration": video_duration,
        "material_notes": material_notes,
        "material_assets": material_assets,
        "max_review_attempts": max_retries,
    }


def render_result() -> None:
    if not st.session_state.result:
        st.info("在左侧填写内容 Brief 和视频设置，点击“生成视频方案”开始运行。")
        with st.expander("这个系统会怎样工作？", expanded=True):
            st.markdown(
                "Flow 先校验输入，再依次调用选题、文案、平台适配、审核和视频制片 Agent。"
                "若审核或 Guardrail 不通过，系统会带着问题自动重写，直到通过或达到最大次数。"
            )
        return

    if st.session_state.errors:
        st.error("运行失败：" + "；".join(st.session_state.errors))
        return

    status_col, attempts_col, assets_col, time_col = st.columns(4)
    status_col.metric(
        "审核状态",
        "通过" if st.session_state.review_passed else "需要人工复核",
    )
    attempts_col.metric("审核次数", st.session_state.review_attempts)
    assets_col.metric("素材数量", len(st.session_state.uploaded_assets))
    time_col.metric("生成时间", datetime.now().strftime("%H:%M"))

    tabs = st.tabs(["内容策略", "母版文案", "平台方案", "审核报告", "视频生产包", "完整 Markdown"])
    values = [
        st.session_state.strategy,
        st.session_state.copy,
        st.session_state.platform,
        st.session_state.review,
        st.session_state.video,
        st.session_state.result,
    ]
    for tab, value in zip(tabs, values):
        with tab:
            st.markdown('<div class="result-card">', unsafe_allow_html=True)
            st.markdown(value or "暂无内容")
            st.markdown("</div>", unsafe_allow_html=True)

    filename = f"{st.session_state.last_product or 'content-plan'}-视频方案.md"
    st.download_button(
        "下载完整 Markdown",
        data=st.session_state.result,
        file_name=filename,
        mime="text/markdown",
        use_container_width=True,
    )
    project_filename = f"{st.session_state.last_product or 'content-plan'}-视频项目包.zip"
    st.download_button(
        "下载视频项目包",
        data=build_video_project_zip(
            st.session_state.result,
            st.session_state.video,
            st.session_state.uploaded_assets,
        ),
        file_name=project_filename,
        mime="application/zip",
        use_container_width=True,
    )

    if can_render_preview(st.session_state.uploaded_assets):
        try:
            preview_video = render_preview_video(
                st.session_state.uploaded_assets,
                title=st.session_state.last_product or "视频草稿",
                subtitle="AI 生成视频方案粗剪预览",
            )
            st.download_button(
                "下载 MP4 粗剪草稿",
                data=preview_video,
                file_name=f"{st.session_state.last_product or 'content-plan'}-粗剪草稿.mp4",
                mime="video/mp4",
                use_container_width=True,
            )
        except Exception as exc:
            st.warning(f"MP4 粗剪草稿生成失败：{exc}")
    else:
        st.caption("上传至少一张图片素材后，可下载静音 MP4 粗剪草稿。")


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
            st.write("运行选题、文案、平台适配、审核和视频制片 Agent")
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
