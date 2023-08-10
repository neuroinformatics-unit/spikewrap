from __future__ import annotations

import copy
import os
from typing import Dict, Optional

import spikeinterface.sorters as ss

from ..data_classes.sorting import SortingData
from ..utils import logging_sw, slurm, utils
from ..utils.managing_images import (
    get_image_run_settings,
    move_singularity_image_if_required,
)


def run_sorting(
    base_path,
    sub_name,
    run_names,
    sorter: str,
    concat_for_sorting: bool,
    sorter_options: Optional[Dict] = None,
    existing_sorting_output: bool = False,  # TODO: fix
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
    logs = logging_sw.get_started_logger(
        utils.get_logging_path(base_path, sub_name), "full_pipeline"
    )

    sorting_data = SortingData(
        base_path,
        sub_name,
        run_names,
        sorter=sorter,
        concat_for_sorting=concat_for_sorting,
    )

    if slurm_batch:
        local_args = copy.deepcopy(locals())
        slurm.run_sorting_slurm(**local_args)
        return sorting_data

    sorter_options_dict = validate_inputs(slurm_batch, sorter, sorter_options, verbose)

    # This must be run from the folder that has both sorter output AND rawdata
    os.chdir(sorting_data.base_path)

    singularity_image, docker_image = get_image_run_settings(sorter)

    if "kilosort" in sorter:
        sorter_options_dict.update({"delete_tmp_files": False})

    run_sorting_on_all_runs(
        sorting_data,
        singularity_image,
        docker_image,
        existing_sorting_output=existing_sorting_output,
        **sorter_options_dict,
    )

    move_singularity_image_if_required(sorting_data, singularity_image, sorter)

    logs.stop_logging()

    return sorting_data


def run_sorting_on_all_runs(
    sorting_data,
    singularity_image,
    docker_image,
    existing_sorting_output,
    **sorter_options_dict,
):
    """ """
    utils.message_user(f"Starting {sorting_data.sorter} sorting...")

    #    if sorting_data.concat_for_sorting:
    #        run_names = [sorting_data.concat_run_name()]
    #        output_paths = [sorting_data.get_sorting_path(run_name=None)]  # TODO: figure out this confusing thing?
    #    else:
    #        run_names = sorting_data.run_names
    #        output_paths = [sorting_data.get_sorting_path(run_name) for run_name in sorting_data.run_names]

    #    for run_name, output_path in zip(run_names, output_paths):

    for run_name in sorting_data.get_all_run_names():
        output_path = sorting_data.get_sorting_path(run_name)

        if output_path.is_dir():
            if existing_sorting_output == "fail_if_exists":
                raise RuntimeError(
                    f"Sorting output already exists at {output_path} and"
                    f"`existing_sorting_output` is set to 'fail_if_exists'."
                )

            elif existing_sorting_output == "load_if_exists":
                utils.message_user(
                    f"Sorting output already exists at {output_path}. Nothing "
                    f"will be done. The existing sorting will be used for postprocessing "
                    f"if running with `run_full_pipeline`"
                )
                continue

            quick_safety_check(existing_sorting_output, output_path)

        ss.run_sorter(
            sorting_data.sorter,
            sorting_data[run_name],
            output_folder=output_path,
            singularity_image=singularity_image,
            docker_image=docker_image,
            remove_existing_folder=True,
            **sorter_options_dict,
        )

        sorting_data.save_sorting_info(run_name)


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

    sorter_options_dict = {}
    if sorter_options is not None and sorter in sorter_options:
        sorter_options_dict = sorter_options[sorter]

    sorter_options_dict.update({"verbose": verbose})

    return sorter_options_dict


def quick_safety_check(existing_sorting_output, output_path):
    """
     In this case, either output path does not exist, or it does
     and `existing_sorter_output` is "overwrite"

    TODO: delete after some testing
    """
    assert existing_sorting_output != "fail_if_exists"
    if existing_sorting_output == "load_if_exists":
        assert not output_path.is_dir()
