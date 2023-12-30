import click
import os
import requests

from deepdiff import DeepDiff
from esphome.__main__ import run_esphome
from esphome.config import read_config, strip_default_ids
from esphome.core import CORE
from esphome.yaml_util import dump

from .upstream import make_wrapper
from .config_util import normalize_config, show_diff
from .two_stage import perform_two_stage


@click.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("config_path", type=click.Path(exists=True))
@click.option("--quite", "-q", is_flag=True, help="Hide verbose output")
@click.option("--ask", "-a", is_flag=True, help="Ask before applying changes")
@click.option(
    "--dry-run", "-d", is_flag=True, help="Show changes without applying them"
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def reconcile(ctx, config_path, **kwargs):
    """
    Reconcile ESPHome YAML files with a running device.

    This tool will read the YAML file(s) at CONFIG_PATH and compare them
    to the YAML files running on the device. If there are differences,
    it will prompt the user to apply them.

    CONFIG_PATH can be a single YAML file or a directory of YAML files.
    If CONFIG_PATH is a directory, reconcile will apply to all .yaml files
    """

    if not os.path.isdir(config_path):
        reconcile_file(ctx, config_path, **kwargs)
        return

    # If CONFIG_PATH is a directory, we need to pass --no-logs to esphome, otherwise
    # it will get stuck streaming logs from the first file
    kwargs["args"] += ("--no-logs",)

    errors = {}
    # config_path is a directory. Apply reconcile_file to all .yaml files in the directory
    for file_name in sorted(os.listdir(config_path)):
        if not file_name.endswith(".yaml"):
            continue

        if file_name.startswith("."):
            continue

        try:
            reconcile_file(
                ctx,
                os.path.join(config_path, file_name),
                **kwargs,
            )
        except Exception as e:
            errors[file_name] = e
        finally:
            CORE.reset()

    if errors:
        click.echo("Errors occurred while reconciling files:")
        for file_name, e in errors.items():
            click.echo(f"Error reconciling {file_name}: {e}", err=True)


def reconcile_file(ctx, config_path, quite, ask, dry_run, args):
    if not quite:
        click.echo(f"Reconciling {config_path}")

    config = load_config_from_file(config_path)
    current_config = load_config_content_from_device(config)

    # Compute the semantic difference between the two YAML files
    diff = DeepDiff(
        current_config,
        config,
        ignore_order=True,
        exclude_paths=[
            "root['substitutions']",
            "root['wifi']['use_address']",
            "root['esphome']['min_version']",
        ],
    )

    if not diff:
        click.echo("No difference found")
        return

    if not quite:
        show_diff(current_config, config)

        # If there are differences, ask the user if they want to apply them
        if ask and not click.confirm("Apply these changes?"):
            return

    if dry_run:
        return

    # Apply the changes
    perform_two_stage(config_path, args)


def load_config_from_file(path):
    CORE.config_path = path

    # Create a Config object
    config = strip_default_ids(read_config({}))
    return normalize_config(dump(config))


def load_config_content_from_device(config):
    address = config["wifi"]["use_address"]

    try:
        response = requests.get(f"http://{address}/config.yaml")
        response.raise_for_status()  # Check for HTTP errors

        return normalize_config(response.text)
    except requests.exceptions.RequestException as e:
        click.echo(f"Error fetching YAML from {address}: {e}", err=True)
        raise e
