import copy
import os
import shutil
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
    pipeline (or path to existing 'preprocessed' output folder.

    Here, save the preprocessed recording to binary file. Then, run sorting
    on the saved binary. The preprocessed binary and sorting output are
    saved in a 'derivatives' folder, in the same top-level folder as 'rawdata'.
    The folder structure will be the same as in 'rawdata'.

    Parameters
    ----------

    data : Data
        swc_ephys Data object or path to previously saved 'preprocessed' directory.

    sorter : str
        Name of the sorter to use (e.g. "kilosort2_5").

    sorter_options : Dict
        Kwargs to pass to spikeinterface sorter class.

    use_existing_preprocessed_file : bool
        If this function has been run previously
        and a saved pre-proccessed binary already
        exists in the 'preprocessed' folder for this
        subject, it will be used. If False and this folder
        exists, an error will be raised.

     overwrite_existing_sorter_output : bool
         If False, an error will be reaised if sorting output already
         exists. If True, existing sorting output will be overwritten.

    verbose : bool
        If True, messages will be printed to consolve updating on the
        progress of preprocessing / sorting.

    slurm_batch : bool
        If True, the pipeline will be run in a SLURM job. Set False
        if running on an interactive job, or locally.

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

    if singularity_image is True:  # no existing image was found
        store_singularity_image(loaded_data.base_path, sorter)


def store_singularity_image(base_path, sorter):
    """
    When running locally, SPikeInterface will pull the docker image
    to the current working directly. Move this to home/.swc_ephys
    so they can be used again in future and are centralised.
    """
    path_to_image = base_path / utils.get_sorter_image_name(sorter)
    shutil.move(path_to_image, utils.get_local_sorter_path(sorter).parent)


def get_data_and_recording(
    data: Union[Data, Path, str], use_existing_preprocessed_file: bool
) -> Tuple[Data, BaseRecording]:
    """

    Parameters
    ----------
    data: Data
        Can contain a path to previously saved 'preprocessed' directory.
        This will load a spikeinterface recording that will be fed directory
        to the sorter. If a Data object is passed, the last recording in the
        preprocessing chain will be saved to binary form as required for
        sorting and the recording object returned.

    use_existing_preprocessed_file : bool
        By default, an error will be thrown if the
        'preprocessed' directory already exists for the
        subject stored in the Data class.
        If use_existing_preprocessed_file is True, the
        'preprocessed' directory will be loaded
        and used for sorting and no error thrown.

    Returns
    -------

    data : Data
        The Data object (if a Data object is passed, this will be the same as passed)

    recording : BaseRecording
        Recording object (the last in the preprocessing chain) to be passed
        to the sorter.
    """
    if isinstance(data, Data):
        assert not (
            data.preprocessed_binary_data_path.is_dir()
            and use_existing_preprocessed_file is False
        ), (
            f"Preprocessed binary already exists at "
            f"{data.preprocessed_binary_data_path}. "
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
    """
    Check that the sorter is valid, singularity is installed and format
    the dictionary of options to pass to the sorter.
    """
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
    """
    Get the path to a pre-installed system singularity image. If none
    can be found, set to True. In this case SpikeInterface will
    pull the imagine to the current working directory, and
    this will be moved after sorting
    (see store_singularity_image).
    """
    singularity_image: Union[Literal[True], str]

    if utils.get_hpc_sorter_path(sorter).is_file():
        singularity_image = str(utils.get_hpc_sorter_path(sorter))

    elif utils.get_local_sorter_path(sorter).is_file():
        singularity_image = str(utils.get_local_sorter_path(sorter))
    else:
        singularity_image = True

    return singularity_image
