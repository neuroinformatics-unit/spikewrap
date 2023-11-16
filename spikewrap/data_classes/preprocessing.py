import shutil
from dataclasses import dataclass
from typing import Dict

import spikeinterface

from ..utils import utils
from .base import BaseUserDict


@dataclass
class PreprocessingData(BaseUserDict):
    """
    Dictionary to store SpikeInterface preprocessing recordings.

    Details on the preprocessing steps are held in the dictionary keys e.g.
    e.g. 0-raw, 1-raw-bandpass_filter, 2-raw_bandpass_filter-common_average
    and recording objects are held in the value. These are generated
    by the `pipeline.preprocess.run_preprocessing()` function.

    The class manages paths to raw data and preprocessing output,
    as defines methods to dump key information and the SpikeInterface
    binary to disk. Note that SI preprocessing  is lazy and
    preprocessing only run when the recording.get_traces()
    is called, or the data is saved to binary.

    Parameters
    ----------
    base_path : Union[Path, str]
        Path where the rawdata folder containing subjects.

    sub_name : str
        'subject' to preprocess. The subject top level dir should
        reside in base_path/rawdata/.

    run_names : Union[List[str], str]
        The SpikeGLX run name (i.e. not including the gate index)
        or list of run names.
    """

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_rawdata_inputs()

        self.sync: Dict = {}

        for ses_name, run_name in self.preprocessing_sessions_and_runs():
            utils.update(self.data, ses_name, run_name, {"0-raw": None})
            utils.update(self.sync, ses_name, run_name, None)

    def _validate_rawdata_inputs(self) -> None:
        self._validate_inputs(
            "rawdata",
            self.get_rawdata_top_level_path,
            self.get_rawdata_sub_path,
            self.get_rawdata_ses_path,
            self.get_rawdata_run_path,
        )
