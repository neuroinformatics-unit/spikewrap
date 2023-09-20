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

    def _validate_rawdata_inputs(self) -> None:
        self._validate_inputs(
            "rawdata",
            self.get_rawdata_top_level_path,
            self.get_rawdata_sub_path,
            self.get_rawdata_ses_path,
            self.get_rawdata_run_path,
        )

    # Saving preprocessed data ---------------------------------------------------------

    def save_preprocessed_data(
        self, ses_name: str, run_name: str, overwrite: bool = False
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

        self._save_preprocessed_binary(ses_name, run_name)
        self._save_sync_channel(ses_name, run_name)
        self._save_preprocessing_info(ses_name, run_name)

    def _save_preprocessed_binary(self, ses_name: str, run_name: str) -> None:
        """
        Save the fully preprocessed data (i.e. last step in the
        preprocessing chain) to binary file. This is required for sorting.

        If the recording is a `Dict`, then it was split during `run_preprocess`
        and each recording in the dictionary is a split shank. Otherwise, it
        is a single (unsplit) recording object.
        """
        recording, __ = utils.get_dict_value_from_step_num(
            self[ses_name][run_name], "last"
        )

        if isinstance(recording, Dict):
            for shank, rec in recording.items():
                utils.message_user(
                    f"Saving preprocessed data for {ses_name}, {run_name}, shank {shank}."
                )

                rec.save(
                    folder=self._get_pp_binary_data_path(ses_name, run_name)
                    / f"shank_{shank}",
                    chunk_memory="10M",  # TODO: handle duplication.
                )
        else:
            utils.message_user(f"Saving preprocessed data for {ses_name}, {run_name}.")

            recording.save(
                folder=self._get_pp_binary_data_path(ses_name, run_name),
                chunk_memory="10M",
            )

    def _save_sync_channel(self, ses_name: str, run_name: str) -> None:
        """
        Save the sync channel separately. In SI, sorting cannot proceed
        if the sync channel is loaded to ensure it does not interfere with
        sorting. As such, the sync channel is handled separately here.
        """
        utils.message_user(f"Saving sync channel for {ses_name} run {run_name}")

        assert (
            self.sync[ses_name][run_name] is not None
        ), f"Sync channel on PreprocessData session {ses_name} run {run_name} is None"

        self.sync[ses_name][run_name].save(  # type: ignore
            folder=self._get_sync_channel_data_path(ses_name, run_name),
            chunk_memory="10M",
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
