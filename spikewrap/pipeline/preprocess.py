import json
from typing import Dict, List, Tuple, Union

import numpy as np
import spikeinterface.preprocessing as spre

from ..configs import configs
from ..data_classes.preprocessing import PreprocessingData
from ..utils import logging_sw, slurm, utils, validate
from ..utils.custom_types import HandleExisting

# --------------------------------------------------------------------------------------
# Public Functions
# --------------------------------------------------------------------------------------


def run_preprocessing(
    preprocess_data: PreprocessingData,
    pp_steps: str,
    handle_existing_data: HandleExisting,
    slurm_batch: Union[bool, Dict] = False,
    log: bool = True,
):
    """
    Main entry function to run preprocessing and write to file. Preprocessed
    lazy spikeinterface recordings will be added to all sessions / runs in
    `preprocess_data` and written to file.

    Parameters
    ----------

    preprocess_data : PreprocessingData
        A preprocessing data object that has as attributes the
        paths to rawdata. The pp_steps attribute is set on
        this class during execution of this function.

    pp_steps: The name of valid preprocessing .yaml file (without the yaml extension).
              stored in spikewrap/configs.

    existing_preprocessed_data : custom_types.HandleExisting
        Determines how existing preprocessed data (e.g. from a prior pipeline run)
        is handled.
            "overwrite" : Will overwrite any existing preprocessed data output.
                          This will delete the 'preprocessed' folder. Therefore,
                          never save derivative work there.
            "skip_if_exists" : will search for existing data and skip preprocesing
                               if it exists (sorting will run on existing
                               preprocessed data).
                               Otherwise, will preprocess and save the current run.
            "fail_if_exists" : If existing preprocessed data is found, an error
                               will be raised.

    slurm_batch : Union[bool, Dict]
        see `run_full_pipeline()` for details.
    """
    # TOOD: refactor and handle argument groups separately.
    # Avoid duplication with logging.
    passed_arguments = locals()
    validate.check_function_arguments(passed_arguments)

    pp_steps_dict, _, _ = configs.get_configs(pp_steps)  # TODO: call 'config_name'

    if slurm_batch:
        slurm.run_in_slurm(
            slurm_batch,
            _preprocess_and_save_all_runs,
            {
                "preprocess_data": preprocess_data,
                "pp_steps": pp_steps_dict,
                "handle_existing_data": handle_existing_data,
                "log": log,
            },
        ),
    else:
        _preprocess_and_save_all_runs(
            preprocess_data, pp_steps_dict, handle_existing_data, log
        )


def fill_all_runs_with_preprocessed_recording(
    preprocess_data: PreprocessingData, pp_steps: str
) -> None:
    """
    Convenience function to fill all session and run entries in the
    `preprocess_data` dictionary with preprocessed spikeinterface
    recording objects.

    preprocess_data : PreprocessingData
        A preprocessing data object that has as attributes the
        paths to rawdata. The pp_steps attribute is set on
        this class during execution of this function.

    pp_steps: The name of valid preprocessing .yaml file (without the yaml extension).
              stored in spikewrap/configs.
    """
    pp_steps_dict, _, _ = configs.get_configs(pp_steps)

    for ses_name, run_name in preprocess_data.flat_sessions_and_runs():
        _fill_run_data_with_preprocessed_recording(
            preprocess_data, ses_name, run_name, pp_steps_dict
        )


# --------------------------------------------------------------------------------------
# Private Functions
# --------------------------------------------------------------------------------------


def _preprocess_and_save_all_runs(
    preprocess_data: PreprocessingData,
    pp_steps_dict: Dict,
    handle_existing_data: HandleExisting,
    log: bool = True,
) -> None:
    """
    Handle the loading of existing preprocessed data.
    See `run_preprocessing()` for details.

    This function validates all input arguments and initialises logging.
    Then, it will iterate over every run in `preprocess_data` and
    check whether preprocessing needs to be run and saved based on the
    `handle_existing_data` option. If so, it will fill the relevant run
    with the preprocessed spikeinterface recording object and save to disk.
    """
    passed_arguments = locals()
    validate.check_function_arguments(passed_arguments)

    if log:
        logs = logging_sw.get_started_logger(
            utils.get_logging_path(preprocess_data.base_path, preprocess_data.sub_name),
            "preprocessing",
        )
        utils.show_passed_arguments(passed_arguments, "`run_preprocessing`")

    for ses_name, run_name in preprocess_data.flat_sessions_and_runs():
        utils.message_user(f"Preprocessing run {run_name}...")

        to_save, overwrite = _handle_existing_data_options(
            preprocess_data, ses_name, run_name, handle_existing_data
        )

        if to_save:
            _preprocess_and_save_single_run(
                preprocess_data, ses_name, run_name, pp_steps_dict, overwrite
            )

    if log:
        logs.stop_logging()


