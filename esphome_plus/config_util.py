import click
import os
import yaml

from esphome.yaml_util import dump


# Load the esphome config in yaml format and normalize it for comparison
def normalize_config(content):
    try:
        return yaml.load(content, Loader=LiteralCustomTagsLoader)
    except yaml.YAMLError as e:
        click.echo(f"Error parsing YAML: {e}", err=True)
        raise e


class LiteralCustomTagsLoader(yaml.SafeLoader):
    pass


# Custom constructor for the !secret tag
def custom_tag_constructor(loader, node):
    # Extract the plain text value without processing
    return node.tag + " " + node.value


# Add the custom constructor for the !secret tag
LiteralCustomTagsLoader.add_constructor("!secret", custom_tag_constructor)
LiteralCustomTagsLoader.add_constructor("!lambda", custom_tag_constructor)


# Show the difference between two esphome configs
def show_diff(current_config, new_config, cols=None, context=True):
    if not cols:
        cols = get_cols() or 80

    lines_a = dump(current_config).splitlines()
    lines_b = dump(new_config).splitlines()

    try:
        from icdiff import ConsoleDiff
    except ImportError:
        from difflib import unified_diff

        diff_gerenator = unified_diff(
            lines_a, lines_b, fromfile="CURRENT", tofile="NEW"
        )
    else:
        diff_gerenator = ConsoleDiff(cols=cols).make_table(
            lines_a,
            lines_b,
            "CURRENT",
            "NEW",
            context=context,
        )
    finally:
        for line in diff_gerenator:
            click.echo(line)


def get_cols():
    if os.name == "nt":
        try:
            import struct
            from ctypes import windll, create_string_buffer

            fh = windll.kernel32.GetStdHandle(-12)  # stderr is -12
            csbi = create_string_buffer(22)
            windll.kernel32.GetConsoleScreenBufferInfo(fh, csbi)
            res = struct.unpack("hhhhHhhhhhh", csbi.raw)
            return res[7] - res[5] + 1  # right - left + 1

        except Exception:
            pass

    else:

        def ioctl_GWINSZ(fd):
            try:
                import fcntl
                import termios
                import struct

                cr = struct.unpack("hh", fcntl.ioctl(fd, termios.TIOCGWINSZ, "1234"))
            except Exception:
                return None
            return cr

        cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
        if cr and cr[1] > 0:
            return cr[1]
    return 80
