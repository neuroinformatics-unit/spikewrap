from __future__ import annotations

import copy
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Literal, Tuple, Union

from ..configs.configs import get_configs
from ..data_classes.preprocessing import PreprocessingData
from ..utils import logging_sw, slurm, utils
from ..utils.custom_types import HandleExisting
from .load_data import load_data
from .postprocess import run_postprocess
from .preprocess import preprocess
from .sort import run_sorting

if TYPE_CHECKING:
    pass

    # visualisation
    # TODO: double check SLURM
    # TODO: delete intermediate files: use new spikeinterface settings for kilosort.


def run_full_pipeline(
    base_path: Union[Path, str],
    sub_name: str,
    run_names: Union[List[str], str],
    config_name: str = "default",
    sorter: str = "kilosort2_5",
    concat_for_sorting: bool = True,
    existing_preprocessed_data: HandleExisting = "load_if_exists",
    existing_sorting_output: HandleExisting = "load_if_exists",
    overwrite_postprocessing: bool = False,
    postprocessing_to_run: Union[Literal["all"], Dict] = "all",
    delete_intermediate_files: Tuple[
        Literal["recording.dat", "temp_wh.dat", "waveforms"]
    ] = ("recording.dat",),
    verbose: bool = True,
    slurm_batch: bool = False,
) -> None:
    """
    Run preprocessing, sorting and post-processing on SpikeGLX data.
    see README.md for detailed information on use. If waveforms and
    postprocessing exist for the subjects / runs, it will be
    overwritten.

    This function must be run in main as uses multiprocessing e.g.
    if __name__ == "__main__":
        run_full_pipeline(args...)

    Parameters
    ----------
    base_path : Union[Path, str]
        Path to the rawdata folder containing subjects folders.

    sub_name : str
        Subject to preprocess. The subject top level dir should reside in
        base_path/rawdata/ .

    run_names : Union[List[str], str],
        The SpikeGLX run name (i.e. not including the gate index). This can
        also be a list of run names. Preprocessing will still occur per-run.
        Runs are concatenated in the order passed prior to sorting.

    config_name : str
        The name of the configuration to use. Note this must be the name
        of a .yaml file (not including the extension) stored in
        spikewrap/configs.

    sorter : str
        name of the sorter to use e.g. "kilosort2_5".

    existing_preprocessed_data : Literal["overwrite", "load_if_exists", "fail_if_exists"]
        Determines how existing preprocessed data (e.g. from a prior pipeline run)
        is treated.
            "overwrite" : will overwrite any existing preprocessed data output. This will
                          delete the 'preprocessed' folder. Therefore, never save
                          derivative work there.
            "load_if_exists" : will search for existing data and load if it exists.
                               Otherwise, will use the preprocessing from the
                               current run.
            "fail_if_exists" : If existing preprocessed data is found, an error
                               will be raised.

    existing_sorting_output : bool
        Determines how existing sorted data is treated. The same behaviour
        as `existing_preprocessed_data` but for sorting output. If overwrite,
        the 'sorting' folder will be deleted. Therefore, never save
        derivative work there.

    overwrite_postprocessing : bool
        If `False`, an error will be raised if postprocessing output already
        exists. Otherwise, 'postprocessing' folder will be overwritten. Note,
        that the entire 'postprocessing' folder (including all contents) will be
        deleted. Therefore, never save derivative work there.

    postprocessing_to_run : Union[Literal["all"], Dict]
        Specify the postprocessing to run. By default, "all" will run
        all available postprocessing. Otherwise, provide a dict of
        including postprocessing to run e.g. {"quality_metrics: True"}.

    delete_intermediate_files : Tuple[Union["preprocessing", "recording.dat", "temp_wh.dat", "waveforms"]]  # TODO: check types
        Specify intermediate files or folders to delete. This option is useful for
        reducing the size of output data by deleting unneeded files.

        preprocessing  - the 'preprocesed' folder holding the data that has been
                         preprocessed by SpikeInterface
        recording.dat - SpikeInterfaces copies the preprocessed data to folder
                        prior to sorting, where it resides in the 'sorter_output'
                        folder. Often, this can be deleted after sorting.
        temp_wh.dat - Kilosort output file that holds the data preprocessed by
                      Kilosort (e.g. drift correction). By default, this is used
                      for visualisation in Phy.
        waveforms - The waveform outputs that SpikeInterface generates to calculate
                    quality metrics. Often, these can be deleted once final quality
                    metrics are computed.

    verbose : bool
        If True, messages will be printed to console updating on the
        progress of preprocessing / sorting.

    slurm_batch : bool
        If True, the pipeline will be run in a SLURM job. Set False
        if running on an interactive job, or locally.
    """
    if slurm_batch:
        local_args = copy.deepcopy(locals())
        slurm.run_full_pipeline_slurm(**local_args)
        return
    assert slurm_batch is False, "SLURM run has slurm_batch set True"

    pp_steps, sorter_options, waveform_options = get_configs(config_name)

    logs = logging_sw.get_started_logger(
        utils.get_logging_path(base_path, sub_name), "full_pipeline"
    )

    loaded_data = load_data(base_path, sub_name, run_names, data_format="spikeglx")

    preprocess_and_save(loaded_data, pp_steps, existing_preprocessed_data, verbose)

    sorting_data = run_sorting(
        base_path,
        sub_name,
        run_names,
        sorter,
        concat_for_sorting,
        sorter_options,
        existing_sorting_output,
        verbose,
    )

    # Run Postprocessing
    for run_name in sorting_data.get_all_run_names():
        sorting_path = sorting_data.get_sorting_path(run_name)

        postprocess_data = run_postprocess(
            sorting_path,
            overwrite_postprocessing=overwrite_postprocessing,
            existing_waveform_data="fail_if_exists",
            postprocessing_to_run=postprocessing_to_run,
            verbose=verbose,
            waveform_options=waveform_options,
        )

    for run_name in sorting_data.get_all_run_names():
        handle_delete_intermediate_files(
            run_name, sorting_data, delete_intermediate_files
        )

    logs.stop_logging()


