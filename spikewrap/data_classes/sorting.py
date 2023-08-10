import copy
import os
import warnings
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import spikeinterface as si
from spikeinterface import concatenate_recordings

from ..utils import utils
from .base import BaseUserDict


class SortingData(BaseUserDict):
    """
    Class to organise the sorting of preprocessed data. Handles the
    paths to preprocessed data, sorted output and all post-processing
    steps.

    This class should be agnostic to any rawdata and the PreprocessingData
    class, and concerned only with preprocessed data onwards.

    Parameters
    ----------
    preprocessed_data_path : Union[str, Path]
        Path to the preprocessed data output path, that contains
        the dumped si_recording and .yaml file of PreprocessingData
        attributes.

    Notes
    -----
    This class matches the data-access signature of PreprocessData
    for compatibility with `visualise()` methods. This pattern
    does not really make sense for this class as it most likely will
    only ever contain a single data attribute.This includes
    some jiggery-pokery with the `self.init_data_key`. This is not a nice
    pattern and can be improved on refactoring of `visualise.py`.
    """

    def __init__(
        self, base_path, sub_name, run_names, sorter: str, concat_for_sorting: bool
    ):
        super(SortingData, self).__init__(base_path, sub_name, run_names)

        self.concat_for_sorting = concat_for_sorting
        self.sorter = sorter

        self._check_preprocessing_exists()

        self.data: Dict = {}
        self.preprocessing_info_paths = {}
        self._load_preprocessed_binary()

    def _top_level_folder(self):
        return "derivatives"

    def _check_preprocessing_exists(self):
        """ """

        def error_message(path_):
            return (
                f"The run folder {path_.stem} cannot be found at "
                f"file path {path_.parent}."
            )

        for run_name in self.run_names:
            assert (
                prepro_path := self.get_run_path(run_name) / "preprocessed"
            ).is_dir(), error_message(prepro_path)

            assert (
                recording_path := prepro_path / "si_recording"
            ).is_dir(), error_message(recording_path)

    def _load_preprocessed_binary(self):
        """
        Use SpikeInterface to load the binary-data into a recording object.
        """
        # Load the preprocessing recordings
        recordings = {}
        for run_name in self.run_names:
            recordings[run_name] = si.load_extractor(
                self._get_pp_binary_data_path(run_name)
            )

        # Set the dict data to the separate or concatenated recordings
        if not self.concat_for_sorting:
            self.data = recordings
        else:
            concatenated_recording = self._concatenate_si_recording(recordings)
            self.data = {self.concat_run_name(): concatenated_recording}

    def _concatenate_si_recording(self, recordings):
        """ """
        loaded_prepro_run_names, recordings_list = zip(*recordings.items())

        concatenated_recording = concatenate_recordings(recordings_list)

        # Perform some checks before returning.
        assert loaded_prepro_run_names == tuple(
            self.run_names
        ), "Something has gone wrong in the `run_names` ordering."

        if not self._run_names_are_in_datetime_order("creation"):
            warnings.warn(
                "The runs provided are not in creation datetime order.\n"
                "They will be concatenated in the order provided."
            )

        utils.message_user(
            f"Concatenating runs in the order: " f"{loaded_prepro_run_names}"
        )

        return concatenated_recording

    def _run_names_are_in_datetime_order(
        self, creation_or_modification: str = "creation"
    ) -> bool:
        """
        Assert whether a list of paths are in order. By default, check they are
        in order by creation date. Can also check if they are ordered by
        modification date.

        Parameters
        ----------
        creation_or_modification : str
            If "creation", check the list of paths are ordered by creation datetime.
            Otherwise if "modification", check they are sorterd by modification
            datetime.

        Returns
        -------
        is_in_time_order : bool
            Indicates whether `list_of_paths` was in creation or modification time
            order.
            depending on the value of `creation_or_modification`.
        """
        assert creation_or_modification in [
            "creation",
            "modification",
        ], "creation_or_modification must be 'creation' or 'modification."

        filter: Callable
        filter = (
            os.path.getctime
            if creation_or_modification == "creation"
            else os.path.getmtime
        )

        list_of_paths = [self.get_run_path(run_name) for run_name in self.run_names]

        list_of_paths_by_time = copy.deepcopy(list_of_paths)
        list_of_paths_by_time.sort(key=filter)

        is_in_time_order = list_of_paths == list_of_paths_by_time

        return is_in_time_order

    def save_sorting_info(self, run_name: Optional[str] = None):
        """"""
        # Load preprocessing_info for provenance
        if run_name is None:
            assert self.concat_for_sorting is True
            run_names_to_load = self.run_names
        else:
            assert self.concat_for_sorting is False
            run_names_to_load = [run_name]

        preprocessing_info = {"preprocessing": {}}

        for load_prepro_run_name in run_names_to_load:  # TODO: naming!
            preprocessing_info["preprocessing"][
                load_prepro_run_name
            ] = utils.load_dict_from_yaml(
                self._get_preprocessing_info_path(load_prepro_run_name)
            )

        sorted_run_name = (
            self.concat_run_name() if self.concat_for_sorting else run_name
        )

        preprocessing_info["base_path"] = self.base_path.as_posix()
        preprocessing_info["sub_name"] = self.sub_name
        preprocessing_info["run_names"] = self.run_names
        preprocessing_info["concat_for_sorting"] = self.concat_for_sorting
        preprocessing_info["sorter"] = self.sorter
        preprocessing_info["sorted_run_name"] = sorted_run_name

        output_path = self.get_sorting_path(run_name) / utils.canonical_names(
            "sorting_yaml"
        )

        utils.dump_dict_to_yaml(output_path, preprocessing_info)

    def get_preprocessed_recording(self, run_name: Optional[str] = None):
        """"""
        breakpoint()
        if self.concat_for_sorting:
            assert run_name is None
            recording = self[self.concat_run_name()]
        else:
            assert isinstance(run_name, str)
            recording = self[run_name]

        return recording

    def get_all_run_names(self):
        if self.concat_for_sorting:
            run_names = [None]
        else:
            run_names = self.run_names
        return run_names

    # Paths ----------------------------------------------------------------------------

    def _get_base_sorting_path(self, run_name: Optional[str] = None) -> None:
        """ """
        sub_folder = self.base_path / "derivatives" / self.sub_name
        if self.concat_for_sorting:
            assert run_name is None
            base_sorting_path = (
                sub_folder
                / f"{self.sub_name}-sorting-concat"
                / self.concat_run_name()
                / self.sorter
            )
        else:
            assert run_name is not None
            base_sorting_path = sub_folder / run_name / self.sorter

        return base_sorting_path

    def get_sorting_path(self, run_name: Optional[str] = None):
        return self._get_base_sorting_path(run_name) / "sorting"

    def get_sorter_output_path(self, run_name: Optional[str] = None):
        return self.get_sorting_path(run_name) / "sorter_output"

    def get_postprocessing_path(self, run_name: Optional[str] = None):
        return self._get_base_sorting_path(run_name) / "postprocessing"

    # Handle Multiple Runs -------------------------------------------------------------

    def concat_run_name(
        self,
    ) -> Tuple[List[Path], List[str], str]:
        """
        The run_names may be a single run, or a list of runs to process.
        Return a list of paths to the runs found on the system. enforces
        that the runs are in datetime order.

        Returns
        -------
        run_names : List[str]
            List of run names (folder names within the subject level folder)
            to be used in the pipeline.

        concat_run_name : str
            A name consisting of the ordered combination of all run names
            (see self.make_run_name_from_multiple_run_names)
        """
        assert len(self.run_names) > 1, (
            f"Concatenate for sorting (`concat_for_sorting`) is "
            f"true but only a single run"
            f"has been passed: {self.run_names}."
        )

        concat_run_name = self._make_run_name_from_multiple_run_names(self.run_names)

        return concat_run_name

    # Multiple run path naming ---------------------------------------------------------

    @staticmethod
    def _make_run_name_from_multiple_run_names(run_names: List[str]) -> str:
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
