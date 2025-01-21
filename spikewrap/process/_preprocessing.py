from __future__ import annotations

import spikeinterface.full as si
import numpy as np
import json

from spikewrap.utils import _utils
from spikewrap.configs._backend import canon


def fill_with_preprocessed_recordings(
    preprocess_data,  # TYPE
    pp_steps: Dict,
) -> None:
    """
    For a particular run, fill the `preprocess_data` object entry with preprocessed
    spikeinterface recording objects. For each preprocessing step, a separate
    recording object will be stored. The name of the dict entry will be
    a concatenation of all preprocessing steps that were performed.

    e.g. "0-raw", "0-raw_1-phase_shift_2-bandpass_filter"
    """
    pp_funcs = _get_pp_funcs()

    checked_pp_steps, pp_step_names = _check_and_sort_pp_steps(
        pp_steps, pp_funcs
    )

    for step_num, pp_info in checked_pp_steps.items():
        _perform_preprocessing_step(  # TODO: can this cut down and tidied..?
            step_num,
            pp_info,
            preprocess_data,
            pp_step_names,
            pp_funcs,
        )

def _perform_preprocessing_step(
    step_num: str,
    pp_info: Tuple[str, Dict],
    preprocess_data: PreprocessingData,
    pp_step_names: List[str],
    pp_funcs: Dict,
) -> None:
    """
    Given the preprocessing step and preprocess_data UserDict containing
    spikeinterface BaseRecordings, apply a preprocessing step to the
    last preprocessed recording and save the recording object to PreprocessingData.
    For example, if step_num = "3", get the recording of the second
    preprocessing step from preprocess_data and apply the 3rd preprocessing step
    as specified in pp_info.

    Parameters
    ----------
    step_num : str
        Preprocessing step to run (e.g. "1", corresponds to the key in pp_dict).

    pp_info : Tuple[str, Dict]
        Preprocessing name, preprocessing kwargs) tuple (the value from
        the pp_dict).

    preprocess_data : PreprocessingData
        spikewrap PreprocessingData class (a UserDict in which key-values are
        the preprocessing chain name : spikeinterface recording objects).

    run_name: str
        Name of the run to preprocess. This should correspond to a
        run_name in `preprocess_data.preprocessing_run_names`.

    pp_step_names : List[str]
        Ordered list of preprocessing step names that are being
        applied across the entire preprocessing chain.

    pp_funcs : Dict
        The canonical SpikeInterface preprocessing functions. The key
        are the function name and value the function object.
    """
    # last pp step outpiut is not used by above and should be split out.
    (
        pp_name,
        pp_options,
        last_pp_step_output,
        new_name,
    ) = _get_preprocessing_step_information(
        pp_info, pp_step_names, preprocess_data, step_num
    )

    _confidence_check_pp_func_name(pp_name, pp_funcs)

    preprocessed_recording = pp_funcs[pp_name](
        last_pp_step_output, **pp_options
    )

    preprocess_data[new_name] = preprocessed_recording


def _get_preprocessing_step_information(
    pp_info, pp_step_names, preprocess_data, step_num
):
    """"""
    pp_name, pp_options = pp_info

    _utils.message_user(
        f"Running preprocessing step: {pp_name} with options {pp_options}"
    )

    last_pp_step_output, __ = _utils.get_dict_value_from_step_num(
        preprocess_data, step_num=str(int(step_num) - 1)
    )

    new_name = f"{step_num}-" + "-".join(["raw"] + pp_step_names[: int(step_num)])

    return pp_name, pp_options, last_pp_step_output, new_name


# Helpers for preprocessing steps dictionary -------------------------------------------

def _check_and_sort_pp_steps(pp_steps: Dict, pp_funcs: Dict) -> Tuple[Dict, List[str]]:
    """
    Sort the preprocessing steps dictionary by order to be run (based on the
    keys) and check the dictionary is valid.

    Parameters
    ----------
    pp_steps : Dict
        A dictionary with keys as numbers indicating the order that
        preprocessing steps are run (starting at "1"). The values are a
        (preprocessing name, preprocessing kwargs) tuple containing the
        spikeinterface preprocessing function name, and kwargs to pass to it.

    pp_funcs : Dict
        A dictionary linking preprocessing step names to the underlying
        SpikeInterface function objects that conduct the preprocessing.

    Returns
    -------
    pp_steps :Dict
        The checked preprocessing steps dictionary.

    pp_step_names : List
        Preprocessing step names (e.g. "bandpass_filter") in order
        that they are to be run.
    """
    _validate_pp_steps(pp_steps)
    pp_step_names = [item[0] for item in pp_steps.values()]

    # Check the preprocessing function names are valid and print steps used
    canonical_step_names = list(pp_funcs.keys())

    for user_passed_name in pp_step_names:
        assert (
            user_passed_name in canonical_step_names
        ), f"{user_passed_name} not in allowed names: ({canonical_step_names}"

    _utils.message_user(
        f"\nThe preprocessing options dictionary is "
        f"{json.dumps(pp_steps, indent=4, sort_keys=True)}"
    )

    return pp_steps, pp_step_names


def _validate_pp_steps(pp_steps: Dict):
    """
    Ensure the pp_steps dictionary of preprocessing steps
    has number-order that makes sense. The preprocessing step numbers
    should start 1 at, and increase by 1 for each subsequent step.
    """
    assert all(
        key.isdigit() for key in pp_steps.keys()
    ), "pp_steps keys must be integers"

    key_nums = [int(key) for key in pp_steps.keys()]

    assert np.min(key_nums) == 1, "dict keys must start at 1"

    if len(key_nums) > 1:
        diffs = np.diff(key_nums)
        assert np.unique(diffs).size == 1, "all dict keys must increase in steps of 1"
        assert diffs[0] == 1, "all dict keys must increase in steps of 1"


def _confidence_check_pp_func_name(pp_name: str, pp_funcs: Dict):
    """
    Ensure that the correct preprocessing function is retrieved. This
    essentially checks the _get_pp_funcs dictionary is correct.

    TODO
    ----
    This should be a standalone test, not incorporated into the package.
    """
    func_name_to_class_name = "".join([word.lower() for word in pp_name.split("_")])

    if pp_name == "silence_periods":
        assert pp_funcs[pp_name].__name__ == "SilencedPeriodsRecording"  # TODO: open PR
    elif isinstance(pp_funcs[pp_name], type):
        assert (
            func_name_to_class_name in pp_funcs[pp_name].__name__.lower()
        ), "something is wrong in func dict"

    else:
        assert pp_funcs[pp_name].__name__ == pp_name


def _get_pp_funcs() -> Dict:
    """
    Get the spikeinterface preprocessing function
    from its name.

    Add iteratively as required / tested.
    """
    pp_funcs = {
        "phase_shift": si.phase_shift,
        "bandpass_filter": si.bandpass_filter,
        "common_reference": si.common_reference,
    }

    return pp_funcs