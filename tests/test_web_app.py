from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_web_app_renders_brief_form_without_running_model():
    app_path = Path(__file__).parents[1] / "src" / "web_app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=20)

    assert not app.exception
    assert app.text_input[0].value == "无线蓝牙耳机"
    assert app.button[0].label == "生成多平台方案"
