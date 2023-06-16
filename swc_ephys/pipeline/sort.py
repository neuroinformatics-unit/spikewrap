import copy
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Literal, Optional, Union

if TYPE_CHECKING:
    from ..data_classes.sorting import SortingData

import spikeinterface.sorters as ss

from ..pipeline.load_data import load_data_for_sorting
from ..utils import slurm, utils

# issue with laoding sync channel breaks probe


def run_sorting(
    preprocessed_data_path: Union[Path, str],
    sorter: str = "kilosort2_5",
    sorter_options: Optional[Dict] = None,
    overwrite_existing_sorter_output: bool = False,
    verbose: bool = True,
    slurm_batch: bool = False,
) -> Optional[SortingData]:
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

    preprocess_data_or_path : PreprocessingData
        swc_ephys PreprocessingData object or path to previously saved 'preprocessed' directory.

    sorter : str
        Name of the sorter to use (e.g. "kilosort2_5").

    sorter_options : Dict
        Kwargs to pass to spikeinterface sorter class.

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
    preprocessed_data_path = Path(preprocessed_data_path)

    if slurm_batch:
        local_args = copy.deepcopy(locals())
        slurm.run_sorting_slurm(**local_args)
        return None

    sorter_options_dict = validate_inputs(slurm_batch, sorter, sorter_options, verbose)

    # Load preprocessed data from saved preprocess output path.
    utils.message_user(
        f"\nLoading binary preprocessed data from {preprocessed_data_path.as_posix()}\n"
    )
    sorting_data = load_data_for_sorting(preprocessed_data_path)

    sorting_data.set_sorter_output_paths(sorter)

    # this must be run from the folder that has both
    # sorter output AND rawdata
    os.chdir(sorting_data.base_path)

    singularity_image = get_singularity_image(sorter)

    utils.message_user(f"Starting {sorter} sorting...")

    ss.run_sorter(
        sorter,
        sorting_data.data["0-preprocessed"],
        output_folder=sorting_data.sorter_base_output_path,
        singularity_image=singularity_image,
        remove_existing_folder=overwrite_existing_sorter_output,
        **sorter_options_dict,
    )

    if (
        singularity_image is True
    ):  # no existing image was found # TODO: need to use this only on local!
        store_singularity_image(sorting_data.base_path, sorter)

    return sorting_data


def store_singularity_image(base_path: Path, sorter: str) -> None:
    """
    When running locally, SPikeInterface will pull the docker image
    to the current working directly. Move this to home/.swc_ephys
    so they can be used again in future and are centralised.
    """
    path_to_image = base_path / utils.get_sorter_image_name(sorter)
    shutil.move(path_to_image, utils.get_local_sorter_path(sorter).parent)


def validate_inputs(
    slurm_batch: bool, sorter: str, sorter_options: Optional[Dict], verbose: bool
) -> Dict:
    """
    Check that the sorter is valid, singularity is installed and format
    the dictionary of options to pass to the sorter.
    """
    assert slurm_batch is False, "SLURM run has slurm_batch set True"

    supported_sorters = ["spykingcircus", "kilosort2", "kilosort2_5", "kilosort3"]
    assert sorter in supported_sorters, f"sorter must be: {supported_sorters}"

    assert (
        utils.check_singularity_install()
    ), "Singularity must be installed to run sorting."

    sorter_options_dict = {}
    if sorter_options is not None and sorter in sorter_options:
        sorter_options_dict = sorter_options[sorter]

    sorter_options_dict.update({"verbose": verbose})

    return sorter_options_dict


def get_singularity_image(sorter: str) -> Union[Literal[True], str]:
    """
    Get the path to a pre-installed system singularity image. If none
    can be found, set to True. In this case SpikeInterface will
    pull the image to the current working directory, and
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
