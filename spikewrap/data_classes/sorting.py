from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING, Dict, List, Optional

import spikeinterface as si
from spikeinterface import concatenate_recordings

from spikewrap.data_classes.base import BaseUserDict
from spikewrap.utils import utils

if TYPE_CHECKING:
    from pathlib import Path


# TODO: do some checking of order!
# TODO: test here with multiple runs
# TODO: need to validate more, preprocessing data is not validating correctly!!
# TODO: add "all"


@dataclass
class SortingData(BaseUserDict, ABC):
    """
    Class to organise the sorting of preprocessed data.

    Parameters
    ----------

    base_path : Union[Path, str]
     Path to the rawdata folder containing subjects folders.

    sub_name : str
     Subject to preprocess. The subject top level dir should reside in
     base_path/rawdata/ .

    run_names : Union[List[str], str],
     The SpikeGLX run name (i.e. not including the gate index). This can
     also be a list of run names. Preprocessing will still occur per-run.
     Runs are concatenated in the order passed prior to sorting.

    sorter : str
     Name of the sorter to use (e.g. "kilosort2_5").

    concat_for_sorting: bool
     If `True`, preprocessed runs are concatenated together before sorting.
     Otherwise, runs are sorted separately.

    Notes
    -----

    Preprocessed data are stored in this UserDict (i.e. in `self.data`).
    If `self.concat_for_sorting`, these preprocessed data is concatenated
    together. If concatenation is not performed, `self.data` will be
    a dictionary of N runs. Otherwise if concatenation is performed,
    `self.data` will always have only a single run - the concentrated data.
    However, `self.run_names` will still hold the original preprocessed data
    run names, and the new concatenated run name to which the data are
    saved is accessed by `self.concat_run_name()`
    """

    sorter: str
    print_messages: bool = True

    def __post_init__(self) -> None:
        super().__post_init__()

        self._convert_session_and_run_keywords_to_foldernames(
            self.get_derivatives_sub_path,
            self.get_derivatives_ses_path,
        )
        self._validate_derivatives_inputs()
        self._check_preprocessing_exists()

        self.load_preprocessed_binary()

    def __repr__(self):
        """
        Show the dict not the class.
        This does not work on base class.
        """
        return self.data.__repr__()

    # Checkers
    # ----------------------------------------------------------------------------------

    def _check_preprocessing_exists(self) -> None:
        """
        Check that the preprocessed data to be sorted exists
        at the expected filepaths
        """

        def error_message(path_):
            return (
                f"The run folder {path_.stem} cannot be found at "
                f"file path {path_.parent}."
            )

        for ses_name, run_name in self.flat_sessions_and_runs():
            assert (
                prepro_path := self.get_derivatives_run_path(ses_name, run_name)
                / "preprocessing"
            ).is_dir(), error_message(prepro_path)

            assert (
                recording_path := prepro_path / "si_recording"
            ).is_dir(), error_message(recording_path)

    # Load and concatenate preprocessed data
    # ----------------------------------------------------------------------------------

    def initialise_preprocessed_recordings_dict(self) -> Dict:
        """"""
        recordings: Dict = {}
        for ses_name, run_name in self.flat_sessions_and_runs():
            rec = si.load_extractor(self._get_pp_binary_data_path(ses_name, run_name))
            self.update_two_layer_dict(recordings, ses_name, run_name, value=rec)

        return recordings

    def _concatenate_runs(self, ses_name: str, recordings: Dict) -> si.BaseRecording:
        """
        Concatenate the Spikeinterface recording objects together.

        Parameters
        ----------
        recordings : Dict
            A dictionary in which key are the run names and values are the
            SI recording object holding the preprocessed data for that run.

        Returns
        -------
        concatenated_recording : si.BaseRecording
            A SI recording object holding the concatenated preprocessed data.
        """
        session_run_names, recordings_list = zip(*recordings[ses_name].items())
        concatenated_recording = concatenate_recordings(recordings_list)

        assert session_run_names == tuple(
            self.sessions_and_runs[ses_name]
        ), "Something has gone wrong in the `run_names` ordering."

        if self.print_messages:
            self.check_ses_or_run_folders_in_datetime_order(ses_name)

            utils.message_user(
                f"Preprocessed data loaded prior to sorting for session {ses_name}. "
                f"Runs were concatenated runs in the order: "
                f"{session_run_names}"
            )

        return concatenated_recording

    def check_ses_or_run_folders_in_datetime_order(
        self, ses_name: Optional[str] = None
    ) -> None:
        """"""
        if ses_name is None:
            list_of_paths = [
                self.get_rawdata_ses_path(ses_name)
                for ses_name in self.sessions_and_runs.keys()
            ]
        else:
            list_of_paths = [
                self.get_rawdata_run_path(ses_name, run_name)
                for run_name in self.sessions_and_runs[ses_name]
            ]

        for path_ in list_of_paths:
            if not path_.is_dir():
                utils.message_user(
                    f"Could not find raw data to check concatenation order."
                    f"Concatenation will proceed in the following order: {list_of_paths}"
                )
                return

        if not utils.paths_are_in_datetime_order(list_of_paths, "creation"):
            warnings.warn(
                f"The sessions or runs provided for are not in creation datetime "
                f"order. \nThey will be concatenated in the order provided, as: {list_of_paths}."
            )

    # Paths
    # ----------------------------------------------------------------------------------

    def get_sorting_path(self, ses_name: str, run_name: Optional[str]) -> Path:
        return self._get_base_sorting_path(ses_name, run_name) / "sorting"

    def get_sorter_output_path(self, ses_name: str, run_name: Optional[str]) -> Path:
        return self.get_sorting_path(ses_name, run_name) / "sorter_output"

    def _get_sorting_info_path(self, ses_name: str, run_name: Optional[str]) -> Path:
        return self.get_sorting_path(ses_name, run_name) / utils.canonical_names(
            "sorting_yaml"
        )

    def get_postprocessing_path(self, ses_name: str, run_name: Optional[str]) -> Path:
        return self._get_base_sorting_path(ses_name, run_name) / "postprocessing"

    def _validate_derivatives_inputs(self):
        self._validate_inputs(
            "derivatives",
            self.get_derivatives_top_level_path,
            self.get_derivatives_sub_path,
            self.get_derivatives_ses_path,
            self.get_derivatives_run_path,
        )

    # Multiple Run Names
    # ----------------------------------------------------------------------------------

    def _make_run_name_from_multiple_run_names(self, run_names: List[str]) -> str:
        """
        Make a single run_name given a list of run names. This will use the
        first part of the first name and then add unique parts of the
        subsequent names to the string.

        Parameters
        ----------
        run_names : Union[List[str], str]
            A list of run names.

        Returns
        -------
        pp_run_name : str
            A single run name formed from the list of run names.
        """
        all_names = []
        for idx, name in enumerate(run_names):
            if idx == 0:
                all_names.extend(name.split("_"))
            else:
                split_name = name.split("_")
                new_name = [n for n in split_name if n not in all_names]
                all_names.extend(new_name)

        if "g0" in all_names:
            all_names.remove("g0")

        concat_run_name = "_".join(all_names)

        return concat_run_name

    # Sorting info
    # ----------------------------------------------------------------------------------

    def save_sorting_info(self, ses_name: str, run_name: str) -> None:
        """
        Save a sorting_info.yaml file containing a dictionary holding
        important information on the sorting. This is for provenance.
        Importantly, the preprocessing_info.yaml files for all
        preprocessed runs that were sorted are also loaded and
        re-saved.

        This is very important for PostprocessData in which the
        waveforms are extracted from the preprocessed data based on the
        results of the sorting. In this case it is critical the
        preprocessing data at the expected Path is the same that was
        used for sorting.
        """
        # Load preprocessing info to store for provenance
        preprocessing_info_paths = self.preprocessing_info_paths(ses_name, run_name)

        sorting_info: Dict = {"preprocessing": {}}

        for load_prepro_path in preprocessing_info_paths:
            pp_dict = utils.load_dict_from_yaml(load_prepro_path)
            self.update_two_layer_dict(
                sorting_info["preprocessing"],
                pp_dict["ses_name"],
                pp_dict["run_name"],
                value=pp_dict,
            )

        # Add sorting-specific information
        sorting_info["base_path"] = self.base_path.as_posix()
        sorting_info["sub_name"] = self.sub_name
        sorting_info["sessions_and_runs"] = self.sessions_and_runs
        sorting_info["sorted_ses_name"] = ses_name
        sorting_info["sorted_run_name"] = run_name
        sorting_info["sorter"] = self.sorter
        sorting_info["concatenate_sessions"] = self.concatenate_sessions
        sorting_info["concatenate_runs"] = self.concatenate_runs
        sorting_info["spikeinterface_version"] = si.__version__
        sorting_info["spikewrap_version"] = utils.spikewrap_version()
        sorting_info["datetime_created"] = utils.get_formatted_datetime()

        utils.dump_dict_to_yaml(
            self._get_sorting_info_path(ses_name, run_name), sorting_info
        )

    @property
    @abstractmethod
    def concatenate_sessions(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def concatenate_runs(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def preprocessing_info_paths(
        self,
        ses_name: str,
        run_name: str,
    ) -> List[Path]:
        raise NotImplementedError

    @abstractmethod
    def load_preprocessed_binary(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_sorting_sessions_and_runs(self):  # TODO: iterable!
        raise NotImplementedError

    @abstractmethod
    def get_preprocessed_recordings(
        self, ses_name: str, run_name: Optional[str]
    ) -> si.BaseRecording:
        raise NotImplementedError

    @abstractmethod
    def _get_base_sorting_path(self, ses_name: str, run_name: Optional[str]) -> Path:
        raise NotImplementedError


class ConcatenateSessions(SortingData):
    """ """

    @property
    def concatenate_sessions(self) -> bool:
        return True

    @property
    def concatenate_runs(self) -> bool:
        return True

    def load_preprocessed_binary(self) -> None:
        """"""
        recordings = self.initialise_preprocessed_recordings_dict()

        self.check_ses_or_run_folders_in_datetime_order()

        concat_run_recordings = []
        for ses_name in recordings.keys():
            concat_run_recordings.append(self._concatenate_runs(ses_name, recordings))
        self[self.concat_ses_name()] = concatenate_recordings(concat_run_recordings)

    def get_sorting_sessions_and_runs(self):  # TODO: type
        return [(self.concat_ses_name(), None)]

    def concat_ses_name(self) -> str:
        ses_names = list(self.sessions_and_runs.keys())
        return self._make_run_name_from_multiple_run_names(ses_names)

    def get_preprocessed_recordings(
        self, ses_name: str, run_name: Optional[str]
    ) -> si.BaseRecording:
        self.assert_names(ses_name, run_name)
        return self[self.concat_ses_name()]

    def _get_base_sorting_path(self, ses_name: str, run_name: Optional[str]) -> Path:
        """"""
        self.assert_names(ses_name, run_name)

        base_sorting_path = (
            self.get_derivatives_sub_path()
            / f"{self.sub_name}-sorting-concat"
            / self.concat_ses_name()  # TODO: centralise paths!!  # TODO: centralise
            / "ephys"
            / self.sorter
        )
        return base_sorting_path

    def preprocessing_info_paths(
        self, ses_name: str, run_name: Optional[str]
    ) -> List[Path]:
        """"""
        self.assert_names(ses_name, run_name)

        preprocessing_info_paths = []
        for pp_ses_name, pp_run_name in self.flat_sessions_and_runs():
            preprocessing_info_paths.append(
                self.get_preprocessing_info_path(pp_ses_name, pp_run_name)
            )

        return preprocessing_info_paths

    def assert_names(self, ses_name: str, run_name: Optional[str]) -> None:
        assert ses_name == self.concat_ses_name()
        assert run_name is None


class ConcatenateRuns(SortingData):
    """ """

    @property
    def concatenate_sessions(self) -> bool:
        return False

    @property
    def concatenate_runs(self) -> bool:
        return True

    def load_preprocessed_binary(self) -> None:
        """"""
        recordings = self.initialise_preprocessed_recordings_dict()

        for ses_name in self.sessions_and_runs.keys():
            concat_recording = self._concatenate_runs(ses_name, recordings)

            self.update_two_layer_dict(
                self, ses_name, self.concat_run_name(ses_name), concat_recording
            )

    def get_sorting_sessions_and_runs(self):  # TODO: type
        """"""
        sorting_sessions_and_runs = []
        for ses_name in self.sessions_and_runs.keys():
            sorting_sessions_and_runs.append((ses_name, self.concat_run_name(ses_name)))

        return sorting_sessions_and_runs

    def concat_run_name(self, ses_name: str) -> str:
        """ """
        if not len(self.sessions_and_runs[ses_name]) > 1:
            warnings.warn(
                f"Concatenate runs is true but only a single "
                f"run has been passed for sessions {ses_name}."
            )
        concat_run_name = self._make_run_name_from_multiple_run_names(
            self.sessions_and_runs[ses_name]
        )

        return concat_run_name

    def get_preprocessed_recordings(
        self, ses_name: str, run_name: Optional[str]
    ) -> si.BaseRecording:
        assert run_name == self.concat_run_name(ses_name)
        assert run_name is not None

        return self[ses_name][run_name]

    def _get_base_sorting_path(self, ses_name: str, run_name: Optional[str]) -> Path:
        assert run_name == self.concat_run_name(ses_name)
        assert run_name is not None

        base_sorting_path = (
            self.get_derivatives_sub_path()
            / ses_name
            / "ephys"  # TODO: combine with base paths   # TODO: centralise paths!!
            / f"{self.sub_name}-sorting-concat"
            / run_name
            / self.sorter
        )
        return base_sorting_path

    def preprocessing_info_paths(self, ses_name: str, run_name: str) -> List[Path]:
        """"""
        assert run_name == self.concat_run_name(ses_name)

        preprocessing_info_paths = []
        for pp_run_name in self.sessions_and_runs[ses_name]:
            preprocessing_info_paths.append(
                self.get_preprocessing_info_path(ses_name, pp_run_name)
            )
        return preprocessing_info_paths


class NoConcatenation(SortingData):
    """ """

    @property
    def concatenate_sessions(self) -> bool:
        return False

    @property
    def concatenate_runs(self) -> bool:
        return False

    def load_preprocessed_binary(self) -> None:
        recordings = self.initialise_preprocessed_recordings_dict()
        self.data = recordings

    def get_sorting_sessions_and_runs(self):  # TODO: type
        ordered_ses_names = list(
            chain(*[[ses] * len(runs) for ses, runs in self.items()])
        )
        ordered_run_names = list(chain(*[runs for runs in self.values()]))
        return list(zip(ordered_ses_names, ordered_run_names))

    def get_preprocessed_recordings(
        self, ses_name: str, run_name: Optional[str]
    ) -> si.BaseRecording:
        assert run_name is not None
        return self[ses_name][run_name]

    def _get_base_sorting_path(self, ses_name: str, run_name: Optional[str]) -> Path:
        assert run_name is not None
        # TODO: centralise paths!!# TODO: centralise paths!!# TODO: centralise paths!!
        return (
            self.get_derivatives_sub_path()
            / ses_name
            / "ephys"
            / run_name
            / self.sorter
        )

    def preprocessing_info_paths(self, ses_name: str, run_name: str) -> List[Path]:
        return [self.get_preprocessing_info_path(ses_name, run_name)]
