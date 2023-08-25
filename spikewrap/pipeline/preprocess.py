import json
from typing import Dict, List, Literal, Tuple, Union

import numpy as np
import spikeinterface.preprocessing as spre

from ..configs import configs
from ..data_classes.preprocessing import PreprocessingData
from ..utils import logging_sw, slurm, utils
from ..utils.custom_types import HandleExisting


def run_preprocess(
    preprocess_data: PreprocessingData,
    pp_steps,
    save_to_file: Union[Literal[False], HandleExisting],
    slurm_batch: bool = False,
    log: bool = True,
) -> None:
    """

    SLURM:  # TODO: save_to_file must be TRUE

    Handle the loading of existing preprocessed data.
    See `run_full_pipeline()` for details.
    """
    passed_arguments = locals()

    if slurm_batch:
        assert save_to_file is not False, "`save_to_file` cannot be `False` if running in SLURM"  # TODO: validation!
        slurm.run_preprocessing_slurm(**passed_arguments)
        return None, None
    assert slurm_batch is False, "SLURM run has slurm_batch set True"

    if log:
        logs = logging_sw.get_started_logger(
            utils.get_logging_path(preprocess_data.base_path, preprocess_data.sub_name),
            "preprocessing",
        )
        utils.show_passed_arguments(passed_arguments, "`run_preprocessing`")

    for ses_name, run_name in preprocess_data.preprocessing_sessions_and_runs():
        utils.message_user(f"Preprocessing run {run_name}...")

        preprocess_path = preprocess_data.get_preprocessing_path(ses_name, run_name)

        if save_to_file is False:
            preprocess_data = preprocess(preprocess_data, ses_name, run_name, pp_steps)
        else:
            if save_to_file == "skip_if_exists":
                if preprocess_path.is_dir():
                    utils.message_user(
                        f"\nSkipping preprocessing, using file at "
                        f"{preprocess_path} for sorting.\n"
                    )
                    continue  # sorting will automatically use the existing data
                else:
                    utils.message_user(
                        f"No data found at {preprocess_path}, saving preprocessed data."
                    )
                    overwrite = False

            elif save_to_file == "overwrite":
                if preprocess_path.is_dir():
                    utils.message_user(f"Removing existing file at {preprocess_path}\n")

                utils.message_user(f"Saving preprocessed data to {preprocess_path}")
                overwrite = True

            elif save_to_file == "fail_if_exists":
                if preprocess_path.is_dir():
                    raise FileExistsError(
                        f"Preprocessed binary already exists at "
                        f"{preprocess_path}. "
                        f"To overwrite, set 'existing_preprocessed_data' to 'overwrite'"
                    )
                overwrite = False

            #          else:
            #             raise ValueError(  # TODO: use assert not and end here (Validate Inputs)
            #                "`existing_prepreprocessed_data` argument not recognised."
            #               "Must be: 'skip_if_exists', 'fail_if_exists' or 'overwrite'."
            #          )
            preprocess_data = preprocess(preprocess_data, ses_name, run_name, pp_steps)

            preprocess_data.save_preprocessed_data(ses_name, run_name, overwrite)

    if log:
        logs.stop_logging()


def preprocess(
    preprocess_data: PreprocessingData,
    ses_name: str,
    run_name: str,
    pp_steps: Union[Dict, str],
) -> PreprocessingData:
    """
    Returns an updated PreprocessingData dictionary of SpikeInterface
    recording objects setup in the order and with the options specified
    in pp_steps.

    Spikeinterface preprocessing is lazy - no preprocessing is done
    until the data is written to file or the get_traces() method on
    the recording object is called.

    Parameters
    ----------
    preprocess_data : PreprocessingData
        A preprocessing data object that has as attributes the
        paths to rawdata. The pp_steps attribute is set on
        this class during execution of this function.

    run_name: str
        Name of the run to preprocess. This should correspond to a
        run_name in `preprocess_data.preprocessing_run_names`.

    pp_steps: either a pp_steps dictionary, or name of valid
              preprocessing .yaml file (without hte yaml extension).
              See configs/configs.py for details.

    Returns
    -------
    preprocess_data : PreprocessingData
        Preprocessing data class with pp_steps updated and
        dictionary field filled with key-value pairs indicating
        the name and order of preprocessing keys, and value containing
        associated SpikeInterface recording objects.

    """
    if isinstance(pp_steps, str):
        pp_steps_to_run, _, _ = configs.get_configs(pp_steps)
    else:
        pp_steps_to_run = pp_steps

    pp_funcs = get_pp_funcs()

    checked_pp_steps, pp_step_names = check_and_sort_pp_steps(pp_steps_to_run, pp_funcs)

    preprocess_data.set_pp_steps(pp_steps_to_run)

    for step_num, pp_info in checked_pp_steps.items():
        perform_preprocessing_step(
            step_num,
            pp_info,
            preprocess_data,
            ses_name,
            run_name,
            pp_step_names,
            pp_funcs,
        )

    return preprocess_data


def check_and_sort_pp_steps(pp_steps: Dict, pp_funcs: Dict) -> Tuple[Dict, List[str]]:
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

    Notes
    -------
    This will soon be deprecated and replaced by validation
    of the config file itself on load.
    """
    validate_pp_steps(pp_steps)
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


def validate_pp_steps(pp_steps: Dict):
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


def perform_preprocessing_step(
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

    confidence_check_pp_func_name(pp_name, pp_funcs)

    #    if isinstance(last_pp_step_output, Dict):
    #        preprocess_data[ses_name][run_name][new_name] = {
    #            k: pp_funcs[pp_name](v, **pp_options)
    #            for k, v in last_pp_step_output.items()
    #        }
    #    else:
    preprocess_data[ses_name][run_name][new_name] = pp_funcs[pp_name](
        last_pp_step_output, **pp_options
    )


def confidence_check_pp_func_name(pp_name, pp_funcs):
    """
    Ensure that the correct preprocessing function is retrieved. This
    essentially checks the get_pp_funcs dictionary is correct.

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


def remove_channels(recording, bad_channel_ids):
    return recording.remove_channels(bad_channel_ids)


def get_pp_funcs() -> Dict:
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
        "remove_channels": remove_channels,
        #        "resample": spre.resample,  leading to linAlg error
        "scale": spre.scale,
        "silence_periods": spre.silence_periods,
        "whiten": spre.whiten,
        "zscore": spre.zscore,
    }

    return pp_funcs
