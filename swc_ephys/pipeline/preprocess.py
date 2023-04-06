import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import spikeinterface.extractors as se
import spikeinterface.preprocessing as spre

from ..utils import utils
from .data_class import Data

pp_funcs = {
    "phase_shift": spre.phase_shift,
    "bandpass_filter": spre.bandpass_filter,
    "common_reference": spre.common_reference,
}


def preprocess(
    base_path: Union[Path, str], sub_name: str, run_name: str, pp_steps: Optional[Dict]
) -> Data:
    """ """
    if not pp_steps:
        pp_steps = {
            "1": ("phase_shift", {}),  # TODO: move
            "2": ("bandpass_filter", {"freq_min": 300, "freq_max": 6000}),
            "3": ("common_reference", {"operator": "median", "reference": "global"}),
        }

    checked_pp_steps, pp_step_names = check_and_sort_pp_steps(pp_steps)

    data = Data(base_path, sub_name, run_name, pp_steps)

    data.run_level_path = data.rawdata_path / sub_name / (run_name + "_g0")
    data.set_preprocessing_output_path()

    data["0-raw"] = se.read_spikeglx(
        folder_path=data.run_level_path, stream_id="imec0.ap", all_annotations=True
    )

    for step_num, pp_info in checked_pp_steps.items():
        perform_preprocessing_step(step_num, pp_info, data, pp_step_names)

    handle_bad_channels(data)

    return data


def handle_bad_channels(data: Data):
    """ """
    bad_channels = spre.detect_bad_channels(data["0-raw"])

    utils.message_user(
        f"The following channels were detected as dead / noise: {bad_channels[0]}\n"
        f"TODO: DO SOMETHING BETTER WITH THIS INFORMATION. SAVE IT SOMEHWERE\n"
        f"You may like to automatically remove bad channels "
        f"by setting XXX as a preprocessing option\n"
        f"TODO: check how this is handled in SI"
    )


def perform_preprocessing_step(
    step_num: str, pp_info: Tuple[str, Dict], data: Data, pp_step_names: List
):
    """ """
    pp_name, pp_options = pp_info

    last_pp_step_output, __ = utils.get_dict_value_from_step_num(
        data, step_num=str(int(step_num) - 1)
    )  # TODO: check annotation at this point

    new_name = f"{step_num}-" + "-".join(["raw"] + pp_step_names[: int(step_num)])

    assert pp_funcs[pp_name].__name__ == pp_name, "something is wrong in func dict"

    data[new_name] = pp_funcs[pp_name](last_pp_step_output, **pp_options)
    data.opts[new_name] = pp_options


def check_and_sort_pp_steps(pp_steps: Dict) -> Tuple[Dict, List[str]]:
    """
    TODO: TEST THOROUGHLY!
    """
    sorted_pp_steps = {k: pp_steps[k] for k in sorted(pp_steps.keys())}

    # check keys
    assert all(
        key.isdigit() for key in sorted_pp_steps.keys()
    ), "pp_steps keys must be integers"

    key_nums = [int(key) for key in sorted_pp_steps.keys()]

    assert np.min(key_nums) == 1, "dict keys must start at 1"

    diffs = np.diff(key_nums)
    assert np.unique(diffs).size == 1, "all dict keys must increase in steps of 1"
    assert diffs[0] == 1, "all dict keys must increase in steps of 1"

    # key names
    pp_step_names = [item[0] for item in sorted_pp_steps.values()]
    canonical_step_names = list(pp_funcs.keys())

    for user_passed_name in pp_step_names:
        assert (
            user_passed_name in canonical_step_names
        ), f"{user_passed_name} not in allowed names: ({canonical_step_names}"

    # check options... or better (?), validate a config file.

    utils.message_user(
        f"\nThe preprocessing options dictionary is "
        f"{json.dumps(sorted_pp_steps, indent=4, sort_keys=True)}"
    )

    return sorted_pp_steps, pp_step_names
