from __future__ import annotations

from typing import TYPE_CHECKING, List, Union

if TYPE_CHECKING:
    from pathlib import Path

import spikeinterface.extractors as se
from spikeinterface import append_recordings

from .data_class import Data


def load_spikeglx_data(
    base_path: Union[Path, str], sub_name: str, run_names: Union[List[str], str]
) -> Data:
    """
    Load raw spikeglx data (in rawdata). If multiple runs are selected
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
        The spikeglx run name (i.e. not including the gate index). This can
        also be a list of run names, or "all".

    Returns
    -------

    Data class containing SpikeINterface recording object and information
    on the data filepaths.
    """
    data = Data(base_path, sub_name, run_names)

    all_recordings = [
        se.read_spikeglx(
            folder_path=run_path, stream_id="imec0.ap", all_annotations=True
        )
        for run_path in data.all_run_paths
    ]

    data["0-raw"] = append_recordings(all_recordings)

    return data
