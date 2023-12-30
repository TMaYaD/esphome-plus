import click


@click.group()
@click.version_option()
def cli():
    pass


from .reconcile import reconcile

cli.add_command(reconcile)

from .register import register

cli.add_command(register)

from .upstream import add_upsteam_commands_to

add_upsteam_commands_to(cli)
