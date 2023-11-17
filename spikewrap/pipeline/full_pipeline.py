from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from ..configs.configs import get_configs
from ..data_classes.preprocessing import PreprocessingData
from ..data_classes.sorting import SortingData
from ..utils import logging_sw, slurm, utils, validate
from ..utils.custom_types import DeleteIntermediate, HandleExisting
from .load_data import load_data
from .postprocess import run_postprocess
from .preprocess import run_preprocessing
from .sort import run_sorting


def run_full_pipeline(
    base_path: Union[Path, str],
    sub_name: str,
    sessions_and_runs: Dict[str, List[str]],
    config_name: str = "default",
    sorter: str = "kilosort2_5",
    concat_sessions_for_sorting: bool = False,
    concat_runs_for_sorting: bool = False,
    existing_preprocessed_data: HandleExisting = "fail_if_exists",
    existing_sorting_output: HandleExisting = "fail_if_exists",
    overwrite_postprocessing: bool = False,
    delete_intermediate_files: DeleteIntermediate = ("recording.dat",),
    slurm_batch: Union[bool, Dict] = False,
):
    """ """
    # TOOD: refactor and handle argument groups separately.
    # Avoid duplication with logging.
    passed_arguments = locals()
    validate.check_function_arguments(passed_arguments)

    if slurm_batch:
        slurm.run_in_slurm(
            slurm_batch,
            _run_full_pipeline,
            {
                "base_path": base_path,
                "sub_name": sub_name,
                "sessions_and_runs": sessions_and_runs,
                "config_name": config_name,
                "sorter": sorter,
                "concat_sessions_for_sorting": concat_sessions_for_sorting,
                "concat_runs_for_sorting": concat_runs_for_sorting,
                "existing_preprocessed_data": existing_preprocessed_data,
                "existing_sorting_output": existing_sorting_output,
                "overwrite_postprocessing": overwrite_postprocessing,
                "delete_intermediate_files": delete_intermediate_files,
                "slurm_batch": slurm_batch,
            },
        ),
    else:
        return _run_full_pipeline(
            base_path,
            sub_name,
            sessions_and_runs,
            config_name,
            sorter,
            concat_sessions_for_sorting,
            concat_runs_for_sorting,
            existing_preprocessed_data,
            existing_sorting_output,
            overwrite_postprocessing,
            delete_intermediate_files,
            slurm_batch,
        )


def _run_full_pipeline(
    base_path: Union[Path, str],
    sub_name: str,
    sessions_and_runs: Dict[str, List[str]],
    config_name: str = "default",
    sorter: str = "kilosort2_5",
    concat_sessions_for_sorting: bool = False,
    concat_runs_for_sorting: bool = False,
    existing_preprocessed_data: HandleExisting = "fail_if_exists",
    existing_sorting_output: HandleExisting = "fail_if_exists",
    overwrite_postprocessing: bool = False,
    delete_intermediate_files: DeleteIntermediate = ("recording.dat",),
    slurm_batch: Union[bool, Dict] = False,
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

    sessions_and_runs : Dict[str, Union[str, List]]
        A dictionary containing the sessions and runs to run through the pipeline.
        Each session should be a session-level folder name residing in the passed
        `sub_name` folder. Each session to run is a key in the
        `sessions_and_runs` dict.
        For each session key, the value can be a single run name (str)
        or a list of run names. The runs will be processed in the
        order passed.

    config_name : str
        The name of the configuration to use. Note this must be the name
        of a .yaml file (not including the extension) stored in
        spikewrap/configs.

    sorter : str
        name of the sorter to use e.g. "kilosort2_5".

    concat_sessions_for_sorting: bool
        If `True`, preprocessed sessions are concatenated after preprocessing
        and before sorting. `concat_runs_for_sorting` must be `True`, as first
        all runs-per session are concatenated, and then all sessions are concatenated.

    concat_runs_for_sorting : bool
        If `True`, the runs for each session are concatenated, in the order
        they are passed in the `sessions_and_runs` dictionary.

    existing_preprocessed_data : custom_types.HandleExisting
        Determines how existing preprocessed data (e.g. from a prior pipeline run)
        is handled.
            "overwrite" : Will overwrite any existing preprocessed data output.
                          This will delete the 'preprocessed' folder. Therefore,
                          never save derivative work there.
            "skip_if_exists" : will search for existing data and skip preprocesing
                               if it exists (sorting will run on existing
                               preprocessed data).
                               Otherwise, will preprocess and save the current run.
            "fail_if_exists" : If existing preprocessed data is found, an error
                               will be raised.

    existing_sorting_output : bool
        Determines how existing sorted data is treated. The same behaviour
        as `existing_preprocessed_data` but for sorting output. If "overwrite",
        the 'sorting' folder will be deleted. Therefore, never save
        derivative work there.

    overwrite_postprocessing : bool
        If `False`, an error will be raised if postprocessing output already
        exists. Otherwise, 'postprocessing' folder will be overwritten. Note,
        that the entire 'postprocessing' folder (including all contents) will be
        deleted. Therefore, never save derivative work there.

    delete_intermediate_files : DeleteIntermediate
        Specify intermediate files or folders to delete. This option is useful for
        reducing the size of output data by deleting unneeded files.

        recording.dat - SpikeInterfaces copies the preprocessed data to folder
                        prior to sorting, where it resides in the 'sorter_output'
                        folder. Often, this can be deleted after sorting.
        temp_wh.dat - Kilosort output file that holds the data preprocessed by
                      Kilosort (e.g. drift correction). By default, this is used
                      for visualisation in Phy.
        waveforms - The waveform outputs that SpikeInterface generates to calculate
                    quality metrics. Often, these can be deleted once final quality
                    metrics are computed.

    slurm_batch : Union[bool, Dict]
        If True, the pipeline will be run in a SLURM job. Set False
        if running on an interactive job, or locally. By default,
        slurm is run with the option set in configs/backend/hpc.py.
        To overwrite, pass a dict of submitit key-value pairs to
        overwrite the default options. Note that only the passed
        options will be overwritten, all other defaults will be
        maintained if not explicitly overwritten.

        Importantly, if the environment you are running the slurm job
        in is not called `spikewrap`, you will need to pass the name of the
        conda environment you want to run the job in, as an option
        in the dictionary e.g. `slurm_batch={"env_name": "my_env_name"}`.
    """
    passed_arguments = locals()
    validate.check_function_arguments(passed_arguments)

    pp_steps, sorter_options, waveform_options = get_configs(config_name)

    logs = logging_sw.get_started_logger(
        utils.get_logging_path(base_path, sub_name),
        "full_pipeline",
    )
    utils.show_passed_arguments(passed_arguments, "`run_full pipeline`")

    loaded_data = load_data(
        base_path, sub_name, sessions_and_runs, data_format="spikeglx"
    )

    run_preprocessing(
        loaded_data,
        config_name,
        existing_preprocessed_data,
        slurm_batch=False,
        log=True,
    )  # TODO: use config_name for all funcs.

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
