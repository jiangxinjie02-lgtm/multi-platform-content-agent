"""Lightweight local MP4 draft rendering for uploaded image assets."""

from __future__ import annotations

import tempfile
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


IMAGE_MIME_PREFIX = "image/"
VIDEO_SIZE = (720, 1280)
FPS = 24


def image_asset_records(asset_records: list[dict]) -> list[dict]:
    return [
        asset
        for asset in asset_records
        if str(asset.get("type", "")).startswith(IMAGE_MIME_PREFIX)
    ]


def can_render_preview(asset_records: list[dict]) -> bool:
    return bool(image_asset_records(asset_records))


def _load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def _fit_image(image: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    image = image.convert("RGB")
    target_w, target_h = target_size
    scale = min(target_w / image.width, target_h / image.height)
    resized = image.resize(
        (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
        Image.Resampling.LANCZOS,
    )

    canvas = Image.new("RGB", target_size, (16, 18, 24))
    x = (target_w - resized.width) // 2
    y = (target_h - resized.height) // 2
    canvas.paste(resized, (x, y))
    return canvas


def _draw_text_box(
    image: Image.Image,
    text: str,
    y: int,
    font: ImageFont.ImageFont,
    max_width: int,
) -> None:
    if not text:
        return

    draw = ImageDraw.Draw(image, "RGBA")
    words = list(text)
    lines: list[str] = []
    current = ""
    for word in words:
        trial = current + word
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    line_height = font.size + 12 if hasattr(font, "size") else 36
    box_h = line_height * len(lines) + 28
    box_x = 48
    box_y = y
    draw.rounded_rectangle(
        (box_x, box_y, image.width - box_x, box_y + box_h),
        radius=18,
        fill=(0, 0, 0, 160),
    )

    text_y = box_y + 14
    for line in lines:
        draw.text((box_x + 20, text_y), line, font=font, fill=(255, 255, 255, 255))
        text_y += line_height


def make_preview_frame(
    image: Image.Image,
    title: str,
    subtitle: str,
    asset_name: str,
    frame_size: tuple[int, int] = VIDEO_SIZE,
) -> Image.Image:
    frame = _fit_image(image, frame_size)
    title_font = _load_font(42)
    subtitle_font = _load_font(34)
    meta_font = _load_font(24)

    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    draw.rectangle((0, 0, frame.width, 150), fill=(0, 0, 0, 118))
    draw.rectangle((0, frame.height - 220, frame.width, frame.height), fill=(0, 0, 0, 132))
    frame = Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")

    _draw_text_box(frame, title, 42, title_font, frame.width - 120)
    _draw_text_box(frame, subtitle, frame.height - 180, subtitle_font, frame.width - 120)

    draw = ImageDraw.Draw(frame, "RGBA")
    draw.text((52, frame.height - 54), f"素材：{asset_name}", font=meta_font, fill=(230, 235, 245, 230))
    return frame


def render_preview_video(
    asset_records: list[dict],
    title: str,
    subtitle: str,
    seconds_per_asset: int = 3,
) -> bytes:
    image_records = image_asset_records(asset_records)
    if not image_records:
        raise ValueError("至少需要上传一张图片素材才能生成 MP4 草稿。")

    try:
        import imageio.v2 as imageio
    except ImportError as exc:
        raise RuntimeError("缺少 imageio/imageio-ffmpeg，无法生成 MP4 草稿。") from exc

    frames_per_asset = FPS * seconds_per_asset
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as output:
        output_path = Path(output.name)

    try:
        with imageio.get_writer(
            str(output_path),
            fps=FPS,
            codec="libx264",
            macro_block_size=16,
        ) as writer:
            for asset in image_records:
                with Image.open(BytesIO(asset["bytes"])) as source:
                    frame = make_preview_frame(
                        source,
                        title=title,
                        subtitle=subtitle,
                        asset_name=asset["name"],
                    )
                frame_data = np.asarray(frame)
                for _ in range(frames_per_asset):
                    writer.append_data(frame_data)
        return output_path.read_bytes()
    finally:
        output_path.unlink(missing_ok=True)
