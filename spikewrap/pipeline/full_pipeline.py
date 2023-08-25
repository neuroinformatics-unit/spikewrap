from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, Literal, Optional, Tuple, Union

from ..configs.configs import get_configs
from ..data_classes.preprocessing import PreprocessingData
from ..data_classes.sorting import SortingData
from ..utils import logging_sw, slurm, utils
from ..utils.custom_types import DeleteIntermediate, HandleExisting
from .load_data import load_data
from .postprocess import run_postprocess
from .preprocess import run_preprocess
from .sort import run_sorting


def run_full_pipeline(
    base_path: Union[Path, str],
    sub_name: str,
    sessions_and_runs: Dict,
    config_name: str = "default",
    sorter: str = "kilosort2_5",
    concat_sessions_for_sorting: bool = False,
    concat_runs_for_sorting: bool = False,
    existing_preprocessed_data: HandleExisting = "fail_if_exists",
    existing_sorting_output: HandleExisting = "fail_if_exists",
    overwrite_postprocessing: bool = False,
    postprocessing_to_run: Union[Literal["all"], Dict] = "all",
    delete_intermediate_files: DeleteIntermediate = ("recording.dat",),
    slurm_batch: bool = False,
) -> Tuple[Optional[PreprocessingData], Optional[SortingData]]:
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

    concat_for_sorting: bool
        If `True`, preprocessed runs are concatenated before sorting. Otherwise,
        sorting is performed per-run.

    existing_preprocessed_data : custom_types.HandleExisting
        Determines how existing preprocessed data (e.g. from a prior pipeline run)
        is handled.
            "overwrite" : will overwrite any existing preprocessed data output. This will
                          delete the 'preprocessed' folder. Therefore, never save
                          derivative work there.
            "skip_if_exists" : will search for existing data and skip preprocesing
                               if it exists (sorting will run on existing preprocessed data).
                               Otherwise, will preprocess and save the current run.
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
        Accepted keys are "quality_metrics" and "unit_locations".

    delete_intermediate_files : DeleteIntermediate
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

    slurm_batch : bool
        If True, the pipeline will be run in a SLURM job. Set False
        if running on an interactive job, or locally.
    """
    passed_arguments = locals()

    if slurm_batch:
        slurm.run_full_pipeline_slurm(**passed_arguments)
        return None, None
    assert slurm_batch is False, "SLURM run has slurm_batch set True"

    pp_steps, sorter_options, waveform_options = get_configs(config_name)

    logs = logging_sw.get_started_logger(
        utils.get_logging_path(base_path, sub_name),
        "full_pipeline",
    )
    utils.show_passed_arguments(passed_arguments, "`run_full pipeline`")

    loaded_data = load_data(
        base_path, sub_name, sessions_and_runs, data_format="spikeglx"
    )

    run_preprocess(loaded_data, pp_steps, save_to_file=existing_preprocessed_data)

    sorting_data = run_sorting(
        base_path,
        sub_name,
        sessions_and_runs,
        sorter,
        concat_sessions_for_sorting,
        concat_runs_for_sorting,
        sorter_options,
        existing_sorting_output,
    )
    assert sorting_data is not None

    # Run Postprocessing
    for ses_name, run_name in sorting_data.get_sorting_sessions_and_runs():
        sorting_path = sorting_data.get_sorting_path(ses_name, run_name)

        postprocess_data = run_postprocess(
            sorting_path,
            overwrite_postprocessing=overwrite_postprocessing,
            existing_waveform_data="fail_if_exists",
            postprocessing_to_run=postprocessing_to_run,
            waveform_options=waveform_options,
        )

    # Delete intermediate files
    for ses_name, run_name in sorting_data.get_sorting_sessions_and_runs():
        handle_delete_intermediate_files(
            ses_name, run_name, sorting_data, delete_intermediate_files
        )
    logs.stop_logging()

    return (
        loaded_data,
        sorting_data,
    )


# --------------------------------------------------------------------------------------
# Preprocessing
# --------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------
# Remove Intermediate Files
# --------------------------------------------------------------------------------------


def handle_delete_intermediate_files(
    ses_name: str,
    run_name: Optional[str],
    sorting_data: SortingData,
    delete_intermediate_files: DeleteIntermediate,
):
    """
    Handle the cleanup of intermediate files created during sorting and
    postprocessing. Some of these files are sorter-specific (e.g. `temp_wh.dat`
    for Kilosort). See `run_full_pipeline` for inputs
    """
    if "recording.dat" in delete_intermediate_files:
        if (
            recording_file := sorting_data.get_sorter_output_path(ses_name, run_name)
            / "recording.dat"
        ).is_file():
            recording_file.unlink()

    if "temp_wh.dat" in delete_intermediate_files:
        if (
            recording_file := sorting_data.get_sorter_output_path(ses_name, run_name)
            / "temp_wh.dat"
        ).is_file():
            recording_file.unlink()

    if "waveforms" in delete_intermediate_files:
        if (
            waveforms_path := sorting_data.get_postprocessing_path(ses_name, run_name)
            / "waveforms"
        ).is_dir():
            shutil.rmtree(waveforms_path)
