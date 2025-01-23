from __future__ import annotations

import os
import psutil
import numpy as np

from slurmio import SlurmJobParameters
import copy
import json


def message_user(message: str) -> None:
    """
    Method to interact with user.

    Parameters
    ----------
    message : str
        Message to print.
    """
    print(f"\n{message}")


def get_dict_value_from_step_num(
        data: Union[PreprocessingData, SortingData], step_num: str
) -> Tuple[BaseRecording, str]:
    """
    Get the value of the PreprocessingData dict from the preprocessing step number.

    PreprocessingData contain keys indicating the preprocessing steps,
    starting with the preprocessing step number.
    e.g. 0-raw, 1-raw-bandpass_filter, 2-raw_bandpass_filter-common_average

    Return the value of the dict (spikeinterface recording object)
    from the dict using only the step number.

    Parameters
    ----------
    data : Union[PreprocessingData, SortingData]
        spikewrap PreprocessingData class holding filepath information.

    step_num : str
        The preprocessing step number to get the value (i.e. recording object)
        from.

    Returns
    -------
    dict_value : BaseRecording
        The SpikeInterface recording stored in the dict at the
        given preprocessing step number.

    pp_key : str
        The key of the preprocessing dict at the given
        step number.
    """
    if step_num == "last":
        pp_key_nums = get_keys_first_char(data, as_int=True)

        # Complete overkill as a check but this is critical.
        step_num = str(int(np.max(pp_key_nums)))
        assert (
                int(step_num) == len(data.keys()) - 1
        ), "the last key has been taken incorrectly"

    select_step_pp_key = [key for key in data.keys() if
                          key.split("-")[0] == step_num]

    assert len(select_step_pp_key) == 1, "pp_key must always have unique first char"

    pp_key: str = select_step_pp_key[0]
    dict_value = data[pp_key]

    return dict_value, pp_key


def get_keys_first_char(
    data: Union[PreprocessingData, SortingData], as_int: bool = False
) -> Union[List[str], List[int]]:
    """
    Get the first character of all keys in a dictionary. Expected
    that the first characters are integers (as str type).

    Parameters
    ----------
    data : Union[PreprocessingData, SortingData]
        spikewrap PreprocessingData class holding filepath information.

    as_int : bool
        If True, the first character of the keys are cast to
        integer type.

    Returns
    -------
    list_of_numbers : Union[List[str], List[int]]
        A list of numbers of string or integer type, that are
        the first numbers of the Preprocessing / Sorting Data
        .data dictionary keys.
    """
    list_of_numbers = [
        int(key.split("-")[0]) if as_int else key.split("-")[0] for key in data.keys()
    ]
    return list_of_numbers


def get_default_chunk_size(recording, sync: bool = False):
    """
    Get chunk size that uses ~80% of available memory.
    Larger chunk size is better
    because it reduces filter edge effect and (I guess)
    will be faster.

    The calculation for memory use is:
    mem_use_bytes = max_itemsize * num_channels * * error_multiplier

    where
        max_itemsize : preprocessing steps are in performed in float64 in spikewrap,
                       sync channel is not preprocessed.
        num_channels : number of channels in the recording (all of which
                       need to be preprocessed in memory together).
        error_multiplier : preprocessing steps in SI may use ~2 times as
                           much memory due to necessary copies. Therefore
                           increase the memory estimate by this factor.
    """
    if sync:
        max_itemsize = recording.dtype.itemsize
    else:
        max_itemsize = np.float64().itemsize

    mem_percent_use = 80

    try:
        # if in slurm environment
        os.environ["SLURM_JOB_ID"]
        # Only allocated memory (not free).
        total_limit_bytes = SlurmJobParameters().allocated_memory
    except KeyError:
        total_limit_bytes = psutil.virtual_memory().available

    mem_limit_bytes = int(np.floor(total_limit_bytes * mem_percent_use / 100))

    num_channels = recording.get_num_channels()
    error_multiplier = 2

    mem_per_sample_bytes = max_itemsize * num_channels * error_multiplier

    chunk_size = int(np.floor(mem_limit_bytes / mem_per_sample_bytes))

    message_user(
        f"Memory available (GB) ({mem_percent_use}%): {mem_limit_bytes / 1e9}, chunk size: {chunk_size}"
    )

    return chunk_size


def cast_pp_steps_values(
    pp_steps: Dict, list_or_tuple: Literal["list", "tuple"]
) -> None:
    """
    The settings in the pp_steps dictionary that defines the options
    for preprocessing should be stored in Tuple as they are not to
    be edited. However, when dumping Tuple to .yaml, there are tags
    displayed on the .yaml file which are very ugly.

    These are not shown when storing list, so this function serves
    to convert Tuple and List values in the preprocessing dict when
    loading / saving the preprocessing dict to .yaml files. This
    function converts `pp_steps` in place.

    Parameters
    ----------
    pp_steps : Dict
        The dictionary indicating the preprocessing steps to perform.

    list_or_tuple : Literal["list", "tuple"]
        The direction to convert (i.e. if "tuple", will convert to Tuple).
    """
    assert list_or_tuple in ["list", "tuple"], "Must cast to `list` or `tuple`."
    func = tuple if list_or_tuple == "tuple" else list

    for key in pp_steps.keys():
        pp_steps[key] = func(pp_steps[key])


def paths_are_in_datetime_order(
    list_of_paths: List[Path], creation_or_modification: str = "creation"
) -> bool:
    """
    Assert whether a list of paths are in order. By default, check they are
    in order by creation date. Can also check if they are ordered by
    modification date.

    Parameters
    ----------
    list_of_paths: List[Path]
        A list of paths to folders / files to check are in datetime
        order.

    creation_or_modification : str
        If "creation", check the list of paths are ordered by creation datetime.
        Otherwise if "modification", check they are sorterd by modification
        datetime.

    Returns
    -------
    is_in_time_order : bool
        Indicates whether `list_of_paths` was in creation or modification time
        order.
        depending on the value of `creation_or_modification`.
    """
    assert creation_or_modification in [
        "creation",
        "modification",
    ], "creation_or_modification must be 'creation' or 'modification."

    filter: Callable
    filter = (
        os.path.getctime if creation_or_modification == "creation" else os.path.getmtime
    )

    list_of_paths_by_time = copy.deepcopy(list_of_paths)
    list_of_paths_by_time.sort(key=filter)

    is_in_time_order = list_of_paths == list_of_paths_by_time

    return is_in_time_order


def show_preprocessing_dict(pp_steps: dict) -> None:
    """
    """
    message_user(
        f"\nThe preprocessing options dictionary is "
        f"{json.dumps(pp_steps, indent=4, sort_keys=True)}"
    )