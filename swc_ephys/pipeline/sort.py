import copy
import os
from pathlib import Path
from typing import Dict, Literal, Optional, Tuple, Union

import spikeinterface.sorters as ss
from spikeinterface.core import BaseRecording

from ..utils import slurm, utils
from .data_class import Data


def run_sorting(
    data: Union[Data, Path, str],
    sorter: str = "kilosort2_5",
    sorter_options: Optional[Dict] = None,
    use_existing_preprocessed_file: bool = False,
    overwrite_existing_sorter_output: bool = False,
    verbose: bool = True,
    slurm_batch=False,
):
    """
    Run a sorter on pre-processed data. Takes a Data (pipeline.data_class)
    object that contains spikeinterface recording objects for the preprocessing
    pipeline (these are lazy until data is saved to binary). TODO UPDATE

    Here, save the preprocessed recording to binary file. Then, run sorting
    on the saved binary. The preprocessed binary and sorting output are
    saved in a 'derivatives' folder, in the same top-level folder as 'rawdata'.
    The folder structure will be the same as in 'rawdata'.

    Parameters
    ----------

    data : swc_ephys Data object or path to previously saved 'preprocessed' directory.

    sorter : name of the sorter to use (e.g. "kilosort2_5")

    sorter_options : kwargs to pass to spikeinterface sorter class

    use_existing_preprocessed_file : by default, if the 'preprocessed' folder for the
                                     subject on Data already exists, an error is raised.
                                     If use_existing_preprocessed_file is True, instead
                                     the 'preprocessed' folder will be loaded and used
                                     passed to the sorter.

    """
    if slurm_batch:
        local_args = copy.deepcopy(locals())
        slurm.run_sorting_slurm(**local_args)
        return

    sorter_options_dict = validate_inputs(slurm_batch, sorter, sorter_options, verbose)

    # Write the data to file prior to sorting, or
    # load existing preprocessing from file required
    loaded_data, recording = get_data_and_recording(
        data, use_existing_preprocessed_file
    )

    loaded_data.set_sorter_output_paths(sorter)

    # this must be run from the folder that has both
    # sorter output AND rawdata
    os.chdir(loaded_data.base_path)

    singularity_image = get_singularity_image(sorter)

    if recording.get_num_segments() > 1:
        recording = utils.concatenate_runs(recording)

    utils.message_user(f"Starting {sorter} sorting...")

    ss.run_sorter(
        sorter,
        recording,
        output_folder=loaded_data.sorter_base_output_path,
        singularity_image=singularity_image,
        remove_existing_folder=overwrite_existing_sorter_output,
        **sorter_options_dict,
    )


def get_data_and_recording(
    data: Union[Data, Path, str], use_existing_preprocessed_file: bool
) -> Tuple[Data, BaseRecording]:
    """

    Parameters
    ----------
    data: a duck-typed variable, can be Data or a str / Path containing
          a path to previously saved 'preprocessed' directory. This will
          load a spikeinterface recording that will be fed directory
          to the sorter.

          if a Data object is passed, the last recording in the preprocessing
          chain will be saved to binary form as required for sorting and the recording
          object returned.

    use_existing_preprocessed_file : By default, an error will be thrown if the
                                     'preprocessed' directory already exists for the
                                     subject stored in the Data class.
                                     If use_existing_preprocessed_file is True, the
                                     'preprocessed' directory will be loaded
                                     and used for sorting and no error thrown.

    Returns
    -------

    data : the Data object (if a Data object is passed, this will be the same as passed)

    recording : recording object (the last in the preprocessing chain) to be fed
                to the sorter.
    """
    if isinstance(data, Data):
        assert not (
            data.preprocessed_binary_data_path.is_dir()
            and use_existing_preprocessed_file is False
        ), (
            f"Preprocessed binary already exists at {data.preprocessed_binary_data_path}. "
            f"To overwrite, set 'use_existing_preprocessed_file' to True"
        )

    if isinstance(data, str) or isinstance(data, Path):
        utils.message_user(f"\nLoading binary preprocessed data from {data}\n")
        data, recording = utils.load_data_and_recording(Path(data))

    elif use_existing_preprocessed_file and data.preprocessed_binary_data_path.is_dir():
        utils.message_user(
            f"\n"
            f"use_existing_preprocessed_file=True. "
            f"Loading binary preprocessed data from {data.preprocessed_output_path}\n"
        )
        data, recording = utils.load_data_and_recording(data.preprocessed_output_path)
    else:
        utils.message_user(
            f"\nSaving data class and binary preprocessed data to "
            f"{data.preprocessed_output_path}\n"
        )

        data.save_all_preprocessed_data()
        recording, __ = utils.get_dict_value_from_step_num(data, "last")

    return data, recording


def validate_inputs(
    slurm_batch: bool, sorter: str, sorter_options: Optional[Dict], verbose: bool
) -> Dict:
    assert slurm_batch is False, "SLURM run has slurm_batch set True"

    supported_sorters = ["kilosort2", "kilosort2_5", "kilosort3"]
    assert sorter in supported_sorters, f"sorter must be: {supported_sorters}"

    assert (
        utils.check_singularity_install()
    ), "Singularity must be installed to run sorting."

    sorter_options_dict = {}
    if sorter_options is not None:
        sorter_options_dict = sorter_options[sorter]

    sorter_options_dict.update({"verbose": verbose})

    return sorter_options_dict


def get_singularity_image(sorter: str) -> Union[Literal[True], str]:
    """"""
    singularity_image: Union[Literal[True], str]

    if utils.get_sorter_path(sorter).is_file():
        singularity_image = str(utils.get_sorter_path(sorter))
    else:
        singularity_image = True

    return singularity_image
