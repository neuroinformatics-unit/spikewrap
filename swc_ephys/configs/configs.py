import os
from pathlib import Path

import yaml


def get_configs(name):
    """
    TODO: must be a better way to handle path
    """
    config_dir = Path(os.path.dirname(os.path.realpath(__file__)))
    with open(config_dir / f"{name}.yaml") as file:
        config = yaml.full_load(file)

    pp_steps = config["preprocessing"]
    sorter_options = config["sorting"]

    return pp_steps, sorter_options
