from __future__ import annotations

import time
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Literal, Optional, Union

import matplotlib.pyplot as plt
import numpy
import numpy as np
import pandas as pd
import spikeinterface as si
from spikeinterface import curation
from spikeinterface.extractors import NpzSortingExtractor

from ..configs.configs import get_configs
from ..data_classes.sorting import SortingData
from ..pipeline.load_data import load_data_for_sorting
from ..utils import logging_sw, utils
from ..utils.custom_types import HandleExisting
from .waveform_compare import get_waveform_similarity

if TYPE_CHECKING:
    from spikeinterface import WaveformExtractor
    from spikeinterface.core import BaseSorting

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
    sorting_data: Union[Path, str, SortingData],
    sorter: str,
    existing_waveform_data: HandleExisting = "load_if_exists",
    postprocessing_to_run: Union[Literal["all"], Dict] = "all",
    verbose: bool = True,
    waveform_options: Optional[Dict] = None,
) -> None:
    """
    Run post-processing, including ave quality metrics on sorting
    output to a quality_metrics.csv file.

    Parameters
    ----------

    sorting_data : Union[Path, str, SortingData]
        The path to the 'preprocessed' folder in the subject / run
        folder used for sorting or a SortingData object. If a

        SortingData object, the path will be read from the
        `preprocessed_data_path` attribute.

    sorter : str
        The name of the sorter (e.g. "kilosort2_5").

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
    if not isinstance(sorting_data, SortingData):
        sorting_data = load_data_for_sorting(
            Path(sorting_data),
        )
    assert isinstance(sorting_data, SortingData), "type narrow `sorting_data`."

    logs = logging_sw.get_started_logger(sorting_data.logging_path, "postprocess")

    # Create / load waveforms
    if waveform_options is None:
        _, _, waveform_options = get_configs("default")

    sorting_data.set_sorter_output_paths(sorter)

    utils.message_user(
        f"Quality Checks: sorting path used: {sorting_data.sorter_run_output_path}",
        verbose,
    )

    waveforms = run_or_get_waveforms(
        sorting_data, existing_waveform_data, waveform_options, sorter, verbose
    )

    # Perform postprocessing
    run_settings = handle_postprocessing_to_run(postprocessing_to_run)

    if run_option(run_settings, "quality_metrics"):
        save_quality_matrics(waveforms, sorting_data)

    if run_option(run_settings, "unit_locations"):
        save_unit_locations(waveforms, sorting_data)

    if run_option(run_settings, "template_plots"):
        save_plots_of_templates(sorting_data.postprocessing_output_path, waveforms)

    if run_option(run_settings, "waveform_similarity"):
        save_waveform_similarities(
            sorting_data.postprocessing_output_path, waveforms, MATRIX_BACKEND
        )

    logs.stop_logging()


# Sorting Loader -----------------------------------------------------------------------


def run_option(run_settings: Dict, option: str):
    return option in run_settings and run_settings[option]


def run_or_get_waveforms(
    sorting_data: SortingData,
    existing_waveform_data: HandleExisting,
    waveform_options: Dict,
    sorter: str,
    verbose: bool,
):
    """
    How to handle existing waveform output, either load, fail if exists or
    overwrite.
    """
    if (
        sorting_data.postprocessing_output_path.is_dir()
        and existing_waveform_data == "load_if_exists"
    ):
        utils.message_user(
            f"Loading existing waveforms from: "
            f"{sorting_data.postprocessing_output_path}",
            verbose,
        )
        waveforms = si.load_waveforms(sorting_data.postprocessing_output_path)

    elif (
        sorting_data.postprocessing_output_path.is_dir()
        and existing_waveform_data == "fail_if_exists"
    ):
        raise RuntimeError(
            f"Waveforms exist at {sorting_data.postprocessing_output_path} but "
            f"`existing_waveform_data` is 'fail_if_exists'."
        )
    else:
        utils.message_user(
            f"Saving waveforms to {sorting_data.postprocessing_output_path}"
        )

        sorting_without_excess_spikes = load_sorting_output(sorting_data, sorter)

        waveforms = si.extract_waveforms(
            sorting_data.data["0-preprocessed"],
            sorting_without_excess_spikes,
            folder=sorting_data.postprocessing_output_path,
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


def load_sorting_output(sorting_data: SortingData, sorter: str) -> BaseSorting:
    """
    Load the output of a sorting run as a SpikeInterface SortingExtractor
    object.

    It is assumed sorting is performed on concatenated runs. As such,
    only a single sorting segment is expected, and error raised
    if there are more.

    Automatically remove empty units, which complicate downstream
    processing. Also, remove excess spikes, which are caused by
    strange behaviour of KS returning spike times that occur
    outside the number of samples in a recording. This is required
    for waveform extraction in Spikeinterface.

    Parameters
    ----------

    sorting_data : SortingData
        An spikewrap SortingData object holding information about sorting

    sorter : str
        The sorter used (e.g. "kilosort2_5")

    TODO
    ----
    In newer SpikeInterface version, `remove_empty_units()` is automatically
    applied during `KiloSortSortingExtractor()`. We can simply use
    this default rather than applying again here after pinning to newer
    SI version. See  https://github.com/SpikeInterface/spikeinterface/issues/1760
    """
    if not sorting_data.sorter_run_output_path.is_dir():
        raise FileNotFoundError(
            f"{sorter} output was not found at "
            f"{sorting_data.sorter_run_output_path}.\n"
            f"Quality metrics will not be generated."
        )

    assert (
        len(sorting_data) == 1
    ), "unexpected number of entries in `sorting_data` dict."

    recording = sorting_data[sorting_data.init_data_key]

    if "kilosort" in sorter:
        sorting = si.extractors.read_kilosort(
            folder_path=sorting_data.sorter_run_output_path,
            keep_good_only=False,
        )
    elif sorter == "mountainsort5":
        sorting = NpzSortingExtractor(
            (sorting_data.sorter_run_output_path / "firings.npz").as_posix()
        )

    elif sorter == "tridesclous":
        sorting = si.extractors.read_tridesclous(
            folder_path=sorting_data.sorter_run_output_path.as_posix()
        )

    elif sorter == "spykingcircus":
        sorting = si.extractors.read_spykingcircus(
            folder_path=sorting_data.sorter_run_output_path.as_posix()
        )

    sorting = sorting.remove_empty_units()
    sorting_without_excess_spikes = curation.remove_excess_spikes(sorting, recording)

    return sorting_without_excess_spikes


# Helpers ------------------------------------------------------------------------------


def save_quality_matrics(waveforms: WaveformExtractor, sorting_data: SortingData):
    """ """
    quality_metrics = si.qualitymetrics.compute_quality_metrics(waveforms)
    quality_metrics.to_csv(sorting_data.quality_metrics_path)
    utils.message_user(f"Quality metrics saved to {sorting_data.quality_metrics_path}")


def save_unit_locations(waveforms: WaveformExtractor, sorting_data: SortingData):
    """ """
    unit_locations = si.postprocessing.compute_unit_locations(
        waveforms, outputs="by_unit"
    )
    unit_locations_pandas = pd.DataFrame.from_dict(
        unit_locations, orient="index", columns=["x", "y"]
    )
    unit_locations_pandas.to_csv(sorting_data.unit_locations_path)

    utils.message_user(f"Unit locations saved to {sorting_data.unit_locations_path}")


def save_waveform_similarities(
    postprocessing_output_path: Path,
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

    postprocessing_output_path : Path
        Pathlib object holding the output path where waveforms are saved
        and /images will be written.

    waveforms : WaveformExtractor
        Spikeinterface WaveformExtractor object.

    backend : Literal["jax", "numpy"]
        The backend with which to run waveform comparisons. Jax is around 50
        times faster in this case.
    """
    utils.message_user("Saving waveform similarity matrices...\n")

    matrices_out_path = postprocessing_output_path / "similarity_matrices"
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


# --------------------------------------------------------------------------------------
# Save imagines
# --------------------------------------------------------------------------------------


def save_plots_of_templates(
    postprocessing_output_path: Path, waveforms: WaveformExtractor
):
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

    postprocessing_output_path : Path
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

        output_folder = postprocessing_output_path / "template_plots"
        output_folder.mkdir(exist_ok=True)
        plt.savefig(
            postprocessing_output_path / "template_plots" / f"unit_{unit_id}.png"
        )
        plt.clf()

    utils.message_user(f"Saving plots of templates took: {time.perf_counter() - t}")
