import shutil
from dataclasses import dataclass
from typing import Dict, Optional

import spikeinterface
from spikeinterface.preprocessing import astype

from spikewrap.data_classes.base import BaseUserDict
from spikewrap.utils import utils


@dataclass
class PreprocessingData(BaseUserDict):
    """
    Dictionary to store SpikeInterface preprocessing recordings.

    Details on the preprocessing steps are held in the dictionary keys e.g.
    e.g. 0-raw, 1-raw-bandpass_filter, 2-raw_bandpass_filter-common_average
    and recording objects are held in the value. These are generated
    by the `pipeline.preprocess._preprocess_and_save_all_runs()` function.

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

    orig_dtype = None

    def __post_init__(self) -> None:
        super().__post_init__()

        self._convert_session_and_run_keywords_to_foldernames(
            self.get_rawdata_sub_path,
            self.get_rawdata_ses_path,
        )
        self._validate_rawdata_inputs()

        self.sync: Dict = {}

        for ses_name, run_name in self.flat_sessions_and_runs():
            self.update_two_layer_dict(self, ses_name, run_name, {"0-raw": None})
            self.update_two_layer_dict(self.sync, ses_name, run_name, None)

    def __repr__(self):
        """
        Show the dict not the class.
        This does not work on base class.
        """
        return self.data.__repr__()

    def set_orig_dtype(self, dtype):  # TODO: type dtype!
        """used for writing data"""
        self.orig_dtype = dtype

    def set_pp_steps(self, pp_steps: Dict) -> None:
        """
        Set the preprocessing steps (`pp_steps`) attribute
        that defines the preprocessing steps and options.

        Parameters
        ----------
        pp_steps : Dict
            Preprocessing steps to setp as class attribute. These are used
            when `pipeline.preprocess._fill_run_data_with_preprocessed_recording()` function is called.
        """
        self.pp_steps = pp_steps

    def _validate_rawdata_inputs(
        self,
    ) -> None:  # TODO: getting these paths should be handled at BASE!
        self._validate_inputs(
            "rawdata",
            self.get_rawdata_top_level_path,
            self.get_rawdata_sub_path,
            self.get_rawdata_ses_path,
            self.get_rawdata_run_path,
        )

    # Saving preprocessed data ---------------------------------------------------------

    def save_preprocessed_data(
        self,
        ses_name: str,
        run_name: str,
        overwrite: bool = False,
        chunk_size: Optional[
            int
        ] = None,  # TODO: remove all default arguments from internal calls?
    ) -> None:
        """
        Save the preprocessed output data to binary, as well
        as important class attributes to a .yaml file.

        Both are saved in a folder called 'preprocessed'
        in derivatives/<sub_name>/<pp_run_name>

        Parameters
        ----------
        run_name : str
            Run name corresponding to one of `self.preprocessing_run_names`.

        overwrite : bool
            If `True`, existing preprocessed output will be overwritten.
            By default, SpikeInterface will error if a binary recording file
            (`si_recording`) already exists where it is trying to write one.
            In this case, an error  should be raised before this function
            is called.

        """
        if overwrite:
            if self.get_preprocessing_path(ses_name, run_name).is_dir():
                shutil.rmtree(self.get_preprocessing_path(ses_name, run_name))

        self._save_preprocessed_binary(ses_name, run_name, chunk_size)

        if self.sync:
            self._save_sync_channel(ses_name, run_name, chunk_size)

        self._save_preprocessing_info(ses_name, run_name)

    def _save_preprocessed_binary(
        self, ses_name: str, run_name: str, chunk_size: Optional[int]
    ) -> None:
        """
        Save the fully preprocessed data (i.e. last step in the
        preprocessing chain) to binary file. This is required for sorting.
        """
        recording, __ = utils.get_dict_value_from_step_num(
            self[ses_name][run_name], "last"
        )

        recording = astype(recording, self.orig_dtype)

        if chunk_size is None:
            chunk_size = utils.get_default_chunk_size(recording)

        recording.save(
            folder=self._get_pp_binary_data_path(ses_name, run_name),
            chunk_size=chunk_size,
        )

    def _save_sync_channel(
        self, ses_name: str, run_name: str, chunk_size: Optional[int]
    ) -> None:
        """
        Save the sync channel separately. In SI, sorting cannot proceed
        if the sync channel is loaded to ensure it does not interfere with
        sorting. As such, the sync channel is handled separately here.
        """
        utils.message_user(f"Saving sync channel for {ses_name} run {run_name}")

        assert (
            self.sync[ses_name][run_name] is not None
        ), f"Sync channel on PreprocessData session {ses_name} run {run_name} is None"

        sync_recording = self.sync[ses_name][run_name]

        if chunk_size is None:
            chunk_size = utils.get_default_chunk_size(sync_recording, sync=True)

        sync_recording.save(  # type: ignore
            folder=self._get_sync_channel_data_path(ses_name, run_name),
            chunk_size=chunk_size,
        )

    def _save_preprocessing_info(self, ses_name: str, run_name: str) -> None:
        """
        Save important details of the postprocessing for provenance.

        Importantly, this is used to check that the preprocessing
        file used for waveform extraction in `PostprocessData`
        matches the preprocessing that was used for sorting.
        """
        assert self.pp_steps is not None, "type narrow `pp_steps`."

        utils.cast_pp_steps_values(self.pp_steps, "list")

        preprocessing_info = {
            "base_path": self.base_path.as_posix(),
            "sub_name": self.sub_name,
            "ses_name": ses_name,
            "run_name": run_name,
            "rawdata_path": self.get_rawdata_run_path(ses_name, run_name).as_posix(),
            "pp_steps": self.pp_steps,
            "spikeinterface_version": spikeinterface.__version__,
            "spikewrap_version": utils.spikewrap_version(),
            "datetime_written": utils.get_formatted_datetime(),
        }

        utils.dump_dict_to_yaml(
            self.get_preprocessing_info_path(ses_name, run_name), preprocessing_info
        )
