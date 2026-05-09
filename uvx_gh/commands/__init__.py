import importlib.metadata

import typer


def version_callback(echo: bool, *, module_name: str) -> None:
    if echo:
        version = importlib.metadata.version(module_name)
        typer.echo(f"{module_name} cli version: {version}")
        raise typer.Exit(0)
