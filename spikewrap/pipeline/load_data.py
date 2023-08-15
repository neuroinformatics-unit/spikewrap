from __future__ import annotations

from typing import TYPE_CHECKING, Union

import spikeinterface.extractors as se

from ..data_classes.preprocessing import PreprocessingData
from ..utils import utils

if TYPE_CHECKING:
    from pathlib import Path


def load_data(
    base_path: Union[Path, str],
    sub_name: str,
    sessions_and_runs: Dict,
    data_format: str = "spikeglx",
):
    """
    Load raw data (in rawdata). If multiple runs are selected
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

    data_format : str
        The data type format to load. Currently only "spikeglx" is accepted.

    Returns
    -------

    PreprocessingData class containing SpikeInterface recording object and information
    on the data filepaths.

    TODO
    ----
    Figure out the format from the data itself, instead of passing as argument.
    Do this when adding the next supported format.
    """
    empty_data_class = PreprocessingData(base_path, sub_name, sessions_and_runs)

    if data_format == "spikeglx":
        return load_spikeglx_data(empty_data_class)


# --------------------------------------------------------------------------------------
# Format-specific Loaders
# --------------------------------------------------------------------------------------


def load_spikeglx_data(preprocess_data: PreprocessingData) -> PreprocessingData:
    """
    Load raw SpikeGLX data (in rawdata). If multiple runs are selected
    in run_names, these will be stored as segments on a SpikeInterface
    recording object.

    See load_data() for parameters.
    """
    for ses_name, run_name in preprocess_data.preprocessing_sessions_and_runs():
        run_path = preprocess_data.get_rawdata_run_path(ses_name, run_name)
        assert run_name == run_path.name, "TODO"

        with_sync, without_sync = [
            se.read_spikeglx(
                folder_path=run_path,
                stream_id="imec0.ap",
                all_annotations=True,
                load_sync_channel=sync,
            )
            for sync in [True, False]
        ]
        preprocess_data[ses_name][run_name]["0-raw"] = without_sync
        preprocess_data.sync[ses_name][run_name] = with_sync

        utils.message_user(f"Raw session data was loaded from {run_path}")

    return preprocess_data
