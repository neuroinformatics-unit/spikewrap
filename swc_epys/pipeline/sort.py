from preprocess import preprocess
from visualise import visualise
import spikeinterface.sorters  as ss
import utils
import os
from pathlib import Path
import pickle
import spikeinterface as si

def run_sorting(data,
                sorter="kilosort2_5"
                ):
    """
    TODO: accepts data object OR path to written binary
    """
    supported_sorters = ["kilosort2", "kilosort2_5", "kilosort3"]
    assert sorter in supported_sorters, f"sorter must be: {supported_sorters}"

    if isinstance(data, str) or isinstance(data, Path):
        utils.message_user(f"\nLoading binary preprocessed data from {data}\n")

        data, recording = utils.load_data_and_recording(data)
    else:
        utils.message_user(f"\nSaving data class and binary preprocessed data to {data.preprocessed_binary_data_path}\n")

        data.save_all_preprocessed_data()
        recording, __ = utils.get_dict_value_from_step_num(data, "last")

    data.set_sorter_output_paths(sorter)

    # this must be run from the folder that has both sorter output AND
    # rawdata
    os.chdir(data.base_path)

    utils.message_user(f"Starting {sorter} sorting...")
    sorting_output = ss.run_sorter(sorter,
                                   recording,
                                   output_folder=data.sorter_base_output_path,
                                   singularity_image=utils.get_sorter_path(sorter))

    # TODO: dump some kind of config with data configs in the sorter output too
    utils.message_user(f"Saving sorter output to {data.sorter_output_path}")
    sorting_output.save(folder=data.sorter_output_path)
