import click
import os
import requests

from esphome.config import read_config, strip_default_ids
from esphome.core import CORE
from esphome.yaml_util import dump


@click.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("config_path", type=click.Path(exists=True))
@click.option("--url", "-u", help="Home Assistant host", required=True)
@click.option("--token", "-t", help="Home Assistant access token", required=True)
@click.option("--quite", "-q", is_flag=True, help="Hide verbose output")
@click.option("--ask", "-a", is_flag=True, help="Ask before applying changes")
@click.option(
    "--dry-run", "-d", is_flag=True, help="Show changes without applying them"
)
@click.pass_context
def register(ctx, config_path, **kwargs):
    """
    Register ESPHome device with Home Assistant.

    CONFIG_PATH can be a single YAML file or a directory of YAML files.
    If CONFIG_PATH is a directory, reconcile will apply to all .yaml files
    """

    if not os.path.isdir(config_path):
        register_file(ctx, config_path, **kwargs)
        return

    errors = {}
    # config_path is a directory. Apply reconcile_file to all .yaml files in the directory
    for file_name in sorted(os.listdir(config_path)):
        if not file_name.endswith(".yaml"):
            continue

        if file_name.startswith("."):
            continue

        try:
            register_file(
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


def register_file(ctx, config_path, quite, ask, dry_run, url, token):
    if not quite:
        click.echo(f"Registering {config_path}")

    config = load_config_from_file(config_path)
    address = config["wifi"]["use_address"]
    encryption_key = config["api"]["encryption"]["key"]
    area: str = config["esphome"]["area"]

    if not quite:
        click.echo(f"Registering {address} in {area}")

        # If there are differences, ask the user if they want to apply them
        if ask and not click.confirm("Apply these changes?"):
            return

    if dry_run:
        return

    # Apply the changes
    if url.endswith("/"):
        url = url[:-1]
    if not url.endswith("/api"):
        url += "/api"

    headers = {
        "Authorization": f"Bearer {token}",
        "content-type": "application/json",
    }

    url = f"{url}/config/config_entries/flow"
    payloads = [
        {
            "handler": "esphome",
        },
        {
            "host": address,
            "port": 6053,
        },
        {
            "noise_psk": encryption_key,
        },
        # {
        #     "area_id": area,
        # },
    ]

    # Get flow ID
    response = requests.post(
        url,
        headers=headers,
        json=payloads[0],
    )

    if response.status_code != 200:
        raise Exception(f"Error creating flow: {response.text}")

    flow_id = response.json()["flow_id"]
    url = f"{url}/{flow_id}"

    for payload in payloads[1:]:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
        )

        if response.status_code != 200:
            raise Exception(f"Error creating flow: {response.text}")


def load_config_from_file(path):
    CORE.config_path = path

    # Create a Config object
    return strip_default_ids(read_config({}))
