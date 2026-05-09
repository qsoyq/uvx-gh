import typer

from cli_template.commands import default_invoke_without_command

helptext = """

"""

cmd = typer.Typer(help=helptext)


def add_default_invoke():
    for _cmd in (cmd,):
        _cmd.callback(invoke_without_command=True)(default_invoke_without_command)


add_default_invoke()

if __name__ == "__main__":
    cmd()
