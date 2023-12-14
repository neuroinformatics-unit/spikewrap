from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Union

import numpy as np
import spikeinterface.extractors as se
import spikeinterface.preprocessing as spre
from spikeinterface import load_extractor

from spikewrap.data_classes.preprocessing import PreprocessingData
from spikewrap.utils import utils


def load_data(
    base_path: Union[Path, str],
    sub_name: str,
    sessions_and_runs: Dict[str, List[str]],
    data_format: str = "spikeglx",
) -> PreprocessingData:
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

    sessions_and_runs : Dict[str, Union[str, List]]
        A dictionary containing the sessions and runs to run through the pipeline.
        Each session should be a session-level folder name residing in the passed
        `sub_name` folder. Each session to run is a key in the
        `sessions_and_runs` dict.
        For each session key, the value can be a single run name (str)
        or a list of run names. The runs will be processed in the
        order passed.

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
    empty_data_class = PreprocessingData(Path(base_path), sub_name, sessions_and_runs)

    # TODO: when extending to OpenEphys, will need to carefully centralise
    # as much logic as possible e.g. casting to float64 with astype.
    if data_format == "spikeglx":
        _load_spikeglx_data(empty_data_class)

    elif data_format == "spikeinterface":
        _load_spikeinterface(
            empty_data_class
        )  # TODO: this return isn't needed as preprocess_data is simply filled.
    else:
        raise RuntimeError("`data_format` not recognised.")

    empty_data_class.assert_if_multi_segment()  # TODO: change this stupid obj name!

    return empty_data_class  # TODO: change this stupid obj name!


# --------------------------------------------------------------------------------------
# Format-specific Loaders
# --------------------------------------------------------------------------------------


def _load_spikeglx_data(preprocess_data: PreprocessingData) -> PreprocessingData:
    """
    Load raw SpikeGLX data (in rawdata). If multiple runs are selected
    in run_names, these will be stored as segments on a SpikeInterface
    recording object.

    See load_data() for parameters.
    """
    for ses_name, run_name in preprocess_data.flat_sessions_and_runs():
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
        orig_dtype = without_sync.dtype
        without_sync = spre.astype(without_sync, np.float64)

        preprocess_data.set_orig_dtype(orig_dtype)  # TODO: move this out of the loop.

        preprocess_data[ses_name][run_name]["0-raw"] = without_sync
        preprocess_data.sync[ses_name][run_name] = with_sync

        utils.message_user(f"Raw session data was loaded from {run_path}")

    return preprocess_data


def _load_spikeinterface(preprocess_data):  # TODO: does not handle sync
    """
    TODO: centralise
    """
    for ses_name, run_name in preprocess_data.flat_sessions_and_runs():
        run_path = preprocess_data.get_rawdata_run_path(ses_name, run_name)
        assert run_name == run_path.name, "TODO"

        recording = load_extractor(run_path)

        orig_dtype = recording.dtype

        recording = spre.astype(recording, np.float64)

        preprocess_data.set_orig_dtype(orig_dtype)  # TODO: move this out of the loop.

        preprocess_data[ses_name][run_name]["0-raw"] = recording

        utils.message_user(f"Raw session data was loaded from {run_path}")

    preprocess_data.sync = None

    return preprocess_data
