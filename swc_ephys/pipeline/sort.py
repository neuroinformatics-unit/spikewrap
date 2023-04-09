import os
from pathlib import Path

import spikeinterface.sorters as ss

from ..utils import utils


def run_sorting(data, sorter="kilosort2_5", sorter_options=None, use_existing=False):
    """
    TODO: accepts data object OR path to written binary
    """
    supported_sorters = ["kilosort2", "kilosort2_5", "kilosort3"]
    assert sorter in supported_sorters, f"sorter must be: {supported_sorters}"

    if sorter_options is None:
        sorter_options = {}

    if isinstance(data, str) or isinstance(data, Path):
        utils.message_user(f"\nLoading binary preprocessed data from {data}\n")
        data, recording = utils.load_data_and_recording(data)

    elif (
        use_existing and data.preprocessed_binary_data_path.is_dir()
    ):  # TODO: need more checks here
        utils.message_user(
            f"\n"
            f"use_existing=True. "
            f"Loading binary preprocessed data from {data.preprocessed_output_path}\n"
        )
        data, recording = utils.load_data_and_recording(data.preprocessed_output_path)
    else:
        utils.message_user(
            f"\nSaving data class and binary preprocessed data to "
            f"{data.preprocessed_binary_data_path}\n"
        )

        data.save_all_preprocessed_data()
        recording, __ = utils.get_dict_value_from_step_num(data, "last")

    data.set_sorter_output_paths(sorter)

    # this must be run from the folder that has both sorter output AND
    # rawdata
    os.chdir(data.base_path)

    utils.message_user(f"Starting {sorter} sorting...")
    sorting_output = ss.run_sorter(
        sorter,
        recording,
        output_folder=data.sorter_base_output_path,
        singularity_image=utils.get_sorter_path(sorter),
        **sorter_options[sorter],
    )

    # TODO: dump some kind of config with data configs in the sorter output too
    utils.message_user(f"Saving sorter output to {data.sorter_output_path}")
    sorting_output.save(folder=data.sorter_output_path)
