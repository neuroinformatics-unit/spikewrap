from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from pathlib import Path

    from spikeinterface.core import BaseRecording

import copy
import json
import os

import numpy as np
import yaml


def message_user(message: str) -> None:
    """
    Method to print message to user.

    Centralising this method ensures consistent output formatting
    and allows future adjustments (e.g., logging or GUI integration).

    Parameters
    ----------
    message
        Message to print.
    """
    print(f"\n{message}")


def _get_dict_value_from_step_num(
    data: dict, step_num: str
) -> tuple[BaseRecording, str]:
    """
    Get the preprocessed recording from a `Preprocessed._data` dict given
    the preprocessing step number.

    Keys in the dict represent preprocessing steps, formatted as:
    e.g., 0-raw, 1-raw-bandpass_filter, 2-raw_bandpass_filter-common_average.

    This function retrieves the recording object by matching the step number.

    Parameters
    ----------
    data
        The `Preprocessed._data` dict containing preprocessing steps and recordings.

    step_num
        The preprocessing step number (or "last" for the final step) to retrieve.

    Returns
    -------
    dict_value
        The recording object corresponding to the given step number.

    pp_key
        The key of the preprocessing dict associated with the step number.
    """
    if step_num == "last":
        pp_key_nums = _get_keys_first_char(data, as_int=True)

        # Complete overkill as a check but this is critical.
        step_num = str(int(np.max(pp_key_nums)))
        assert (
            int(step_num) == len(data.keys()) - 1
        ), "the last key has been taken incorrectly"

    select_step_pp_key = [key for key in data.keys() if key.split("-")[0] == step_num]

    assert len(select_step_pp_key) == 1, "pp_key must always have unique first char"

    pp_key: str = select_step_pp_key[0]
    recording = data[pp_key]

    return recording, pp_key


# TODO: should overload
def _get_keys_first_char(data: dict, as_int: bool = False) -> list[str] | list[int]:
    """
    Get the first character of all keys in a dictionary.
    Expected that the first characters are integers (as str type).

    Parameters
    ----------
    data
        The `Preprocessed._data` dict containing preprocessing steps and recordings.

    as_int
        If True, the first character of the keys are cast to integer type.

    Returns
    -------
    list_of_numbers
        A list of numbers of string or integer type, that are
        the first numbers of the data dictionary keys.
    """
    list_of_numbers = [
        int(key.split("-")[0]) if as_int else key.split("-")[0] for key in data.keys()
    ]
    return list_of_numbers


def _paths_are_in_datetime_order(
    list_of_paths: list[Path], creation_or_modification: str = "creation"
) -> bool:
    """
    Assert whether a list of paths are in order. By default, check they are
    in order by creation date. Can also check if they are ordered by
    modification date.

    Parameters
    ----------
    list_of_paths
        A list of paths to folders / files to check are in datetime order.

    creation_or_modification
        If "creation", check the list of paths are ordered by creation datetime.
        Otherwise, if "modification", check they are sorted by modification
        datetime.

    Returns
    -------
    is_in_time_order
        Indicates whether `list_of_paths` was in creation or modification time
        order depending on the value of `creation_or_modification`.
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


def show_preprocessing_configs(pp_steps: dict) -> None:
    """
    Print the preprocessing options.
    """
    message_user(
        f"\nThe preprocessing options are: "
        f"{json.dumps(pp_steps, indent=4, sort_keys=True)}"
    )


def show_sorting_configs(sorting_configs: dict) -> None:
    """
    Print the sorting options.
    """
    message_user(
        f"\nThe sorting options are: "
        f"{json.dumps(sorting_configs, indent=2, sort_keys=True)}"
    )


def _dump_dict_to_yaml(filepath: Path | str, dict_: dict) -> None:
    """
    Save a dictionary to Yaml file. Note that keys are
    not sorted and will be saved in the dictionary order.
    """
    with open(
        filepath,
        "w",
    ) as file_to_save:
        yaml.dump(dict_, file_to_save, sort_keys=False)


def _load_dict_from_yaml(filepath: Path | str) -> dict:
    """
    Load a dictionary from yaml file.
    """
    with open(filepath, "r") as file:
        loaded_dict = yaml.safe_load(file)
    return loaded_dict
