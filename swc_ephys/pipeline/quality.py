"""
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from spikeinterface.core import BaseSorting


from pathlib import Path

import spikeinterface as si
from spikeinterface import curation
from spikeinterface.core import BaseRecording
from spikeinterface.extractors import KiloSortSortingExtractor

from ..data_classes.sorting import SortingData
from ..pipeline.load_data import load_data_for_sorting
from ..utils import utils


def quality_check(
    sorting_data: Union[Path, str, SortingData],
    sorter: str = "kilosort2_5",
    verbose: bool = True,
) -> None:
    """
    Save quality metrics on sorting output to a quality_metrics.csv file.

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
    """
    if not isinstance(sorting_data, SortingData):
        sorting_data = load_data_for_sorting(
            Path(sorting_data),
        )
    assert isinstance(sorting_data, SortingData), "type narrow `sorting_data`."

    sorting_data.set_sorter_output_paths(sorter)

    utils.message_user(
        f"Qualitys Checks: sorting path used: {sorting_data.sorter_run_output_path}",
        verbose,
    )

    if not sorting_data.waveforms_output_path.is_dir():
        utils.message_user(f"Saving waveforms to {sorting_data.waveforms_output_path}")

        sorting_without_excess_spikes = load_sorting_output(
            sorting_data, sorter
        )

        waveforms = si.extract_waveforms(
            sorting_data.data["0-preprocessed"],
            sorting_without_excess_spikes,
            folder=sorting_data.waveforms_output_path,
        )
    else:
        utils.message_user(
            f"Loading existing waveforms from: {sorting_data.waveforms_output_path}",
            verbose,
        )

        waveforms = si.load_waveforms(sorting_data.waveforms_output_path)

    metrics = si.qualitymetrics.compute_quality_metrics(waveforms)
    metrics.to_csv(sorting_data.quality_metrics_path)

    utils.message_user(f"Quality metrics saved to {sorting_data.quality_metrics_path}")


def load_sorting_output(
    sorting_data: SortingData, sorter: str
) -> BaseSorting:
    """
    Load the output of a sorting run.

    TODO: understand remove_excess_spikes.
    """
    if not sorting_data.sorter_run_output_path.is_dir():
        raise FileNotFoundError(
            f"{sorter} output was not found at "
            f"{sorting_data.sorter_run_output_path}.\n"
            f"Quality metrics were not generated."
        )

    assert len(sorting_data) == 1, "unexpected number of entries in " \
                                   "`sorting_data` dict."

    recording = sorting_data[sorting_data.init_data_key]

    sorting = KiloSortSortingExtractor(
        folder_path=sorting_data.sorter_run_output_path, keep_good_only=False
    )

    sorting_without_excess_spikes = curation.remove_excess_spikes(sorting, recording)

    return sorting_without_excess_spikes
