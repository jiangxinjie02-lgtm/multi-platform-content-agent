#!/usr/bin/env python3
"""CLI entry point for the multi-platform content planning Agent."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .flow import ContentPlanningFlow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="使用 CrewAI + DeepSeek 生成抖音/小红书内容策划方案",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("product", help="产品或服务名称")
    parser.add_argument("--audience", required=True, help="目标人群")
    parser.add_argument("--goal", default="提升内容互动和购买转化", help="营销目标")
    parser.add_argument(
        "--platforms",
        default="抖音,小红书",
        help="目标平台，用逗号分隔，目前支持抖音、小红书",
    )
    parser.add_argument("--style", default="年轻、真实、自然", help="内容风格")
    parser.add_argument("--selling-points", default="", help="已知卖点，避免模型虚构参数")
    parser.add_argument("--max-retries", type=int, default=2, help="最大审核生成次数")
    parser.add_argument("-o", "--output", type=Path, help="Markdown 输出路径")
    return parser.parse_args()


def default_output_path(product: str) -> Path:
    safe = "".join(c if c.isalnum() else "-" for c in product).strip("-")[:40]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir / f"{safe or 'content-plan'}-{timestamp}.md"


def main() -> int:
    args = parse_args()
    output_path = args.output or default_output_path(args.product)
    flow = ContentPlanningFlow()
    try:
        flow.kickoff(
            inputs={
                "product": args.product,
                "audience": args.audience,
                "goal": args.goal,
                "platforms": args.platforms,
                "style": args.style,
                "selling_points": args.selling_points,
                "max_review_attempts": args.max_retries,
            }
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(flow.state.final_content, encoding="utf-8")
        print(f"生成完成：{output_path}")
        print(f"审核通过：{flow.state.review_passed}")
        print(f"审核次数：{flow.state.review_attempts}")
        return 0 if not flow.state.errors else 1
    except Exception as exc:
        print(f"运行失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
