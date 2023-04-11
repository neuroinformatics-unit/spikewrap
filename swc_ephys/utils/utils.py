import pickle
from pathlib import Path
from typing import Dict, List, Union, Tuple
import numpy as np
from spikeinterface.core import BaseRecording

def get_keys_first_char(dict_: Dict, as_int: bool = False) -> Union[List[str], List[int]]:
    """
    TODO: horrible?
    """
    if as_int:
        return [int(key[0]) for key in dict_.keys()]
    else:
        return [key[0] for key in dict_.keys()]


def get_dict_value_from_step_num(dict_: Dict, step_num: str) -> Tuple[BaseRecording, str]:
    """
    """
    if step_num == "last":
        pp_key_nums = get_keys_first_char(dict_, as_int=True)
        step_num = str(
            int(np.max(pp_key_nums))
        )  # TODO: for now, complete overkill but this is critical
        assert (
            int(step_num) == len(dict_.keys()) - 1
        ), "the last key has been taken incorrectly"

    pp_key = [key for key in dict_.keys() if key[0] == step_num]

    assert len(pp_key) == 1, "pp_key must always have unique first char "

    full_key = pp_key[0]

    return dict_[full_key], full_key


def message_user(message: str):
    """ """
    print(message)


def load_data_and_recording(preprocessed_output_path: Path):
    """
    TODO: think about type, enforce higher
    """
    with open(Path(preprocessed_output_path) / "data_class.pkl", "rb") as file:
        data = pickle.load(file)
    recording = data.load_preprocessed_binary()

    return data, recording


def get_sorter_path(sorter: str) -> Path:
    """
    TODO: these should be loaded on a module.
    This is NOT good!
    """
    base_path = Path("/ceph/neuroinformatics/neuroinformatics/scratch/sorter_images")
    return base_path / sorter / f"{sorter}-compiled-base.sif"
