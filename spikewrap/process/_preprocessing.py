from __future__ import annotations

from typing import Callable

import numpy as np
import spikeinterface.full as si

from spikewrap.utils import _utils


def _fill_with_preprocessed_recordings(
    preprocess_data: dict[str, list],
    pp_steps: dict,
) -> None:
    """
    Fill the Preprocessed._data dict with preprocessed
    SpikeInterface recording objects according to pp_steps.

    For each preprocessing step, the key will be a concatenation
    of all preprocessing steps that were performed.
    e.g. "0-raw", "0-raw_1-phase_shift_2-bandpass_filter"

    Parameters
    ----------
    preprocess_data
        Dictionary to store the newly created recording objects, updated in-place.
    pp_steps
        "preprocessing" entry of a "configs" dictionary. Formatted as
        {step_num_str : [preprocessing_func_name, {pp_func_args}]
    """
    pp_funcs = _get_pp_funcs()

    checked_pp_steps, pp_step_names = _check_and_sort_pp_steps(pp_steps, pp_funcs)

    for step_num, pp_info in checked_pp_steps.items():
        pp_name, pp_options = pp_info

        last_pp_step_output, __ = _utils._get_dict_value_from_step_num(
            preprocess_data, step_num=str(int(step_num) - 1)
        )

        preprocessed_recording = pp_funcs[pp_name](last_pp_step_output, **pp_options)

        new_name = f"{step_num}-" + "-".join(["raw"] + pp_step_names[: int(step_num)])

        preprocess_data[new_name] = preprocessed_recording


# Helpers for preprocessing steps dictionary -------------------------------------------


def _check_and_sort_pp_steps(pp_steps: dict, pp_funcs: dict) -> tuple[dict, list[str]]:
    """
    Sort the preprocessing steps dictionary by order to be run
    (based on the keys) and check the dictionary is valid.

    Parameters
    ----------
    pp_steps dict
        "preprocessing" entry of a "configs" dictionary. Formatted as
        {step_num_str : [preprocessing_func_name, {pp_func_args}]
    pp_funcs
        A dictionary linking preprocessing step names to the underlying
        SpikeInterface preprocessing functions.

    Returns
    -------
    pp_steps
        The checked pp_steps dictionary.
    pp_step_names
        List of ordered preprocessing step names (e.g. "bandpass_filter").
    """
    _validate_pp_steps(pp_steps)
    pp_step_names = [item[0] for item in pp_steps.values()]

    # Check the preprocessing function names are valid and print steps used
    canonical_step_names = list(pp_funcs.keys())

    for user_passed_name in pp_step_names:
        assert (
            user_passed_name in canonical_step_names
        ), f"{user_passed_name} not in allowed names: ({canonical_step_names}"

    return pp_steps, pp_step_names


def _validate_pp_steps(pp_steps: dict) -> None:
    """
    Ensure the pp_steps dict step numbers start 1 at,
    and increase by 1 for each subsequent step.

    Parameters
    ----------
    pp_steps
        "preprocessing" entry of a "configs" dictionary. Formatted as
        {step_num_str : [preprocessing_func_name, {pp_func_args}]
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


def _get_pp_funcs() -> dict[str, Callable]:
    """
    Returns a dict mapping SpikeInterface preprocessing
    function name to the function object.
    """
    pp_funcs = {
        "phase_shift": si.phase_shift,
        "bandpass_filter": si.bandpass_filter,
        "common_reference": si.common_reference,
    }

    return pp_funcs
