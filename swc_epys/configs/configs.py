import os

import yaml


def get_configs(name):
    """
    TODO: must be a better way to handle path
    """
    with open(os.getcwd() / f"{name}.yaml") as file:
        pp_steps = yaml.full_load(file)
    return pp_steps