# --------------------------------------------------------------------------------------
# Preprocessing
# --------------------------------------------------------------------------------------


def preprocess_and_save(
    preprocess_data: PreprocessingData,
    pp_steps,
    existing_preprocessed_data: Literal[
        "overwrite", "load_if_exists", "fail_if_exists"
    ],
    verbose,
) -> None:
    """
    Handle the loading of existing preprocessed data.
    See `run_full_pipeline()` for details.
    """
    for run_name in preprocess_data.run_names:
        preprocess_path = preprocess_data.get_preprocessing_path(run_name)

        if existing_preprocessed_data == "load_if_exists":
            if preprocess_path.is_dir():
                utils.message_user(
                    f"\nSkipping preprocessing, using file at "
                    f"{preprocess_path} for sorting.\n"
                )
                continue  # sorting will automatically use the existing data
            else:
                utils.message_user(
                    f"No data found at {preprocess_path}, saving" f"preprocessed data."
                )
                overwrite = False

        elif existing_preprocessed_data == "overwrite":
            if preprocess_path.is_dir():
                utils.message_user(f"Removing existing file at {preprocess_path}\n")

            utils.message_user(f"Saving preprocessed data to {preprocess_path}")
            overwrite = True

        elif existing_preprocessed_data == "fail_if_exists":
            if preprocess_path.is_dir():
                raise FileExistsError(
                    f"Preprocessed binary already exists at "
                    f"{preprocess_path}. "
                    f"To overwrite, set 'existing_preprocessed_data' to 'overwrite'"
                )
            overwrite = False

        else:
            raise ValueError(  # TODO: use assert not and end here
                "`existing_prepreprocessed_data` argument not recognised."
                "Must be: 'load_if_exists', 'fail_if_exists' or 'overwrite'."
            )

        preprocess_data = preprocess(preprocess_data, run_name, pp_steps, verbose)
        preprocess_data.save_preprocessed_data(run_name, overwrite)


# --------------------------------------------------------------------------------------
# Remove Intermediate Files
# --------------------------------------------------------------------------------------


def handle_delete_intermediate_files(run_name, sorting_data, delete_intermediate_files):
    """ """
    if "recording.dat" in delete_intermediate_files:
        if (
            recording_file := sorting_data.get_sorter_output_path(run_name)
            / "recording.dat"
        ).is_file():
            recording_file.unlink()

    if "temp_wh.dat" in delete_intermediate_files:
        if (
            recording_file := sorting_data.get_sorter_output_path(run_name)
            / "temp_wh.dat"
        ).is_file():
            recording_file.unlink()

    if "waveforms" in delete_intermediate_files:
        if (
            waveforms_path := sorting_data.get_postprocessing_path(run_name)
            / "waveforms"
        ).is_dir():
            shutil.rmtree(waveforms_path)
