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
from spikeinterface.core import compute_sparsity
from spikeinterface.extractors import KiloSortSortingExtractor

from ..configs.configs import get_configs
from ..data_classes.sorting import SortingData
from ..pipeline.load_data import load_data_for_sorting
from ..utils import utils
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
    sorter: str = "kilosort2_5",
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

    # Create / load waveforms
    if waveform_options is None:
        _, _, waveform_options = get_configs("test")

    sorting_data.set_sorter_output_paths(sorter)

    utils.message_user(
        f"Quality Checks: sorting path used: {sorting_data.sorter_run_output_path}",
        verbose,
    )

    if not sorting_data.waveforms_output_path.is_dir():
        utils.message_user(f"Saving waveforms to {sorting_data.waveforms_output_path}")

        sorting_without_excess_spikes = load_sorting_output(sorting_data, sorter)

        waveforms = si.extract_waveforms(
            sorting_data.data["0-preprocessed"],
            sorting_without_excess_spikes,
            folder=sorting_data.waveforms_output_path,
            use_relative_path=True,
            **waveform_options,
        )
    else:
        utils.message_user(
            f"Loading existing waveforms from: {sorting_data.waveforms_output_path}",
            verbose,
        )
        waveforms = si.load_waveforms(sorting_data.waveforms_output_path)

    save_plots_of_templates(sorting_data.waveforms_output_path, waveforms)

    # Perform postprocessing
    save_quality_matrics(waveforms, sorting_data)
    save_unit_locations(waveforms, sorting_data)
    save_waveform_similarities(
        sorting_data.waveforms_output_path, waveforms, MATRIX_BACKEND
    )


# Sorting Loader -----------------------------------------------------------------------


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
        An swc_ephys SortingData object holding information about sorting

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

    sorting = KiloSortSortingExtractor(
        folder_path=sorting_data.sorter_run_output_path,
        keep_good_only=False,
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
    waveforms_output_path: Path,
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

    waveforms_output_path : Path
        Pathlib object holding the output path where waveforms are saved
        and /images will be written.

    waveforms : WaveformExtractor
        Spikeinterface WaveformExtractor object.

    backend : Literal["jax", "numpy"]
        The backend with which to run waveform comparisons. Jax is around 50
        times faster in this case.
    """
    utils.message_user("Saving waveform similarity matrices...\n")

    matrices_out_path = waveforms_output_path / "similarity_matrices"
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


def save_plots_of_templates(waveforms_output_path: Path, waveforms: WaveformExtractor):
    """
    Save a plot of all templates in 'waveforms/images' folder. The plot
    displays the template waveform are calculated in two ways
        1) as the mean over the `unit_chan_idxs`, which are the channels
           in which the template waveform signals are strongest.
        2) as the channel in which the waveform signal is strongest (as
           determined by the minimum value)

    The purpose of these plots is to provide a quick overview of the
    extract templates. Proper investigations on unit quality should
    be done in Phy.

    Parameters
    ------

    waveforms_output_path : Path
        Pathlib object holding the output path where waveforms are saved
        and /images will be written.

    waveforms : WaveformExtractor
        Spikeinterface WaveformExtractor object.

    TODO
    ----
    This assumes the waveform are negative (argmin here, use of peak_sign="neg"
    in compute_sparsity). Investigate and handle positive waveforms...

    TODO: how to determine "neg", "pos", "both", how to decide the
    peak_sign / radius when computing sparisty. Own function.
    """
    t = time.perf_counter()
    utils.message_user("Saving template images...\n")

    fs = waveforms.sampling_frequency
    n_samples = waveforms.nsamples
    time_ = np.arange(n_samples) / fs * 1000

    sparsity = compute_sparsity(
        waveforms, peak_sign="neg", method="radius", radius_um=75
    )

    y_label = "Voltage (uV)" if waveforms.return_scaled else "Voltage (unscaled)"

    for idx, unit_id in enumerate(waveforms.sorting.get_unit_ids()):
        unit_template = waveforms.get_template(unit_id)
        unit_chan_idxs = sparsity.unit_id_to_channel_indices[unit_id]

        plt.plot(time_, np.mean(unit_template[:, unit_chan_idxs], axis=1))

        peak_chan_idx = np.argmin(np.mean(unit_template[:, unit_chan_idxs], axis=0))
        plt.plot(time_, unit_template[:, unit_chan_idxs[peak_chan_idx]])

        plt.legend(["max signal channel", "mean across best channels"])
        plt.xlabel("Time (ms)")
        plt.ylabel(y_label)
        plt.title(f"Unit {unit_id} Template")

        output_folder = waveforms_output_path / "images"
        output_folder.mkdir(exist_ok=True)
        plt.savefig(waveforms_output_path / "images" / f"unit_{unit_id}.png")
        plt.clf()

    utils.message_user(f"Saving plots of templates took: {time.perf_counter() - t}")
