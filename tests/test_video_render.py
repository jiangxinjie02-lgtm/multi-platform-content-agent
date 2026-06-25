from io import BytesIO

from PIL import Image

from src.video_render import can_render_preview, image_asset_records, make_preview_frame


def test_image_asset_records_filters_images():
    records = [
        {"name": "product.jpg", "type": "image/jpeg", "bytes": b"image"},
        {"name": "clip.mp4", "type": "video/mp4", "bytes": b"video"},
    ]

    assert image_asset_records(records) == [records[0]]
    assert can_render_preview(records) is True
    assert can_render_preview([records[1]]) is False


def test_make_preview_frame_returns_vertical_rgb_frame():
    image = Image.new("RGB", (320, 240), "white")

    frame = make_preview_frame(
        image,
        title="无线蓝牙耳机",
        subtitle="AI 生成视频方案粗剪预览",
        asset_name="product.jpg",
    )

    assert frame.mode == "RGB"
    assert frame.size == (720, 1280)


def test_preview_frame_can_be_saved_as_jpeg():
    image = Image.new("RGB", (320, 240), "white")
    frame = make_preview_frame(image, "标题", "字幕", "asset.jpg")
    output = BytesIO()

    frame.save(output, format="JPEG")

    assert output.getvalue().startswith(b"\xff\xd8")
