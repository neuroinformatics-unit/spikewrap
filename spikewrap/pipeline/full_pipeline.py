from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from pathlib import Path

    from spikewrap.data_classes.preprocessing import PreprocessingData
    from spikewrap.data_classes.sorting import SortingData
    from spikewrap.utils.custom_types import DeleteIntermediate, HandleExisting

from spikewrap.configs.configs import get_configs
from spikewrap.pipeline.load_data import load_data
from spikewrap.pipeline.postprocess import run_postprocess
from spikewrap.pipeline.preprocess import run_preprocessing
from spikewrap.pipeline.sort import run_sorting
from spikewrap.utils import logging_sw, slurm, utils, validate


def run_full_pipeline(
    base_path: Union[Path, str],
    sub_name: str,
    sessions_and_runs: Dict[str, List[str]],
    data_format,
    config_name: str = "default",
    sorter: str = "kilosort2_5",
    preprocess_by_group: bool = False,
    sort_by_group: bool = False,
    concat_sessions_for_sorting: bool = False,
    concat_runs_for_sorting: bool = False,
    existing_preprocessed_data: HandleExisting = "fail_if_exists",
    existing_sorting_output: HandleExisting = "fail_if_exists",
    save_preprocessing_chunk_size: Optional[int] = None,
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
                "data_format": data_format,
                "config_name": config_name,
                "sorter": sorter,
                "preprocess_by_group": preprocess_by_group,
                "sort_by_group": sort_by_group,
                "concat_sessions_for_sorting": concat_sessions_for_sorting,
                "concat_runs_for_sorting": concat_runs_for_sorting,
                "existing_preprocessed_data": existing_preprocessed_data,
                "existing_sorting_output": existing_sorting_output,
                "save_preprocessing_chunk_size": save_preprocessing_chunk_size,
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
            data_format,
            config_name,
            sorter,
            preprocess_by_group,
            sort_by_group,
            concat_sessions_for_sorting,
            concat_runs_for_sorting,
            existing_preprocessed_data,
            existing_sorting_output,
            save_preprocessing_chunk_size,
            overwrite_postprocessing,
            delete_intermediate_files,
            slurm_batch,
        )


def _run_full_pipeline(
    base_path: Union[Path, str],
    sub_name: str,
    sessions_and_runs: Dict[str, List[str]],
    data_format: str,
    config_name: str = "default",
    sorter: str = "kilosort2_5",
    preprocess_by_group: bool = False,
    sort_by_group: bool = False,
    concat_sessions_for_sorting: bool = False,
    concat_runs_for_sorting: bool = False,
    existing_preprocessed_data: HandleExisting = "fail_if_exists",
    existing_sorting_output: HandleExisting = "fail_if_exists",
    save_preprocessing_chunk_size: Optional[int] = None,
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
        base_path,
        sub_name,
        sessions_and_runs,
        data_format=data_format,
    )

    run_preprocessing(
        loaded_data,
        config_name,
        existing_preprocessed_data,
        chunk_size=save_preprocessing_chunk_size,
        preprocess_by_group=preprocess_by_group,
        slurm_batch=False,
        log=True,
    )  # TODO: use config_name for all funcs.

    sorting_data = run_sorting(
        base_path,
        sub_name,
        sessions_and_runs,
        sorter,
        sort_by_group,
        concat_sessions_for_sorting,
        concat_runs_for_sorting,
        sorter_options,
        existing_sorting_output,
    )
    assert sorting_data is not None

    # Run Postprocessing
    for ses_name, run_name in sorting_data.get_sorting_sessions_and_runs():
        for sorting_path in _get_sorting_paths(
            sorting_data, ses_name, run_name, sort_by_group
        ):
            postprocess_data = run_postprocess(
                sorting_path,
                overwrite_postprocessing=overwrite_postprocessing,
                existing_waveform_data="fail_if_exists",
                waveform_options=waveform_options,
            )

    # Delete intermediate files
    for ses_name, run_name in sorting_data.get_sorting_sessions_and_runs():
        for sorting_path in _get_sorting_paths(
            sorting_data, ses_name, run_name, sort_by_group
        ):
            postprocessing_path = utils.make_postprocessing_path(sorting_path)

            handle_delete_intermediate_files(
                sorting_path, postprocessing_path, delete_intermediate_files
            )
    logs.stop_logging()

    return (
        loaded_data,
        sorting_data,
    )


def _get_sorting_paths(
    sorting_data: SortingData, ses_name: str, run_name: str, sort_by_group: bool
) -> List[Path]:
    """ """
    if sort_by_group:
        all_group_paths = sorting_data.get_base_sorting_path(ses_name, run_name).glob(
            "group-*"
        )
        group_indexes = [
            int(group.name.split("group-")[1])
            for group in all_group_paths
            if group.is_dir()
        ]  # TODO: kind of hacky
        all_sorting_paths = [
            sorting_data.get_sorting_path(ses_name, run_name, idx)
            for idx in group_indexes
        ]
    else:
        all_sorting_paths = [sorting_data.get_sorting_path(ses_name, run_name)]

    return all_sorting_paths


# --------------------------------------------------------------------------------------
# Remove Intermediate Files
# --------------------------------------------------------------------------------------


def handle_delete_intermediate_files(
    sorting_path: Path,
    postprocessing_path: Path,
    delete_intermediate_files: DeleteIntermediate,
):
    """
    Handle the cleanup of intermediate files created during sorting and
    postprocessing. Some of these files are sorter-specific (e.g. `temp_wh.dat`
    for Kilosort). See `run_full_pipeline` for inputs
    """
    if "recording.dat" in delete_intermediate_files:
        if (recording_file := sorting_path / "recording.dat").is_file():
            recording_file.unlink()

    if "temp_wh.dat" in delete_intermediate_files:
        if (recording_file := sorting_path / "temp_wh.dat").is_file():
            recording_file.unlink()

    if "waveforms" in delete_intermediate_files:
        if (waveforms_path := postprocessing_path / "waveforms").is_dir():
            shutil.rmtree(waveforms_path)
