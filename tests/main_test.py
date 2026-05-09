import shutil


def test_cmd():
    assert shutil.which("uvx-gh") is not None
