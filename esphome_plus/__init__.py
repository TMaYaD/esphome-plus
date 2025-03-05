import click


@click.group()
@click.version_option()
def cli():
    pass


from .reconcile import reconcile

cli.add_command(reconcile)

from .register import register

cli.add_command(register)

from .two_stage import two_stage, run_minimal

cli.add_command(two_stage)
cli.add_command(run_minimal)

from .upstream import add_upsteam_commands_to

add_upsteam_commands_to(cli)
