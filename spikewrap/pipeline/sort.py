from __future__ import annotations

import copy
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Literal, Optional, Tuple, Union

if TYPE_CHECKING:
    from ..data_classes.sorting import SortingData

import platform

import spikeinterface.sorters as ss

from ..pipeline.load_data import load_data_for_sorting
from ..utils import slurm, utils, checks


def run_sorting(
    preprocessed_data_path: Union[Path, str],
    sorter: str = "kilosort2_5",
    sorter_options: Optional[Dict] = None,
    overwrite_existing_sorter_output: bool = False,
    verbose: bool = True,
    slurm_batch: bool = False,
) -> SortingData:
    """
    Run a sorter on pre-processed data. Takes a PreprocessingData (pipeline.data_class)
    object that contains spikeinterface recording objects for the preprocessing
    pipeline (or path to existing 'preprocessed' output folder.

    Here, save the preprocessed recording to binary file. Then, run sorting
    on the saved binary. The preprocessed binary and sorting output are
    saved in a 'derivatives' folder, in the same top-level folder as 'rawdata'.
    The folder structure will be the same as in 'rawdata'.

    Parameters
    ----------
    preprocessed_data_path : Union[Path, str]
        Path to previously saved 'preprocessed' directory.

    sorter : str
        Name of the sorter to use (e.g. "kilosort2_5").

    sorter_options : Dict
        Kwargs to pass to spikeinterface sorter class.

    overwrite_existing_sorter_output : bool
         If False, an error will be raised if sorting output already
         exists. If True, existing sorting output will be overwritten.

    verbose : bool
        If True, messages will be printed to consolve updating on the
        progress of preprocessing / sorting.

    slurm_batch : bool
        If True, the pipeline will be run in a SLURM job. Set False
        if running on an interactive job, or locally.

    """
    preprocessed_data_path = Path(preprocessed_data_path)

    sorting_data = load_data_for_sorting(preprocessed_data_path)
    sorting_data.set_sorter_output_paths(sorter)

    if slurm_batch:
        local_args = copy.deepcopy(locals())
        slurm.run_sorting_slurm(**local_args)
        return sorting_data

    sorter_options_dict = validate_inputs(slurm_batch, sorter, sorter_options, verbose)

    # Load preprocessed data from saved preprocess output path.
    utils.message_user(
        f"\nLoading binary preprocessed data from {preprocessed_data_path.as_posix()}\n"
    )

    # This must be run from the folder that has both sorter output AND rawdata
    os.chdir(sorting_data.base_path)

    singularity_image, docker_image = get_image_run_settings(sorter)

    utils.message_user(f"Starting {sorter} sorting...")

    # TODO: can remove on API change PR #1908
    # Also, once #1908 is merged and updated, we need to check
    # that 'delete_intermediate_files' is not passed by the
    # user in the config file because it is overridden here.
    if "kilosort" in sorter:
        sorter_options_dict.update({"delete_tmp_files": False})

    ss.run_sorter(
        sorter,
        sorting_data.data["0-preprocessed"],
        output_folder=sorting_data.sorting_output_path,
        singularity_image=singularity_image,
        docker_image=docker_image,
        remove_existing_folder=overwrite_existing_sorter_output,
        **sorter_options_dict,
    )

    move_singularity_image_if_required(sorting_data, singularity_image, sorter)

    return sorting_data


def move_singularity_image_if_required(
    sorting_data: SortingData,
    singularity_image: Optional[Union[Literal[True], str]],
    sorter: str,
) -> None:
    """
    On Linux, images are cased to the sorting_data base folder
    by default by SpikeInterface. To avoid re-downloading
    images, these are moved to a pre-determined folder (home
    for local, pre-set on an HPC). This is only required
    for singularity, as docker-desktop handles all image
    storage.

    Parameters
    ----------

    singularity_image: Optional[Union[Literal[True], Path]]
        Holds either a path to an existing (stored) sorter, or
        `True`. If `True`, no stored sorter image exists and so
        we move it. The next time sorting is performed, it will use
        this stored image.

    sorter : str
        Name of the sorter.
    """
    if singularity_image is True:
        assert platform.system() == "Linux", "Docker Desktop should be used on Windows or macOS."
        store_singularity_image(sorting_data.base_path, sorter)


