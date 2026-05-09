from typer_utils.utils import is_cmd_exists


def test_cmd():
    result = is_cmd_exists("cli-template")
    assert result is True
