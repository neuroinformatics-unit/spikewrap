import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import spikeinterface.preprocessing as spre

from ..configs import configs
from ..utils import utils
from .data_class import Data

def preprocess(
    data: Data,
    pp_steps: Optional[Dict] = None,
    verbose: bool = True,
) -> Data:
    """
    Returns a dictionary of spikeinterface recording objects setup in
    the order and with the options specified in pp_steps. Spikeinterface
    preprocessing is lazy - no preprocessing is done until the data is written
    to file or the get_traces() method on the recording object is called.

    Parameters
    ----------

    base_path: path containing the "rawdata" folder, that contains
               subject-level folders.

    sub_name: subject name (i.e. name of the folder in rawdata) to run

    run_name: spikeglx run name (not including the gate index). Currently only
              single gate / trigger recordings are supported (e.g. g0 and t0 only).

    pp_steps: pp_steps dictionary, see configs/configs.py for details.

    Returns
    -------

    data : swc_ephys Data UserDict containing preprocessing spikeinterface
           recording objects. see pipeline.data_class

    """
    if not pp_steps:
        pp_steps, __ = configs.get_configs("test")

    pp_funcs = get_pp_funcs()

    checked_pp_steps, pp_step_names = check_and_sort_pp_steps(pp_steps, pp_funcs)

    data.pp_steps = pp_steps  # TODO: handle this logic flow properly. Can use a setter but
                              # probably makes more sense to think about this data class more
                              # - does it need splitting, - should pp steps be held on it??

    data.set_preprocessing_output_path()

    for step_num, pp_info in checked_pp_steps.items():
        perform_preprocessing_step(step_num, pp_info, data, pp_step_names, pp_funcs, verbose)

    handle_bad_channels(data)

    return data


def handle_bad_channels(data: Data):
    """
    Placeholder function to begin handling bad channel detection. Even if not
    requested, it will always be useful to highlight the bad channels.

    However, it is not clear whether to print these / log these / provide simple
    API argument to remove bad channels.

    TODO
    ----
    Need to determine when best to run this detection. Definately after
    filtering, need to ask on Slack
    see https://spikeinterface.readthedocs.io/en/latest/api.html
    https://github.com/int-brain-lab/ibl-neuropixel/blob/d913ede52117bc79d \
    e77f8dc9cdb407807ab8a8c/src/neurodsp/voltage.py#L445
    """
    bad_channels = spre.detect_bad_channels(data["0-raw"])

    utils.message_user(
        f"\nThe following channels were detected as dead / noise: {bad_channels[0]}\n"
        f"TODO: DO SOMETHING BETTER WITH THIS INFORMATION. SAVE IT SOMEHWERE\n"
        f"You may like to automatically remove bad channels "
        f"by setting [TO IMPLEMENT]] as a preprocessing option\n"
        f"TODO: check how this is handled in SI\n"
    )


def check_and_sort_pp_steps(pp_steps: Dict, pp_funcs: Dict) -> Tuple[Dict, List[str]]:
    """
    Sort the preprocessing steps dictionary by order to be run (based on the
    keys) and check the dictionary is valid.

    Parameters
    ----------

    pp_steps : a dictionary with keys as numbers indicating the order that
               preprocessing steps are run (starting at "1"). The values are a
               (preprocessing name, preprocessing kwargs) tuple containing the
               spikeinterface preprocessing function name, and kwargs to pass to it.

    Returns
    -------

    sorted_pp_steps : a sorted and checked preprocessing steps dictionary.

    pp_step_names : list of preprocessing step names (e.g. "bandpass_filter"] in order
                    that they are to be run.

    Notes
    -------

    This will soon be deprecated and replaced by validation
    of the config file itself on load.
    """
    sorted_pp_steps = {k: pp_steps[k] for k in sorted(pp_steps.keys())}
    pp_step_names = [item[0] for item in sorted_pp_steps.values()]

    # Check keys are numbers starting at 1 increasing by 1
    assert all(
        key.isdigit() for key in sorted_pp_steps.keys()
    ), "pp_steps keys must be integers"

    key_nums = [int(key) for key in sorted_pp_steps.keys()]

    assert np.min(key_nums) == 1, "dict keys must start at 1"

    diffs = np.diff(key_nums)
    assert np.unique(diffs).size == 1, "all dict keys must increase in steps of 1"
    assert diffs[0] == 1, "all dict keys must increase in steps of 1"

    # Check the preprocessing function names are valid
    canonical_step_names = list(pp_funcs.keys())

    for user_passed_name in pp_step_names:
        assert (
            user_passed_name in canonical_step_names
        ), f"{user_passed_name} not in allowed names: ({canonical_step_names}"

    # Print the preprocessing dict used
    utils.message_user(
        f"\nThe preprocessing options dictionary is "
        f"{json.dumps(sorted_pp_steps, indent=4, sort_keys=True)}"
    )

    return sorted_pp_steps, pp_step_names


def perform_preprocessing_step(
    step_num: str,
    pp_info: Tuple[str, Dict],
    data: Data,
    pp_step_names: List,
    pp_funcs: Dict,
    verbose: bool = True,
):
    """
    Given the preprocessing step and data UserDict containing
    spikeinterface BaseRecordings, apply a preprocessing step to the
    last preprocessed recording and save the recording object to Data.
    For example, if step_num = "3", get the recording of the second
    preprocessing step from data and apply the 3rd preprocessing step
    as specified in pp_info.

    Parameters
    ----------
    step_num : preprocessing step to run (e.g. "1", corresponds to the
              key in pp_dict).

    pp_info : (preprocessing name, preprocessing kwargs) tuple (they value from
              the pp_dict).

    data : swc_ephys Data class (a UserDict in which key-values are
           the preprocessing chain name : spikeinterface recording objects).

    pp_step_names : ordered list of preprocessing step names that are being
                    applied across the entire preprocessing chain.

    """
    pp_name, pp_options = pp_info

    utils.message_user(f"Running preprocessing step: {pp_name} with options {pp_options}", verbose)

    last_pp_step_output, __ = utils.get_dict_value_from_step_num(
        data, step_num=str(int(step_num) - 1)
    )

    new_name = f"{step_num}-" + "-".join(["raw"] + pp_step_names[: int(step_num)])

    assert pp_funcs[pp_name].__name__ == pp_name, "something is wrong in func dict"

    data[new_name] = pp_funcs[pp_name](last_pp_step_output, **pp_options)
    data.opts[new_name] = pp_options


def get_pp_funcs() -> Dict:
    """
    Get the spikeinterface preprocessing function
    from its name. TODO: it should be possible to
    generate this on the fly from SI __init__ rather
    than hard code like this
    """
    pp_funcs = {
        "phase_shift": spre.phase_shift,
        "bandpass_filter": spre.bandpass_filter,
        "common_reference": spre.common_reference,
    }

    return pp_funcs
