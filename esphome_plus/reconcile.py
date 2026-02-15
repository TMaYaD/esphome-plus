import traceback
import click
import functools
import os
import requests
from pathlib import Path
from deepdiff import DeepDiff
from esphome.config import read_config, strip_default_ids
from esphome.core import CORE
from esphome.yaml_util import dump
from .config_util import normalize_config, show_diff
from .two_stage import perform_two_stage


class ConfigError(Exception):
    pass


class UpstreamConfigError(Exception):
    pass


@click.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("config_path", type=click.Path(exists=True))
@click.option("--quite", "-q", is_flag=True, help="Hide verbose output")
@click.option("--ask", "-a", is_flag=True, help="Ask before applying changes")
@click.option(
    "--dry-run", "-d", is_flag=True, help="Show changes without applying them"
)
@click.option("--timeout", "-t", type=int, help="Timeout for the device config request")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def reconcile(
    ctx, config_path, dry_run=False, verbose=False, **kwargs
):  # pylint: disable=unused-argument
    """
    Reconcile ESPHome YAML files with a running device.

    This tool will read the YAML file(s) at CONFIG_PATH and compare them
    to the YAML files running on the device. If there are differences,
    it will prompt the user to apply them.

    CONFIG_PATH can be a single YAML file or a directory of YAML files.
    If CONFIG_PATH is a directory, reconcile will apply to all .yaml files
    """

    config_files = get_config_files(config_path)
    if len(config_files) > 1:
        # If CONFIG_PATH is a directory(or more than one file), we need to pass --no-logs to esphome, otherwise
        # it will get stuck streaming logs from the first file
        kwargs["args"] += ("--no-logs",)

    reconcilers = [ReconcileService(file_name, **kwargs) for file_name in config_files]
    pending_changes = [
        reconciler
        for reconciler in reconcilers
        if reconciler.compare_and_decide() and not reconciler.errors
    ]

    if dry_run:
        click.echo("Dry run, no changes will be applied")
        return

    for reconciler in pending_changes:
        reconciler.apply_changes()

    if any(reconciler.errors for reconciler in reconcilers):
        click.echo("Errors occurred while reconciling files:")
        for reconciler in reconcilers:
            for e in reconciler.errors:
                click.echo(f"Error reconciling {reconciler.config_path}: {e}", err=True)
                if verbose:
                    click.echo("".join(traceback.format_exception(e)), err=True)


class ReconcileService:
    """Service class to handle ESPHome configuration reconciliation."""

    def __init__(self, config_path, quite=False, ask=False, args=None, timeout=30):
        self.config_path = config_path
        self.quite = quite
        self.ask = ask
        self.args = args or []
        self.errors = []
        self.timeout = timeout

        # Exclude paths for diff comparison
        self.exclude_paths = [
            "root['substitutions']",
            "root['wifi']['use_address']",
            "root['esphome']['min_version']",
        ]

    @functools.cached_property
    def file_config(self):
        """Load configuration from the specified file."""
        CORE.reset()
        CORE.config_path = Path(self.config_path)

        # Create a Config object
        config = strip_default_ids(read_config({}))
        normalized_config = normalize_config(dump(config))

        if not normalized_config:
            raise ConfigError(f"Could not load config from {self.config_path}")
        return normalized_config

    @functools.cached_property
    def device_config(self):
        """Load current configuration from the device."""
        address = self.file_config["wifi"]["use_address"]

        try:
            response = requests.get(
                f"http://{address}/config.yaml", timeout=self.timeout
            )
            response.raise_for_status()  # Check for HTTP errors

            return normalize_config(response.text)
        except requests.exceptions.RequestException as e:
            raise UpstreamConfigError(f"Error fetching YAML from {address}: {e}") from e

    def compare_and_decide(self):
        """Compare configurations and determine if changes should be applied."""
        click.echo(f"Comparing configurations for {self.config_path}: ", nl=False)
        diff = None
        try:
            diff = DeepDiff(
                self.device_config,
                self.file_config,
                ignore_order=True,
                exclude_paths=self.exclude_paths,
            )
        except Exception as e:
            click.echo("Error comparing configurations")
            self.errors.append(e)
            return False

        if not diff:
            click.echo("No difference found")
            return False

        if not self.quite:
            click.echo("Differences found:")
            show_diff(self.device_config, self.file_config)

        if not self.ask:
            return True

        return click.confirm("Apply these changes?")

    def apply_changes(self):
        """Apply changes to the device."""
        try:
            CORE.reset()
            perform_two_stage(self.config_path, self.args)
        except Exception as e:
            self.errors.append(e)


def get_config_files(config_path):
    """Get list of YAML config files from path, respecting .esphomeignore."""
    if not os.path.isdir(config_path):
        return [config_path]

    # Read .esphomeignore file if it exists
    ignore_patterns = []
    ignore_file = os.path.join(config_path, ".esphomeignore")
    if os.path.exists(ignore_file):
        with open(ignore_file, encoding="utf-8") as f:
            ignore_patterns = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]

    # config_path is a directory. Apply reconcile_file to all .yaml files in the directory
    yaml_files = []
    for file_name in sorted(os.listdir(config_path)):
        if not file_name.endswith(".yaml"):
            continue

        if file_name.startswith("."):
            continue

        # Skip if file matches any ignore pattern
        if any(pattern in file_name for pattern in ignore_patterns):
            continue

        yaml_files.append(os.path.join(config_path, file_name))

    return yaml_files
