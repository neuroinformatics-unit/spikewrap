"""
"""
from pathlib import Path
from typing import Union

import spikeinterface as si
from spikeinterface import curation
from spikeinterface.extractors import KiloSortSortingExtractor

from ..utils import utils


def quality_check(
    preprocessed_output_path: Union[Path, str], sorter: str = "kilosort2_5"
):
    """
    Save quality metrics on sorting output to a qualitric_metrics.csv file.

    Parameters
    ----------

    preprocessed_output_path : the path to the 'preprocessed' folder in the
                               subject / run folder used for sorting.

    sorter : the name of the sorter (e.g. "kilosort2_5").

    """
    data, recording = utils.load_data_and_recording(Path(preprocessed_output_path))
    data.set_sorter_output_paths(sorter)

    if not data.waveforms_output_path.is_dir():
        sorting_without_excess_spikes = load_sorting_output(data, recording, sorter)
        waveforms = si.extract_waveforms(
            recording, sorting_without_excess_spikes, folder=data.waveforms_output_path
        )
    else:
        waveforms = si.load_waveforms(data.waveforms_output_path)

    metrics = si.qualitymetrics.compute_quality_metrics(waveforms)
    metrics.to_csv(data.quality_metrics_path)


def load_sorting_output(data, recording, sorter):
    """
    Load the output of a sorting run
    """
    if not data.sorter_run_output_path.is_dir():
        raise FileNotFoundError(
            f"{sorter} output was not found at "
            f"{data.sorter_run_output_path}.\n"
            f"Quality metrics were not generated."
        )

    sorting = KiloSortSortingExtractor(
        folder_path=data.sorter_run_output_path, keep_good_only=False
    )

    sorting_without_excess_spikes = curation.remove_excess_spikes(sorting, recording)

    return sorting_without_excess_spikes
