import os
from pathlib import Path
from typing import Dict, Tuple

import yaml


def get_configs(name: str) -> Tuple[Dict, Dict]:
    """
    TODO: must be a better way to handle path
    """
    config_dir = Path(os.path.dirname(os.path.realpath(__file__)))
    with open(config_dir / f"{name}.yaml") as file:
        config = yaml.full_load(file)

    pp_steps = config["preprocessing"]
    sorter_options = config["sorting"]

    # keeps type checker happy but does not require
    # Tuple in the .yaml which are ugly
    for key in pp_steps.keys():
        pp_steps[key] = tuple(pp_steps[key])

    return pp_steps, sorter_options
