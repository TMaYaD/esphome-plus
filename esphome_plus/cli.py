#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import click


@click.group()
@click.version_option()
def run():
    pass


if __name__ == "__main__":
    run()
