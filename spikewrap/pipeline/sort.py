from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union

import spikeinterface.sorters as ss

from ..data_classes.sorting import (
    ConcatenateRuns,
    ConcatenateSessions,
    NoConcatenation,
    SortingData,
)
from ..utils import logging_sw, slurm, utils, validate
from ..utils.custom_types import HandleExisting
from ..utils.managing_images import (
    get_image_run_settings,
    move_singularity_image_if_required,
)


def run_sorting(
    base_path: Union[str, Path],
    sub_name: str,
    sessions_and_runs: Dict[str, List[str]],
    sorter: str,
    concatenate_sessions: bool = False,
    concatenate_runs: bool = False,
    sorter_options: Optional[Dict] = None,
    existing_sorting_output: HandleExisting = "fail_if_exists",
    slurm_batch: Union[bool, Dict] = False,
):
    # TOOD: refactor and handle argument groups separately.
    # Avoid duplication with logging.
    passed_arguments = locals()
    validate.check_function_arguments(passed_arguments)

    if slurm_batch:
        slurm.run_in_slurm(
            slurm_batch,
            _run_sorting,
            {
                "base_path": base_path,
                "sub_name": sub_name,
                "sessions_and_runs": sessions_and_runs,
                "concatenate_sessions": concatenate_sessions,
                "concatenate_runs": concatenate_runs,
                "sorter_options": sorter_options,
                "existing_sorting_output": existing_sorting_output,
                "slurm_batch": slurm_batch,
            },
        ),
    else:
        return _run_sorting(
            base_path,
            sub_name,
            sessions_and_runs,
            sorter,
            concatenate_sessions,
            concatenate_runs,
            sorter_options,
            existing_sorting_output,
            slurm_batch,
        )


