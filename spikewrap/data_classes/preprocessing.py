import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union

import spikeinterface

from ..utils import utils
from .base import BaseUserDict


class PreprocessingData(BaseUserDict):
    def __init__(
        self,
        base_path: Union[Path, str],
        sub_name: str,
        run_names: Union[List[str], str],
    ):
        """
        Dictionary to store SpikeInterface preprocessing recordings.
        These are lazy and preprocessing only run when the recording.get_traces()
        is called, or the data is saved to binary.

        Details on the preprocessing steps are held in the dictionary keys e.g.
        e.g. 0-raw, 1-raw-bandpass_filter, 2-raw_bandpass_filter-common_average
        and recording objects are held in the value.

        The class manages paths to raw data and preprocessing output,
        as defines methods to dump key information and the SpikeInterface
        binary to disk.

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
        super(PreprocessingData, self).__init__(base_path, sub_name, run_names)

        self.pp_steps: Optional[Dict] = None
        self.data: Dict = {run_name: {"0-raw": None} for run_name in self.run_names}
        self.sync = {run_name: None for run_name in self.run_names}

    # Load and Save --------------------------------------------------------------------

    def _top_level_folder(self):
        return "rawdata"

    def set_pp_steps(self, pp_steps: Dict) -> None:
        """
        Set the preprocessing steps (`pp_steps`) attribute
        that defines the preprocessing steps and options.

        Parameters
        ----------
        pp_steps : Dict
            Preprocessing steps to setp as class attribute. These are used
            when `pipeline.preprocess.preprocess()` function is called.
        """
        self.pp_steps = pp_steps

    def save_preprocessed_data(self, run_name: str, overwrite: bool = False) -> None:
        """
        Save the preprocessed output data to binary, as well
        as important class attributes to a .yaml file.

        Both are saved in a folder called 'preprocessed'
        in derivatives/<sub_name>/<pp_run_name>

        Parameters
        ----------
        overwrite : bool
            If `True`, existing preprocessed output will be overwritten.
            By default, SpikeInterface will error if a binary recording file
            (`si_recording`) already exists where it is trying to write one.
            In this case, an error  should be raised before this function
            is called.

        """
        if overwrite:
            if self.get_preprocessing_path(run_name).is_dir():
                shutil.rmtree(self.get_preprocessing_path(run_name))

        self._save_preprocessed_binary(run_name)
        self._save_sync_channel(run_name)
        self._save_preprocessing_info(run_name)

    def _save_preprocessed_binary(self, run_name: str) -> None:
        """
        Save the fully preprocessed data (i.e. last step in the
        preprocessing chain) to binary file. This is required for sorting.
        """
        recording, __ = utils.get_dict_value_from_step_num(self[run_name], "last")
        recording.save(
            folder=self._get_pp_binary_data_path(run_name), chunk_memory="10M"
        )

    def _save_sync_channel(self, run_name: str) -> None:
        """ """
        assert self.sync is not None, "Sync channel on PreprocessData is None"
        self.sync[run_name].save(
            folder=self._get_sync_channel_data_path(run_name), chunk_memory="10M"
        )

    def _save_preprocessing_info(self, run_name: str) -> None:
        """ """
        assert self.pp_steps is not None, "type narrow `pp_steps`."

        utils.cast_pp_steps_values(self.pp_steps, "list")

        preprocessing_info = {
            "base_path": self.base_path.as_posix(),
            "sub_name": self.sub_name,
            "rawdata_path": self.get_run_path(run_name).as_posix(),
            "pp_steps": self.pp_steps,
            "si_version": spikeinterface.__version__,
            "datetime_written": utils.get_formatted_datetime(),
        }

        utils.dump_dict_to_yaml(
            self._get_preprocessing_info_path(run_name), preprocessing_info
        )
