"""
"""

import spikeinterface as si
from spikeinterface import curation
import spikeinterface.exporters as se
from spikeinterface.extractors import KiloSortSortingExtractor
from pathlib import Path
import utils


def quality_check(preprocessed_output_path,
                  sorter="kilosort2_5"):
    """
    """
    data, recording = utils.load_data_and_recording(preprocessed_output_path)
    data.set_sorter_output_paths(sorter)

    sorting = KiloSortSortingExtractor(folder_path=data.sorter_run_output_path,
                                       keep_good_only=False)

    sorting_without_excess_spikes = curation.remove_excess_spikes(sorting, recording)

    if not data.waveforms_output_path.is_dir():
        waveforms = si.extract_waveforms(recording, sorting_without_excess_spikes, folder=data.waveforms_output_path)
    else:
        waveforms = si.load_waveforms(data.waveforms_output_path)

    metrics = si.qualitymetrics.compute_quality_metrics(waveforms)
    metrics.to_csv(data.quality_metrics_pathoutput_path / "quality_metrics.csv")
