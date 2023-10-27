#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import click

from esphome.__main__ import run_esphome, PRE_CONFIG_ACTIONS, POST_CONFIG_ACTIONS


@click.group()
@click.version_option()
def run():
    pass


def make_wrapped(name):
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def wrapped(args):
        run_esphome(["esphome", name, *args])

    return wrapped


for action in [*PRE_CONFIG_ACTIONS.keys(), *POST_CONFIG_ACTIONS.keys()]:
    run.command(name=action, context_settings=dict(ignore_unknown_options=True))(
        make_wrapped(action)
    )


if __name__ == "__main__":
    run()