def _run_sorting(
    base_path: Union[str, Path],
    sub_name: str,
    sessions_and_runs: Dict[str, List[str]],
    sorter: str,
    concatenate_sessions: bool = False,
    concatenate_runs: bool = False,
    sorter_options: Optional[Dict] = None,
    existing_sorting_output: HandleExisting = "fail_if_exists",
    slurm_batch: Union[bool, Dict] = False,
) -> Optional[SortingData]:
    """
    Run a sorter on pre-processed data. Takes a PreprocessingData (pipeline.data_class)
    object that contains spikeinterface recording objects for the preprocessing
    pipeline (or path to existing 'preprocessed' output folder).

    Here, save the preprocessed recording to binary file. Then, run sorting
    on the saved binary. The preprocessed binary and sorting output are
    saved in a 'derivatives' folder, in the same top-level folder as 'rawdata'.
    The folder structure will be the same as in 'rawdata'.

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

    sorter : str
        Name of the sorter to use (e.g. "kilosort2_5").

    concatenate_sessions: bool
        If `True`, preprocessed sessions are concatenated before sorting. If `True`,
        `concat_runs_for_sorting` must be `True`, as first all runs-per session are
        concatenated, and then all sessions are concatenated.

    concatenate_runs : bool
        If `True`, the runs for each session are concatenated, in the order
        they are passed in the `sessions_and_runs` dictionary.

    sorter_options : Optional[Dict]
        Kwargs to pass to spikeinterface sorter class.

    existing_sorting_output : custom_types.HandleExisting
        Determines how existing sorting output (e.g. from a prior pipeline run)
        is handled.
            "overwrite" : will overwrite any existing sorting output. This will
                          delete the 'sorting' folder. Therefore, never save
                          derivative work there.
            "skip_if_exists" : will search for existing sorting output and load if it exists.
                               Otherwise, will perform sorting.
            "fail_if_exists" : If existing sorting output is found, an error
                               will be raised.

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

    if sorter == "mountainsort5" and platform.system() == "Darwin":
        raise EnvironmentError("Mountainsort is not currently supported on macOS.")

    logs = logging_sw.get_started_logger(
        utils.get_logging_path(base_path, sub_name),
        "sorting",
    )
    utils.show_passed_arguments(passed_arguments, "`run_sorting`")

    SortingDataClass = get_sorting_data_class(concatenate_sessions, concatenate_runs)

    sorting_data = SortingDataClass(
        Path(base_path), sub_name, sessions_and_runs, sorter
    )

    sorter_options_dict = get_sorter_options_dict(sorter_options, sorter)

    # This must be run from the folder that has both sorter output AND rawdata
    os.chdir(sorting_data.base_path)

    singularity_image, docker_image = get_image_run_settings(sorter)

    if "kilosort" in sorter:
        sorter_options_dict.update(
            {"delete_tmp_files": False, "delete_recording_dat": False}
        )

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


def get_sorter_options_dict(sorter_options: Optional[Dict], sorter: str) -> Dict:
    """"""
    sorter_options_dict = {}
    if sorter_options is not None and sorter in sorter_options:
        sorter_options_dict = sorter_options[sorter]

    sorter_options_dict.update({"verbose": True})

    return sorter_options_dict


def get_sorting_data_class(
    concatenate_sessions: bool, concatenate_runs: bool
) -> Union[type[ConcatenateSessions], type[ConcatenateRuns], type[NoConcatenation]]:
    """"""
    if concatenate_sessions and not concatenate_runs:
        raise ValueError(
            "`concatenate_runs` must be `True` if `concatenate_sessions` is `True`"
        )

    if concatenate_sessions:
        return ConcatenateSessions
    else:
        if concatenate_runs:
            return ConcatenateRuns
        else:
            return NoConcatenation


def run_sorting_on_all_runs(
    sorting_data: SortingData,
    singularity_image: Union[Literal[True], None, str],
    docker_image: Optional[Literal[True]],
    existing_sorting_output: HandleExisting,
    **sorter_options_dict,
) -> None:
    """
    Run the sorting data for each run. If the data is concatenated
    prior to sorting, the `run_name` will be `None` (this is handled
    under the hood by `sorting_data`). Otherwise, run_names
    will be the names of the individually sorted runs.

    Parameters:

    sorting_data: SortingData
        Spikewrap SortingData object.

    singularity_image: Union[True, None, str]
        If True, image is saved locally by SI. If False, docker is not used.
        If str, must be a path to a singularity image to be used.
        Note must be `False` if docker image is `True`.

    docker_image: bool
        If `True`, docker is used otherwise it is not used. No path
        option is given as docker images are managed with Docker Desktop.
        Note must be `False` if singularity image is `True` or a Path.

    existing_sorting_output: see `run_sorter()`

    sorter_options_dict: Dict
        List of kwargs passed to SI's `run_sorter`.
    """
    utils.message_user(f"Starting {sorting_data.sorter} sorting...")

    for ses_name, run_name in sorting_data.get_sorting_sessions_and_runs():
        sorting_output_path = sorting_data.get_sorting_path(ses_name, run_name)
        preprocessed_recording = sorting_data.get_preprocessed_recordings(
            ses_name, run_name
        )

        utils.message_user(
            f"Sorting session: {ses_name} \n"
            f"run: {ses_name}..."
            # TODO: I think can just use run_name now?
        )

        if sorting_output_path.is_dir():
            if existing_sorting_output == "fail_if_exists":
                raise RuntimeError(
                    f"Sorting output already exists at {sorting_output_path} and"
                    f"`existing_sorting_output` is set to 'fail_if_exists'."
                )

            elif existing_sorting_output == "skip_if_exists":
                utils.message_user(
                    f"Sorting output already exists at {sorting_output_path}. Nothing "
                    f"will be done. The existing sorting will be used for "
                    f"postprocessing "
                    f"if running with `run_full_pipeline`"
                )
                continue

            quick_safety_check(existing_sorting_output, sorting_output_path)

        ss.run_sorter(
            sorting_data.sorter,
            preprocessed_recording,
            output_folder=sorting_output_path,
            singularity_image=singularity_image,
            docker_image=docker_image,
            remove_existing_folder=True,
            **sorter_options_dict,
        )

        sorting_data.save_sorting_info(ses_name, run_name)


def quick_safety_check(
    existing_sorting_output: HandleExisting, output_path: Path
) -> None:
    """
     In this case, either output path does not exist, or it does
     and `existing_sorter_output` is "overwrite"

    TODO: delete after some testing
    """
    assert existing_sorting_output != "fail_if_exists"
    if existing_sorting_output == "skip_if_exists":
        assert not output_path.is_dir()
