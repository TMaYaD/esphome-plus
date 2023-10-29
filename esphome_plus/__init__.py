import click


@click.group()
@click.version_option()
def cli():
    pass

from .upstream import add_upsteam_commands_to

add_upsteam_commands_to(cli)
