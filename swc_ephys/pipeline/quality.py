"""
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from ..pipeline.data_class import SortingData

from pathlib import Path

import spikeinterface as si
from spikeinterface import curation
from spikeinterface.core import BaseRecording
from spikeinterface.extractors import KiloSortSortingExtractor

from ..utils import utils
from ..pipeline.data_class import SortingData
from ..pipeline.load_data import load_data_for_sorting

def quality_check(
    sorting_data: Union[Path, str, SortingData],
    sorter: str = "kilosort2_5",
    verbose: bool = True,
):
    """
    Save quality metrics on sorting output to a quality_metrics.csv file.

    Parameters
    ----------

    sorting_data : Union[Path, str]
        The path to the 'preprocessed' folder in the subject / run
        folder used for sorting or a SortingData object.

    sorter : str
        The name of the sorter (e.g. "kilosort2_5").

    verbose : bool
        If True, messages will be printed to consolve updating on the
        progress of preprocessing / sorting.
    """
    if not isinstance(sorting_data, SortingData):
        sorting_data = load_data_for_sorting(
            Path(preprocessed_output_path),
        )
    sorting_data.set_sorter_output_paths(sorter)

    utils.message_user(
        f"Qualitys Checks: sorting path used: {sorting_data.sorter_run_output_path}", verbose
    )

    if not sorting_data.waveforms_output_path.is_dir():
        utils.message_user(f"Saving waveforms to {sorting_data.waveforms_output_path}")

        sorting_without_excess_spikes = load_sorting_output(sorting_data, sorting_data.data["0-preprocessed"], sorter)  # TODO: fix double pass

        waveforms = si.extract_waveforms(
            sorting_data.data["0-preprocessed"], sorting_without_excess_spikes, folder=sorting_data.waveforms_output_path
        )
    else:
        utils.message_user(
            f"Loading existing waveforms from: {sorting_data.waveforms_output_path}", verbose
        )

        waveforms = si.load_waveforms(sorting_data.waveforms_output_path)

    metrics = si.qualitymetrics.compute_quality_metrics(waveforms)
    metrics.to_csv(sorting_data.quality_metrics_path)

    utils.message_user(f"Quality metrics saved to {sorting_data.quality_metrics_path}")


def load_sorting_output(sorting_data: PreprocessingData, recording: BaseRecording, sorter: str):
    """
    Load the output of a sorting run.
    """
    if not sorting_data.sorter_run_output_path.is_dir():
        raise FileNotFoundError(
            f"{sorter} output was not found at "
            f"{sorting_data.sorter_run_output_path}.\n"
            f"Quality metrics were not generated."
        )

    sorting = KiloSortSortingExtractor(
        folder_path=sorting_data.sorter_run_output_path, keep_good_only=False
    )

    sorting_without_excess_spikes = curation.remove_excess_spikes(sorting, recording)

    return sorting_without_excess_spikes
