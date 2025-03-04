from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from pathlib import Path


import copy
import json
import os

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
