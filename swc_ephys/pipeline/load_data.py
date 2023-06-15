from __future__ import annotations

from typing import TYPE_CHECKING, List, Union

if TYPE_CHECKING:
    from pathlib import Path

import spikeinterface.extractors as se
from spikeinterface import append_recordings

from .data_class import PreprocessData


def load_spikeglx_data(
    base_path: Union[Path, str], sub_name: str, run_names: Union[List[str], str]
) -> PreprocessData:
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

    PreprocessData class containing SpikeInterface recording object and information
    on the data filepaths.
    """
    preprocess_data = PreprocessData(base_path, sub_name, run_names)

    all_recordings = [
        se.read_spikeglx(
            folder_path=run_path, stream_id="imec0.ap",
            all_annotations=True, load_sync_channel=False,
        )
        for run_path in preprocess_data.all_run_paths
    ]

    preprocess_data["0-raw"] = append_recordings(all_recordings)

    return preprocess_data
