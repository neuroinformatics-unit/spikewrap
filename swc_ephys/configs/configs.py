import os
from pathlib import Path

import yaml


def get_configs(name):
    """
    TODO: must be a better way to handle path
    """
    config_dir = Path(os.path.dirname(os.path.realpath(__file__)))
    with open(config_dir / f"{name}.yaml") as file:
        pp_steps = yaml.full_load(file)
    return pp_steps
