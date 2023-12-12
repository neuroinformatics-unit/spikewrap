from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Dict, Optional, Union

if TYPE_CHECKING:
    from pathlib import Path

    from spikewrap.utils.custom_types import HandleExisting

import pandas as pd
import spikeinterface as si

from spikewrap.configs.configs import get_configs
from spikewrap.data_classes.postprocessing import PostprocessingData
from spikewrap.utils import logging_sw, utils, validate

if TYPE_CHECKING:
    from spikeinterface import WaveformExtractor

# --------------------------------------------------------------------------------------
# Run Postprocessing
# --------------------------------------------------------------------------------------


def run_postprocess(
    sorting_path: Union[Path, str],
    overwrite_postprocessing: bool = False,
    existing_waveform_data: HandleExisting = "fail_if_exists",
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
        Determines how existing waveforms (e.g. from a prior pipeline run) are treated.
            "overwrite" : will overwrite any existing waveforms.
            "skip_if_exists" : will search for existing waveforms and compute postprocessing on
                               these if they exist. Otherwise, will use the waveforms from the
                               current run.
            "fail_if_exists" : If existing preprocessed data is found, an error
                               will be raised.

    waveform_options: Dict
        A dictionary containing options passed to SpikeInterface's
        `extract_waveforms()` function as kwargs.
    """
    passed_arguments = locals()
    validate.check_function_arguments(passed_arguments)

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
    save_quality_metrics(waveforms, postprocess_data.get_quality_metrics_path())

    save_unit_locations(waveforms, postprocess_data.get_unit_locations_path())

    logs.stop_logging()

    return postprocess_data


# Sorting Loader -----------------------------------------------------------------------


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

    if postprocessing_path.is_dir() and existing_waveform_data == "skip_if_exists":
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
        waveforms, outputs="by_unit", method="monopolar_triangulation"
    )
    unit_locations_pandas = pd.DataFrame.from_dict(
        unit_locations, orient="index", columns=["x", "y", "z"]
    )
    unit_locations_pandas.to_csv(unit_locations_path)

    utils.message_user(f"Unit locations saved to {unit_locations_path}")
