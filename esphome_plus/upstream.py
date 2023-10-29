import click

from esphome.__main__ import run_esphome, PRE_CONFIG_ACTIONS, POST_CONFIG_ACTIONS


def make_wrapper(name):
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def wrapped(args):
        run_esphome(["esphome", name, *args])

    return wrapped


def add_upsteam_commands_to(run):
    for action in [*PRE_CONFIG_ACTIONS.keys(), *POST_CONFIG_ACTIONS.keys()]:
        run.command(name=action, context_settings=dict(ignore_unknown_options=True))(
            make_wrapper(action)
        )
