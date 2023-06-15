from __future__ import annotations

from typing import TYPE_CHECKING, List, Union

if TYPE_CHECKING:
    from pathlib import Path

import spikeinterface.extractors as se
from spikeinterface import append_recordings

from ..data_classes.preprocessing import PreprocessingData
from ..data_classes.sorting import SortingData

def load_spikeglx_data(
    base_path: Union[Path, str], sub_name: str, run_names: Union[List[str], str]
) -> PreprocessingData:
    """
    Load raw SpikeGLX data (in rawdata). If multiple runs are selected
    in run_names, these will be stored as segments on a SpikeInterface
    recording object.

    Parameters
    -----------

    base_path : Union[Path, str]
        Path where the rawdata folder containing subjects.

    sub_name : str
        Subject to preprocess. The subject top level dir should reside in
        base_path/rawdata/ .

    run_names : Union[List[str], str],
        The SpikeGLX run name (i.e. not including the gate index). This can
        also be a list of run names.

    Returns
    -------

    PreprocessingData class containing SpikeInterface recording object and information
    on the data filepaths.
    """
    preprocess_data = PreprocessingData(base_path, sub_name, run_names)

    all_recordings = [
        se.read_spikeglx(
            folder_path=run_path, stream_id="imec0.ap",
            all_annotations=True, load_sync_channel=False,
        )
        for run_path in preprocess_data.all_run_paths
    ]

    preprocess_data["0-raw"] = append_recordings(all_recordings)

    return preprocess_data


def load_data_for_sorting(
    preprocessed_data_path: Path,
    concatenate: bool = True,
) -> Tuple[PreprocessingData, BaseRecording]:
    """
    Returns the previously preprocessed PreprocessingData and
    recording object loaded from the preprocess path.

    During sorting, preprocessed data is saved to
    derivatives/<sub level dirs>/preprocessed. The spikeinterface
    recording (si_recording) and PreprocessingData (data_class.pkl) are saved.

    Parameters
    ----------

    preprocessed_data_path : Path
        Path to the preprocessed folder, containing the binary si_recording
        of the preprocessed data and the data_class.pkl containing all filepath
        information.

    concatenate : bool
        If True, the multi-segment recording object will be concatenated
        together. This is used prior to sorting. Segments should be
        experimental runs.
    """
    sorting_data = SortingData(
        preprocessed_data_path,
    )

    sorting_data.load_preprocessed_binary(concatenate)

    return sorting_data
