import typer
from typer_utils.utils import version_callback


def default_invoke_without_command(
    _: bool = typer.Option(False, "--version", "-v", "-V", callback=lambda echo: version_callback(echo, module_name="python-cli-template")),
): ...
