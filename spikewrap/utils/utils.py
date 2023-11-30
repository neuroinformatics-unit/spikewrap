from __future__ import annotations

import copy
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, List, Literal, Tuple, Union

import numpy as np
import yaml

if TYPE_CHECKING:
    from spikeinterface.core import BaseRecording

    from spikewrap.data_classes.preprocessing import PreprocessingData
    from spikewrap.data_classes.sorting import SortingData


# --------------------------------------------------------------------------------------
# Convenience functions and canonical objects
# --------------------------------------------------------------------------------------


def canonical_names(name: str) -> str:
    """
    Store the canonical names e.g. filenames, tags
    that are used throughout the project.

    Parameters
    ----------
    name : str
        short-hand name of the full name of interest.

    Returns
    -------
    filenames[name] : str
        The full name of interest e.g. filename.

    """
    filenames = {
        "preprocessed_yaml": "preprocessing_info.yaml",
        "sorting_yaml": "sorting_info.yaml",
    }
    return filenames[name]


def canonical_settings(setting: str) -> List:
    """
    Centralise all key settings around supported sorters
    and how they should be run.
    """
    canonical_settings = {
        "supported_sorters": [
            "kilosort2",
            "kilosort2_5",
            "kilosort3",
            "mountainsort5",
            "spykingcircus",
            "tridesclous",
        ],
        "sorter_can_run_locally": ["spykingcircus", "mountainsort5", "tridesclous"],
    }
    return canonical_settings[setting]


def get_formatted_datetime() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def spikewrap_version():
    """
    If the package is installd with `pip install -e .` then
    .__version__ will not work.
    """
    try:
        import spikewrap

        spikewrap_version = spikewrap.__version__
    except AttributeError:
        spikewrap_version = "not found."

    return spikewrap_version


def get_logging_path(base_path: Union[str, Path], sub_name: str) -> Path:
    """
    The path where logs from `run_full_pipeline`, `run_sorting`
    and `run_postprocessing` are saved.
    """
    return Path(base_path) / "derivatives" / "spikewrap" / sub_name / "logs"


def show_passed_arguments(passed_arguments, function_name):
    message_user(
        f"Running {function_name}. The function was called "
        f"with the arguments {passed_arguments}.",
    )


def message_user(message: str) -> None:
    """
    Method to interact with user.

    Parameters
    ----------
    message : str
        Message to print.
    """
    print(f"\n{message}")


def dump_dict_to_yaml(filepath: Union[Path, str], dict_: Dict) -> None:
    """
    Save a dictionary to Yaml file. Note that keys are
    not sorted and will be saved in the dictionary order.
    """
    with open(
        filepath,
        "w",
    ) as file_to_save:
        yaml.dump(dict_, file_to_save, sort_keys=False)


def load_dict_from_yaml(filepath: Union[Path, str]) -> Dict:
    """
    Load a dictionary from yaml file.
    """
    with open(filepath, "r") as file:
        loaded_dict = yaml.safe_load(file)
    return loaded_dict


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


# --------------------------------------------------------------------------------------
# Data class helpers
# --------------------------------------------------------------------------------------


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

    select_step_pp_key = [key for key in data.keys() if key.split("-")[0] == step_num]

    assert len(select_step_pp_key) == 1, "pp_key must always have unique first char"

    pp_key: str = select_step_pp_key[0]
    dict_value = data[pp_key]

    return dict_value, pp_key


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
