import spikeinterface.extractors as se
from spikeinterface import append_recordings

from .data_class import Data


def load_spikeglx_data(base_path, sub_name, run_names):
    """ """
    data = Data(base_path, sub_name, run_names)

    all_recordings = [
        se.read_spikeglx(
            folder_path=run_path, stream_id="imec0.ap", all_annotations=True
        )
        for run_path in data.all_run_paths
    ]

    data["0-raw"] = append_recordings(all_recordings)

    return data
