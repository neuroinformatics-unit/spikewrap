from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Literal, Optional, Union

import pandas as pd
import spikeinterface as si

from ..configs.configs import get_configs
from ..data_classes.postprocessing import PostprocessingData
from ..utils import logging_sw, utils
from ..utils.custom_types import HandleExisting

if TYPE_CHECKING:
    from spikeinterface import WaveformExtractor

# --------------------------------------------------------------------------------------
# Run Postprocessing
# --------------------------------------------------------------------------------------


def run_postprocess(
    sorting_path: Union[Path, str],
    overwrite_postprocessing: bool = False,
    existing_waveform_data: HandleExisting = "fail_if_exists",
    postprocessing_to_run: Union[Literal["all"], Dict] = "all",
    waveform_options: Optional[Dict] = None,
) -> PostprocessingData:
    """
    Run post-processing, including quality metrics on sorting
    output and the unit positions on the electrode.

    Parameters
    ----------

    sorting_path : Union[Path, str, SortingData]
        The path to the sorting output, the 'sorting' folder that
        resides in the folder with a sorter-name (e.g. kilosort2_5).

    overwrite_postprocessing: bool
        If `True`, existing postprocessing is deleted in it's entirely. Otherwise
        if `False` and postprocesing already exists, an error will be raised.

    existing_waveform_data : custom_types.HandleExisting
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

    postprocessing_to_run : Union[Literal["all"], Dict]
        Specify the postprocessing to run. By default, "all" will run
        all available postprocessing. Otherwise, provide a dict of
        including postprocessing to run e.g. {"quality_metrics: True"}.
        Accepted keys are "quality_metrics" and "unit_locations".

    waveform_options: Dict
        A dictionary containing options passed to SpikeInterface's
        `extract_waveforms()` function as kwargs.
    """
    passed_arguments = locals()

    postprocess_data = PostprocessingData(sorting_path)

    logs = logging_sw.get_started_logger(
        utils.get_logging_path(
            postprocess_data.sorting_info["base_path"],
            postprocess_data.sorting_info["sub_name"],
        ),
        "postprocess",
    )
    utils.show_passed_arguments(passed_arguments, "`run_postprocess`")

    utils.message_user(f"Postprocessing run: {postprocess_data.sorted_run_name}...")

    handle_delete_existing_postprocessing(
        postprocess_data.get_postprocessing_path(),
        overwrite_postprocessing,
    )

    # Create / load waveforms
    if waveform_options is None:
        _, _, waveform_options = get_configs("default")

    waveforms = run_or_get_waveforms(
        postprocess_data, existing_waveform_data, waveform_options
    )

    # Perform postprocessing
    run_settings = handle_postprocessing_to_run(postprocessing_to_run)

    if run_option(run_settings, "quality_metrics"):
        save_quality_metrics(waveforms, postprocess_data.get_quality_metrics_path())

    if run_option(run_settings, "unit_locations"):
        save_unit_locations(waveforms, postprocess_data.get_unit_locations_path())

    logs.stop_logging()

    return postprocess_data


# Sorting Loader -----------------------------------------------------------------------


def run_option(run_settings: Dict, option: str) -> bool:
    """
    When to run the option that may either not be in the dict
    (do not run) or is in the dict and set `False`.
    TODO: just use a Tuple instead.
    """
    return option in run_settings and run_settings[option]


def run_or_get_waveforms(
    postprocess_data: PostprocessingData,
    existing_waveform_data: HandleExisting,
    waveform_options: Dict,
) -> WaveformExtractor:
    """
    How to handle existing waveform output, either load, fail if exists or
    overwrite.
    """
    postprocessing_path = postprocess_data.get_postprocessing_path()

    if postprocessing_path.is_dir() and existing_waveform_data == "load_if_exists":
        utils.message_user(
            f"Loading existing waveforms from: " f"{postprocessing_path}",
        )
        waveforms = si.load_waveforms(postprocessing_path)

    elif postprocessing_path.is_dir() and existing_waveform_data == "fail_if_exists":
        raise RuntimeError(
            f"Waveforms exist at {postprocessing_path} but "
            f"`existing_waveform_data` is 'fail_if_exists'."
        )
    else:
        utils.message_user(f"Saving waveforms to {postprocessing_path}")

        waveforms = si.extract_waveforms(
            postprocess_data.preprocessed_recording,
            postprocess_data.sorting_output,
            folder=postprocessing_path,
            use_relative_path=True,
            overwrite=True,
            **waveform_options,
        )

    return waveforms


def handle_postprocessing_to_run(
    postprocessing_to_run: Union[Literal["all"], Dict]
) -> Dict:
    """
    Set to run all postprocessing steps. If user-dict is provided,
    ensure it contains expected keys / values.
    """
    run_settings = {
        "quality_metrics": True,
        "unit_locations": True,
    }

    if postprocessing_to_run == "all":
        return run_settings
    else:
        assert isinstance(postprocessing_to_run, Dict)
        assert all(
            [key in run_settings.keys() for key in postprocessing_to_run.keys()]
        ), (
            f"At least one option in `postprocessing_to_run` is invalid. Must be"
            f"one of {run_settings.keys()}"
        )
        assert all(
            [isinstance(value, bool) for value in postprocessing_to_run.values()]
        ), "`postprocessing_to_run` values must be `True` or `False`."

        run_settings = postprocessing_to_run

        return run_settings


def handle_delete_existing_postprocessing(
    postprocessing_path: Path, overwrite_postprocessing: bool
) -> None:
    """
    If previous postprocessing output exists, it must be deleted before
    the new postprocessing is run. As a safety measure, `overwrite_postprocessing`
    must be set to `True` to perform the deletion.
    """
    if postprocessing_path.is_dir():
        if overwrite_postprocessing:
            utils.message_user(
                f"Deleting existing postprocessing " f"output at {postprocessing_path}"
            )
            shutil.rmtree(postprocessing_path)
        else:
            raise RuntimeError(
                f"Postprocessing output already exists at "
                f"{postprocessing_path} "
                f"but `overwrite_postprocessing` is `False`. Setting "
                f"`overwrite_postprocessing` will delete the postprocessing "
                f"folder and all it's contents."
            )


# Helpers ------------------------------------------------------------------------------


def save_quality_metrics(
    waveforms: WaveformExtractor, quality_metrics_path: Path
) -> None:
    """"""
    quality_metrics = si.qualitymetrics.compute_quality_metrics(waveforms)
    quality_metrics.to_csv(quality_metrics_path)
    utils.message_user(f"Quality metrics saved to {quality_metrics_path}")


def save_unit_locations(
    waveforms: WaveformExtractor, unit_locations_path: Path
) -> None:
    """"""
    unit_locations = si.postprocessing.compute_unit_locations(
        waveforms, outputs="by_unit"
    )
    unit_locations_pandas = pd.DataFrame.from_dict(
        unit_locations, orient="index", columns=["x", "y"]
    )
    unit_locations_pandas.to_csv(unit_locations_path)

    utils.message_user(f"Unit locations saved to {unit_locations_path}")
