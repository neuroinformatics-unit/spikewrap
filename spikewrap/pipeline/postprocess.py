from __future__ import annotations

import shutil
import time
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Literal, Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import spikeinterface as si

from ..configs.configs import get_configs
from ..data_classes.postprocessing import PostprocessingData
from ..utils import logging_sw, utils
from ..utils.custom_types import HandleExisting
from .waveform_compare import get_waveform_similarity

if TYPE_CHECKING:
    from spikeinterface import WaveformExtractor

MATRIX_BACKEND: Literal["numpy", "jax"]
try:
    MATRIX_BACKEND = "jax"
except ImportError:
    warnings.warn(
        "The module Jax was not found. Waveform similarity matrix calculation"
        "will be very slow. Use `pip install jax jaxlib` to install."
    )
    MATRIX_BACKEND = "numpy"


# --------------------------------------------------------------------------------------
# Run Postprocessing
# --------------------------------------------------------------------------------------


def run_postprocess(
    sorting_path: Union[Path, str],
    overwrite_postprocessing: bool = False,
    existing_waveform_data: HandleExisting = "load_if_exists",
    postprocessing_to_run: Union[Literal["all"], Dict] = "all",
    verbose: bool = True,
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

    existing_waveform_data : Literal["overwrite", "load_if_exists", "fail_if_exists"]
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

    verbose : bool
        If True, messages will be printed to console updating on the
        progress of preprocessing / sorting.

    waveform_options: Dict
        A dictionary containing options passed to SpikeInterface's
        `extract_waveforms()` function as kwargs.
    """
    postprocess_data = PostprocessingData(sorting_path)

    logs = logging_sw.get_started_logger(
        utils.get_logging_path(
            postprocess_data.sorting_info["base_path"],
            postprocess_data.sorting_info["sub_name"],
        ),
        "full_pipeline",
    )

    utils.message_user(f"Postprocessing run: {postprocess_data.sorted_run_name}...")

    handle_delete_existing_postprocessing(
        postprocess_data.get_postprocessing_path(),
        overwrite_postprocessing,
    )

    # Create / load waveforms
    if waveform_options is None:
        _, _, waveform_options = get_configs("default")

    waveforms = run_or_get_waveforms(
        postprocess_data, existing_waveform_data, waveform_options, verbose
    )

    # Perform postprocessing
    run_settings = handle_postprocessing_to_run(postprocessing_to_run)

    if run_option(run_settings, "quality_metrics"):
        save_quality_metrics(waveforms, postprocess_data.get_quality_metrics_path())

    if run_option(run_settings, "unit_locations"):
        save_unit_locations(waveforms, postprocess_data.get_unit_locations_path())

    logs.stop_logging()

    return postprocess_data


# Remove these!
#    if run_option(run_settings, "template_plots"):
#        save_plots_of_templates(sorting_data.postprocessing_path, waveforms)

#    if run_option(run_settings, "waveform_similarity"):
#        save_waveform_similarities(
#            sorting_data.postprocessing_path, waveforms, MATRIX_BACKEND
#        )

#    logs.stop_logging()

# Sorting Loader -----------------------------------------------------------------------


def run_option(run_settings: Dict, option: str):
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
    verbose: bool,
):
    """
    How to handle existing waveform output, either load, fail if exists or
    overwrite.
    """
    postprocessing_path = postprocess_data.get_postprocessing_path()

    if postprocessing_path.is_dir() and existing_waveform_data == "load_if_exists":
        utils.message_user(
            f"Loading existing waveforms from: " f"{postprocessing_path}",
            verbose,
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


def handle_postprocessing_to_run(postprocessing_to_run: Union[Literal["all"], Dict]):
    """
    Set to run all postprocessing steps. If user-dict is provided,
    ensure it contains expected keys / values.
    """
    run_settings = {
        "quality_metrics": True,
        "unit_locations": True,
        "template_plots": True,
        "waveform_similarity": True,
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
):
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


# --------------------------------------------------------------------------------------
# TODO: remove
# --------------------------------------------------------------------------------------


def save_waveform_similarities(
    postprocessing_path: Path,
    waveforms: WaveformExtractor,
    backend: Literal["jax", "numpy"],
):
    """
    Save waveform similarity matrices as a csv file. This is a
    num_waveform x num_waveform matrix holding the cosine similarity
    between all waveforms for a unit.

    The .csv file will contain header and index for the spike time of
    each row.

    Parameters
    ---------

    postprocessing_path : Path
        Pathlib object holding the output path where waveforms are saved
        and /images will be written.

    waveforms : WaveformExtractor
        Spikeinterface WaveformExtractor object.

    backend : Literal["jax", "numpy"]
        The backend with which to run waveform comparisons. Jax is around 50
        times faster in this case.
    """
    utils.message_user("Saving waveform similarity matrices...\n")

    matrices_out_path = postprocessing_path / "similarity_matrices"
    matrices_out_path.mkdir(exist_ok=True)

    t = time.perf_counter()
    for unit_id in waveforms.sorting.get_unit_ids():
        sim_matrix, spike_times = get_waveform_similarity(waveforms, unit_id, backend)
        sim_matrix_pd = pd.DataFrame(sim_matrix, columns=spike_times, index=spike_times)
        sim_matrix_pd.to_csv(
            matrices_out_path / f"waveform_similarity_unit_{unit_id}.csv"
        )

    utils.message_user(f"Waveform similarity matrices saved to: {matrices_out_path}")
    utils.message_user(
        f"Saving waveform similarity matrices took: {time.perf_counter() - t}"
    )


def save_plots_of_templates(postprocessing_path: Path, waveforms: WaveformExtractor):
    """
    Save a plot of all templates in 'waveforms/images' folder. The plot
    displays the template waveform are calculated in two ways
        1) as the mean over channels (the channels here are defined by the
           sparsity settings during waveform extraction).
        2) as the channel in which the waveform signal is strongest (as
           determined by the channel minimum value).
           TODO: this is  mostly experimental for testing (for visualisation only).

    The purpose of these plots is to provide a quick overview of the
    extract templates. Proper investigations on unit quality should
    be done in Phy.

    Parameters
    ------

    postprocessing_path : Path
        Pathlib object holding the output path where waveforms are saved
        and /images will be written.

    waveforms : WaveformExtractor
        Spikeinterface WaveformExtractor object.

    """
    t = time.perf_counter()
    utils.message_user("Saving template images...\n")

    fs = waveforms.sampling_frequency
    n_samples = waveforms.nsamples
    time_ = np.arange(n_samples) / fs * 1000

    y_label = "Voltage (uV)" if waveforms.return_scaled else "Voltage (unscaled)"

    for idx, unit_id in enumerate(waveforms.sorting.get_unit_ids()):
        unit_template = waveforms.get_template(unit_id)
        plt.plot(time_, np.mean(unit_template, axis=1))

        peak_chan_idx = np.argmin(np.min(unit_template, axis=0))
        plt.plot(time_, unit_template[:, peak_chan_idx])

        plt.legend(["mean across channels", "max signal channel"])
        plt.xlabel("Time (ms)")
        plt.ylabel(y_label)
        plt.title(f"Unit {unit_id} Template")

        output_folder = postprocessing_path / "template_plots"
        output_folder.mkdir(exist_ok=True)
        plt.savefig(postprocessing_path / "template_plots" / f"unit_{unit_id}.png")
        plt.clf()

    utils.message_user(f"Saving plots of templates took: {time.perf_counter() - t}")
