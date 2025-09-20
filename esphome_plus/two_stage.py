import click
import functools
import os
import socket
import sys
import time

from esphome.__main__ import run_esphome
from esphome import espota2
from esphome.config import read_config, strip_default_ids
from esphome.core import CORE
from esphome.util import OrderedDict
from esphome.yaml_util import dump


class OTABinarySizeError(Exception):
    pass


@click.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("config_path", type=click.Path(exists=True))
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def two_stage(config_path, args):
    perform_two_stage(config_path, args)


@click.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("config_path", type=click.Path(exists=True))
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def run_minimal(config_path, args):
    install_minimal_esphome(config_path, wait_for_ota=False, *args)


def perform_two_stage(config_path, args):
    try:
        with OTABinarySizeErrorCatcher():
            CORE.reset()

            run_esphome(["esphome", "run", config_path, *args])
    except OTABinarySizeError as e:
        # If we get an OTA error, we need to run esphome again with --no-logs
        # to get the full error message
        click.echo(
            click.style(
                "Error binary size, starting two stage upgrade...", fg="yellow"
            ),
            err=True,
        )
        click.echo("Installing minimal esphome...", err=True)
        install_minimal_esphome(config_path, *args)

        click.echo("Retrying OTA update...", err=True)
        # then retry the OTA update
        CORE.reset()
        run_esphome(["esphome", "run", config_path, *args])


class OTABinarySizeErrorCatcher:
    def __init__(self):
        self.old_perform_ota = None

    def __enter__(self):
        self.old_perform_ota = espota2.perform_ota
        espota2.perform_ota = self.perform_ota_factory()

    def __exit__(self, *args):
        espota2.perform_ota = self.old_perform_ota
        self.old_perform_ota = None

    def perform_ota_factory(self):
        def perform_ota(*args, **kwargs):
            try:
                ret = self.old_perform_ota(*args, **kwargs)
            except espota2.OTAError as e:
                if not str(e).startswith("Error binary size"):
                    return ret

                raise OTABinarySizeError(str(e)) from e

        return perform_ota


# read the config file and generate a minimal version, then install it
def install_minimal_esphome(config_path, wait_for_ota=True, *args):
    minimal_esphome = MinimalEsphome(config_path)
    minimal_esphome.generate_minimal_config()
    CORE.reset()
    run_esphome(
        [
            "esphome",
            "run",
            minimal_esphome.minimal_config_path,
            "--no-logs",
            *args,
        ]
    )

    if wait_for_ota:
        wait_for_ota(
            minimal_esphome.minimal_config["wifi"]["use_address"],
            minimal_esphome.minimal_config["ota"][0]["port"],
        )

    os.remove(minimal_esphome.minimal_config_path)


def wait_for_ota(host, port):
    click.echo("Waiting for OTA and reboot to complete...")

    host = socket.gethostbyname(host)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 2 minutes should be enough for OTA and reboot to complete
    sock.settimeout(120.0)
    click.echo(f"Trying to connect to OTA server ({host}:{port})...")
    try:
        sock.connect((host, port))
    finally:
        sock.close()
    click.echo("OTA successful!")


class MinimalEsphome:
    def __init__(self, full_config_path):
        self.full_config_path = full_config_path

    @functools.cached_property
    def minimal_config_path(self):
        base, ext = os.path.splitext(self.full_config_path)
        head, tail = os.path.split(base)
        return head + "/." + tail + ".minimal" + ext

    @functools.cached_property
    def full_config(self):
        CORE.reset()
        CORE.config_path = self.full_config_path
        return strip_default_ids(read_config({}))

    @functools.cached_property
    def minimal_config(self):
        # CORE.config_path = self.minimal_config_path

        platform = self.platform(self.full_config)

        config = pluck_config(
            self.full_config,
            ["esphome", platform, "logger", "wifi", "ota", "captive_portal"],
        )

        config["esphome"]["build_path"] = "build/minimal/" + platform
        config["esphome"]["name"] += "-minimal"
        return config

    def generate_minimal_config(self):
        with open(self.minimal_config_path, "w") as f:
            f.write(dump(self.minimal_config, show_secrets=True))

    def platform(self, config):
        if "esp32" in config:
            return "esp32"
        elif "esp8266" in config:
            return "esp8266"
        elif "bk72xx" in config:
            return "bk72xx"
        else:
            raise ValueError("Unknown platform")


def pluck_config(
    source: OrderedDict, keys: list, skip_missing: bool = True
) -> OrderedDict:
    """Extract specified keys from source OrderedDict.

    Args:
        source: Source OrderedDict to pluck from
        keys: List of keys to extract
        skip_missing: If True, skip keys that don't exist. If False, raise KeyError

    Returns:
        OrderedDict containing only the specified keys
    """
    result = OrderedDict()
    for key in keys:
        if key in source:
            result[key] = source[key]
        elif not skip_missing:
            raise KeyError(f"Required key '{key}' not found in config")
    return result
