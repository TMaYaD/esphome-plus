import click
import os
import sys

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


def perform_two_stage(config_path, args):
    try:
        with OTABinarySizeErrorCatcher():
            CORE.reset()
            run_esphome(["esphome", "run", config_path, *args])
    except OTABinarySizeError as e:
        # If we get an OTA error, we need to run esphome again with --no-logs
        # to get the full error message
        install_minimal_esphome(config_path, *args)

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
def install_minimal_esphome(config_path, *args):
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
    os.remove(minimal_esphome.minimal_config_path)


class MinimalEsphome:
    def __init__(self, full_config_path):
        self.full_config_path = full_config_path
        base, ext = os.path.splitext(full_config_path)
        head, tail = os.path.split(base)
        self.minimal_config_path = head + "." + tail + ".minimal" + ext

    def full_config(self):
        CORE.config_path = self.full_config_path
        return strip_default_ids(read_config({}))

    def minimal_config(self):
        CORE.config_path = self.minimal_config_path

        full_config = self.full_config()

        config = OrderedDict()
        config["esphome"] = full_config["esphome"]
        platform = self.platform(full_config)

        config["esphome"]["build_path"] = "build/minimal/" + platform
        config[platform] = full_config[platform]

        config["logger"] = full_config["logger"]
        config["wifi"] = full_config["wifi"]
        config["ota"] = full_config["ota"]
        config["captive_portal"] = full_config["captive_portal"]

        return config

    def generate_minimal_config(self):
        with open(self.minimal_config_path, "w") as f:
            f.write(dump(self.minimal_config(), show_secrets=True))

    def platform(self, config):
        if "esp32" in config:
            return "esp32"
        elif "esp8266" in config:
            return "esp8266"
        elif "bk72xx" in config:
            return "bk72xx"
        else:
            raise ValueError("Unknown platform")
