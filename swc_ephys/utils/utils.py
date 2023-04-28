import copy
import os.path
import pickle
import subprocess
from pathlib import Path
from typing import List, Tuple, Union

import numpy as np
from spikeinterface import concatenate_recordings
from spikeinterface.core import BaseRecording

from ..pipeline.data_class import Data


def get_keys_first_char(
    dict_: Data, as_int: bool = False
) -> Union[List[str], List[int]]:
    """
    Get the first character of all keys in a dictionary. Expected
    that the first characters are integers (as str type).

    as_int : if True, the first character of the keys are cast
             to integer type.
    """
    return [int(key[0]) if as_int else key[0] for key in dict_.keys()]


def get_dict_value_from_step_num(
    dict_: Data, step_num: str
) -> Tuple[BaseRecording, str]:
    """
    pipeline.data_class.Data contain keys indicating the
    preprocessing steps, starting with the preprocessing step number.
    e.g. 0-raw, 1-raw-bandpass_filter, 2-raw_bandpass_filter-common_average

    Return the value of the dict (spikeinterface recording object)
    from the dict using only the step number
    """
    if step_num == "last":
        pp_key_nums = get_keys_first_char(dict_, as_int=True)

        # complete overkill but this is critical
        step_num = str(int(np.max(pp_key_nums)))
        assert (
            int(step_num) == len(dict_.keys()) - 1
        ), "the last key has been taken incorrectly"

    select_step_pp_key = [key for key in dict_.keys() if key[0] == step_num]

    assert len(select_step_pp_key) == 1, "pp_key must always have unique first char"

    pp_key: str = select_step_pp_key[0]

    return dict_[pp_key], pp_key


def message_user(message: str, verbose: bool = True):
    """
    Method to interact with user.
    """
    if verbose:
        print(message)


def load_data_and_recording(
    preprocessed_output_path: Path,
    concatenate: bool = True,
) -> Tuple[Data, BaseRecording]:
    """
    During sorting, preprocessed data is saved to
    derivatives/<sub level dirs>/preprocessed. The spikeinterface
    recording (si_recording) and Data (data_class.pkl) are saved.

    This returns the Data and recording object loaded from
    the passed preprocess path.
    """
    with open(Path(preprocessed_output_path) / "data_class.pkl", "rb") as file:
        data = pickle.load(file)
    recording = data.load_preprocessed_binary()

    if concatenate:
        recording = concatenate_recordings([recording])

    return data, recording


def get_sorter_path(sorter: str) -> Path:
    """
    Return the path to the sorter image on the HCP.
    Currently, this is just in NIU scratch.
    """
    base_path = Path("/ceph/neuroinformatics/neuroinformatics/scratch/sorter_images")
    return base_path / sorter / f"{sorter}-compiled-base.sif"


def check_singularity_install():
    try:
        subprocess.run("singularity --version", shell=True)
        return True
    except FileNotFoundError:
        return False


def sort_list_of_paths_by_datetime_order(list_of_paths: List[Path]) -> List[Path]:
    """ """
    list_of_paths_by_creation_time = copy.deepcopy(list_of_paths)
    list_of_paths_by_creation_time.sort(key=os.path.getctime)

    assert_list_of_files_are_in_datetime_order(
        list_of_paths_by_creation_time, "modification"
    )

    return list_of_paths_by_creation_time


def assert_list_of_files_are_in_datetime_order(
    list_of_paths, creation_or_modification="creation"
):
    """ """
    filter = (
        os.path.getmtime if creation_or_modification == "creation" else "modification"
    )

    list_of_paths_by_mod_time = copy.deepcopy(list_of_paths)
    list_of_paths_by_mod_time.sort(key=filter)

    assert list_of_paths == list_of_paths_by_mod_time, (
        f"Run list of files are not in {creation_or_modification} datetime order. "
        f"Files List: {list_of_paths}\n"
        f"Contact Joe as it is not clear what to do in this case."
    )