def _preprocess_and_save_single_run(
    preprocess_data: PreprocessingData,
    ses_name: str,
    run_name: str,
    pp_steps_dict: Dict,
    overwrite: bool,
) -> None:
    """
    Given a single session and run, fill the entry for this run
    on the `preprocess_data` object and write to disk.
    """
    _fill_run_data_with_preprocessed_recording(
        preprocess_data,
        ses_name,
        run_name,
        pp_steps_dict,
    )

    preprocess_data.save_preprocessed_data(ses_name, run_name, overwrite)


def _handle_existing_data_options(
    preprocess_data: PreprocessingData,
    ses_name: str,
    run_name: str,
    handle_existing_data: HandleExisting,
) -> Tuple[bool, bool]:
    """
    Determine whether preprocesing for this run needs to be performed based
    on the `handle_existing_data setting`. If preprocessing does not exist, preprocessing
    is always run. Otherwise, if it already exists, the behaviour depends on
    the `handle_existing_data` setting.

    Returns
    -------

    to_save : bool
        Whether the preprocessing needs to be run and saved.

    to_overwrite : bool
        If saving, set the `overwrite` flag to confirm existing data should
        be overwritten.
    """
    preprocess_path = preprocess_data.get_preprocessing_path(ses_name, run_name)

    if handle_existing_data == "skip_if_exists":
        if preprocess_path.is_dir():
            utils.message_user(
                f"\nSkipping preprocessing, using file at "
                f"{preprocess_path} for sorting.\n"
            )
            to_save = False
            overwrite = False
        else:
            utils.message_user(
                f"No data found at {preprocess_path}, saving preprocessed data."
            )
            to_save = True
            overwrite = False

    elif handle_existing_data == "overwrite":
        if preprocess_path.is_dir():
            utils.message_user(f"Removing existing file at {preprocess_path}\n")

        utils.message_user(f"Saving preprocessed data to {preprocess_path}")
        to_save = True
        overwrite = True

    elif handle_existing_data == "fail_if_exists":
        if preprocess_path.is_dir():
            raise FileExistsError(
                f"Preprocessed binary already exists at "
                f"{preprocess_path}. "
                f"To overwrite, set 'existing_preprocessed_data' to 'overwrite'"
            )
        to_save = True
        overwrite = False

    return to_save, overwrite


def _fill_run_data_with_preprocessed_recording(
    preprocess_data: PreprocessingData,
    ses_name: str,
    run_name: str,
    pp_steps: Dict,
) -> None:
    """
    For a particular run, fill the `preprocess_data` object entry with preprocessed
    spikeinterface recording objects. For each preprocessing step, a separate
    recording object will be stored. The name of the dict entry will be
    a concatenenation of all preprocessing steps that were performed.

    e.g. "0-raw", "0-raw_1-phase_shift_2-bandpass_filter"
    """
    pp_funcs = _get_pp_funcs()

    checked_pp_steps, pp_step_names = _check_and_sort_pp_steps(pp_steps, pp_funcs)

    preprocess_data.set_pp_steps(pp_steps)

    for step_num, pp_info in checked_pp_steps.items():
        _perform_preprocessing_step(
            step_num,
            pp_info,
            preprocess_data,
            ses_name,
            run_name,
            pp_step_names,
            pp_funcs,
        )


def _perform_preprocessing_step(
    step_num: str,
    pp_info: Tuple[str, Dict],
    preprocess_data: PreprocessingData,
    ses_name: str,
    run_name: str,
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
    pp_name, pp_options = pp_info

    utils.message_user(
        f"Running preprocessing step: {pp_name} with options {pp_options}"
    )

    last_pp_step_output, __ = utils.get_dict_value_from_step_num(
        preprocess_data[ses_name][run_name], step_num=str(int(step_num) - 1)
    )

    new_name = f"{step_num}-" + "-".join(["raw"] + pp_step_names[: int(step_num)])

    _confidence_check_pp_func_name(pp_name, pp_funcs)

    preprocess_data[ses_name][run_name][new_name] = pp_funcs[pp_name](
        last_pp_step_output, **pp_options
    )


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

    utils.message_user(
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

    TODO
    -----
    It should be possible to generate this on the fly from
    SI __init__ rather than hard code like this
    """
    pp_funcs = {
        "phase_shift": spre.phase_shift,
        "bandpass_filter": spre.bandpass_filter,
        "common_reference": spre.common_reference,
        "blank_saturation": spre.blank_staturation,
        "center": spre.center,
        "clip": spre.clip,
        "correct_lsb": spre.correct_lsb,
        "correct_motion": spre.correct_motion,
        "depth_order": spre.depth_order,
        "filter": spre.filter,
        "gaussian_bandpass_filter": spre.gaussian_bandpass_filter,
        "highpass_filter": spre.highpass_filter,
        "interpolate_bad_channels": spre.interpolate_bad_channels,
        "normalize_by_quantile": spre.normalize_by_quantile,
        "notch_filter": spre.notch_filter,
        "remove_artifacts": spre.remove_artifacts,
        # "remove_channels": remove_channels, not sure how to handle at runtime
        #        "resample": spre.resample,  leading to linAlg error
        "scale": spre.scale,
        "silence_periods": spre.silence_periods,
        "whiten": spre.whiten,
        "zscore": spre.zscore,
    }

    return pp_funcs
