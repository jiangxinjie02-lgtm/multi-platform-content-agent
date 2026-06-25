from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile
import io

from streamlit.testing.v1 import AppTest

from src.web_app import build_material_asset_index, build_uploaded_asset_records, build_video_project_zip


def test_web_app_renders_brief_form_without_running_model():
    app_path = Path(__file__).parents[1] / "src" / "web_app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=20)

    assert not app.exception
    assert app.text_input[0].value == "无线蓝牙耳机"
    assert app.button[0].label == "生成视频方案"


def test_uploaded_assets_are_indexed():
    uploaded_file = SimpleNamespace(
        name="product.jpg",
        type="image/jpeg",
        size=3,
        getvalue=lambda: b"abc",
    )

    records = build_uploaded_asset_records([uploaded_file])
    index = build_material_asset_index(records)

    assert records[0]["name"] == "product.jpg"
    assert records[0]["bytes"] == b"abc"
    assert "文件名：product.jpg" in index
    assert "类型：image/jpeg" in index


def test_video_project_zip_contains_plan_sections_and_assets():
    assets = [
        {
            "name": "logo.png",
            "type": "image/png",
            "size": 4,
            "bytes": b"logo",
        }
    ]
    package = """
## AI 画面提示词
镜头 1：校园宿舍产品特写

## TTS 配音稿
这是一段配音。

## SRT 字幕草稿
00:00:00,000 --> 00:00:03,000
这是一段字幕。
"""

    zip_bytes = build_video_project_zip("完整方案", package, assets)

    with ZipFile(io.BytesIO(zip_bytes)) as archive:
        names = set(archive.namelist())
        assert "plan.md" in names
        assert "video_package.md" in names
        assert "voiceover.txt" in names
        assert "subtitles.srt" in names
        assert "prompts.md" in names
        assert "assets/logo.png" in names
        assert archive.read("assets/logo.png") == b"logo"
