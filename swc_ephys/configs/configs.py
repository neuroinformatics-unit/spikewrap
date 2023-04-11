import os
from pathlib import Path
from typing import Dict, Tuple

import yaml


def get_configs(name: str) -> Tuple[Dict, Dict]:
    """
    Loads the config yaml file in the same folder
    (swc_ephys/configs) containing preprocessing (pp)
    and sorter options.

    Once loaded, the list containing preprocesser name
    and kwargs is cast to tuple. This keeps the type
    checker happy while not requiring a tuple
    in the .yaml which require ugly tags.

    Parameters
    ----------

    name: name of the configs to load. Should not include the
          .yaml suffix.

    Returns
    -------

    pp_steps : a dictionary containing the preprocessing
               step order (keys) and a [pp_name, kwargs]
               list containing the spikeinterface preprocessing
               step and keyword options.

    sorter_options : a dictionary with sorter name (key) and
                     a dictionary of kwargs to pass to the
                     spikeinterface sorter class.
    """
    config_dir = Path(os.path.dirname(os.path.realpath(__file__)))

    with open(config_dir / f"{name}.yaml") as file:
        config = yaml.full_load(file)

    pp_steps = config["preprocessing"]
    sorter_options = config["sorting"]

    for key in pp_steps.keys():
        pp_steps[key] = tuple(pp_steps[key])

    return pp_steps, sorter_options
