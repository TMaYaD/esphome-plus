# ESPHome Plus

ESPHome Plus is an extension of the popular [ESPHome](https://esphome.io/) framework, designed to enhance the management of ESPHome YAML configurations and devices. It offers all the commands available in ESPHome and adds a new `reconcile` command to simplify the process of updating device configurations. This tool allows you to compare the YAML configurations on your device with the local files and apply any differences interactively.

## Features

- Supports all commands available in ESPHome.
- Introduces a new `reconcile` command for easy configuration management.
- Provides a convenient way to sync device configurations with local YAML files.

## Installation

Make sure you have [Python](https://www.python.org/) and [Poetry](https://python-poetry.org/) installed. Then, you can install ESPHome Plus using Poetry:

```bash
poetry install esphome-plus
```

## Usage

ESPHome Plus offers all the commands available in ESPHome. You can use these commands just like in ESPHome. In addition, ESPHome Plus introduces the `reconcile` command.

## Reconcile

The `reconcile` command in ESPHome Plus is designed to simplify the management of your ESPHome YAML configurations and devices. This tool is specifically created to use with gitops model. You can point it to your desired config and it will update the devices as required. It identifies any differences between your local YAML files and the device's configurations and allows you to interactively apply these changes.

### Command Syntax

To use the `reconcile` command, follow the syntax below:

```shell
esphome-plus reconcile [OPTIONS] CONFIG_PATH [ARGS]...
```

- `CONFIG_PATH`: This is the path to the YAML configuration file or directory containing YAML files you want to reconcile with the device.

- `ARGS` (Additional Arguments): You can include additional arguments to be passed to the esphome run command when reconciling your configurations. This allows you to customize and fine-tune the reconciliation process to suit your specific needs.

### Description

The `reconcile` command works by reading the YAML file(s) at `CONFIG_PATH` and comparing them to the configurations currently running on your device. If there are any variations or differences, the tool will prompt you to decide whether to apply these changes to your device. You have the flexibility to review and select which updates to apply and which ones to skip.

### Options

The following options are available when using the `reconcile` command:

- `-q, --quiet`: Use this option to hide verbose output.
- `-a, --ask`: Use this option to ask for confirmation before applying changes.
- `-d, --dry-run`: Use this option to preview changes without actually applying them.

### Example

Here's an example of how to use the `reconcile` command:

```shell
esphome-plus reconcile /path/to/your/config.yaml -a
```

In this example, the tool will reconcile the configuration in the specified YAML file interactively.

The `reconcile` command in ESPHome Plus offers an efficient way to keep your device configurations in sync with your local YAML files, making it easier to manage and maintain your ESPHome devices.

---

Thank you for using ESPHome Plus! We hope this tool makes managing your ESPHome devices easier and more efficient. If you encounter any issues or have suggestions for improvements, please let us know. Your feedback is valuable to us.