def get_image_run_settings(
    sorter: str,
) -> Tuple[
    Optional[Union[Literal[True], str]], Optional[bool]
]:  # cannot set this to Literal[True], for unknown reason.
    """
    Determine how to run the sorting, either locally or in a container
    if required (e.g. kilosort2_5). On windows, Docker is used,
    otherwise singularity. Docker images are handled by Docker-desktop,
    but singularity image storage is handled internally, see
    `move_singularity_image_if_required()`.

    Parameters
    ----------

    sorter : str
        Sorter name.
    """
    can_run_locally = ["spykingcircus", "mountainsort5", "tridesclous"]

    if sorter in can_run_locally:
        singularity_image = docker_image = None
    else:
        if platform.system() == "Windows":
            singularity_image = None
            docker_image = True
        else:
            singularity_image = get_singularity_image(sorter)
            docker_image = None

    if singularity_image or docker_image:
        assert checks._check_virtual_machine()

        if platform.system != "Linux":
            assert checks.docker_desktop_is_running(),\
                "Docker is not running. Open Docker Desktop to start Docker."

    return singularity_image, docker_image


def store_singularity_image(base_path: Path, sorter: str) -> None:
    """
    When running locally, SpikeInterface will pull the docker image
    to the current working directly. Move this to home/.spikewrap
    so they can be used again in future and are centralised.

    Parameters
    ----------
    base_path : Path
        Base-path on the SortingData object, the path that holds
        `rawdata` and `derivatives` folders.

    sorter : str
        Name of the sorter for which to store the image.
    """
    path_to_image = base_path / utils.get_sorter_image_name(sorter)
    shutil.move(path_to_image, utils.get_local_sorter_path(sorter).parent)


def get_singularity_image(sorter: str) -> Union[Literal[True], str]:
    """
    Get the path to a pre-installed system singularity image. If none
    can be found, set to True. In this case SpikeInterface will
    pull the image to the current working directory, and
    this will be moved after sorting
    (see store_singularity_image).

    Parameters
    ----------
    sorter : str
        Name of the sorter to get the image for.

    Returns
    -------
    singularity_image [ Union[Literal[True], str]
        If `str`, the path to the singularity image. Otherwise if `True`,
        this tells SpikeInterface to pull the image.
    """
    singularity_image: Union[Literal[True], str]

    if utils.get_hpc_sorter_path(sorter).is_file():
        singularity_image = str(utils.get_hpc_sorter_path(sorter))

    elif utils.get_local_sorter_path(sorter).is_file():
        singularity_image = str(utils.get_local_sorter_path(sorter))
    else:
        singularity_image = True

    return singularity_image


def validate_inputs(
    slurm_batch: bool, sorter: str, sorter_options: Optional[Dict], verbose: bool
) -> Dict:
    """
    Check that the sorter is valid, singularity is installed and format
    the dictionary of options to pass to the sorter.

    Parameters
    ----------
    slurm_batch : bool
        Whether the run is a SLURM batch. This must be False, otherwise
        indicates some recursion has occurred when SLURM run itself
        calls this function.

    sorter : str
        Name of the sorter.

    sorter_options : Optional[Dict]
        Options to pass to the SpikeInterface sorter. If None, no options
        are passed.

    verbose : bool
        Whether SpikeInterface sorting is run in 'verbose' mode.

    Returns
    -------
    sorter_options_dict : Dict
        A dictionary of configurations to run the sorter with, these
        are passed to SpikeInterface sorter.
    """
    assert slurm_batch is False, "SLURM run has slurm_batch set True"

    supported_sorters = [
        "kilosort2",
        "kilosort2_5",
        "kilosort3",
        "mountainsort5",
        "spykingcircus",
        "tridesclous",
    ]

    assert (
        sorter in supported_sorters
    ), f"sorter {sorter} is invalid, must be one of: {supported_sorters}"

    assert (
        utils.check_singularity_install()
    ), "Singularity must be installed to run sorting."

    sorter_options_dict = {}
    if sorter_options is not None and sorter in sorter_options:
        sorter_options_dict = sorter_options[sorter]

    sorter_options_dict.update({"verbose": verbose})

    return sorter_options_dict
