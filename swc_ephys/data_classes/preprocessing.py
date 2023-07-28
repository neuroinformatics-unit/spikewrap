import fnmatch
import os
import shutil
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import yaml

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
        super(PreprocessingData, self).__init__()

        self.top_level_folder = "rawdata"
        self.init_data_key = "0-raw"

        self.base_path, checked_run_names, self.rawdata_path = self.validate_inputs(
            base_path,
            sub_name,
            run_names,
        )

        self.sub_name = sub_name

        (
            self.all_run_paths,
            self.all_run_names,
            self.pp_run_name,
        ) = self.create_runs_from_single_or_multiple_run_names(checked_run_names)

        self.pp_steps: Optional[Dict] = None
        self.data: Dict = {"0-raw": None}
        self.sync = None

        self.preprocessed_data_path = Path()
        self._pp_data_attributes_path = Path()
        self._pp_binary_data_path = Path()
        self._sync_channel_data_path = Path()
        self._set_preprocessing_output_path()

    # Handle Multiple Runs -------------------------------------------------------------

    def create_runs_from_single_or_multiple_run_names(
        self,
        run_names: List[str],
    ) -> Tuple[List[Path], List[str], str]:
        """
        The run_names may be a single run, or a list of runs to process.
        Return a list of paths to the runs found on the system. enforces
        that the runs are in datetime order.

        Parameters
        ----------
        run_names : Union[List[str], str]
            The SpikeGLX run name (i.e. not including the gate index) or
            list of run names.

        Returns
        -------
        all_run_paths : List[Path]
            List of full filepaths for all runs used in the pipeline.

        all_run_names : List[str]
            List of run names (folder names within the subject level folder)
            to be used in the pipeline.

        run_name : str
            The name of the run used in the derivatives. For a single run,
            this will be the name of the run. When run_names is a list of run
            names, this will be an amalgamation of all run names
            (see self.make_run_name_from_multiple_run_names)
        """
        if len(run_names) > 1:
            all_run_paths, run_name = self.get_multi_run_names_paths(run_names)
        else:
            run_name = run_names[0]
            all_run_paths = [self.get_sub_folder_path() / f"{run_name}_g0"]

        assert len(run_names) > 0, (
            f"No runs found for {run_names}. "
            f"Make sure to specify run_names without gate / trigger (e.g. no _g0)."
        )

        all_run_names = [path_.stem for path_ in all_run_paths]

        for run_path in all_run_paths:
            assert run_path.is_dir(), (
                f"The run folder {run_path.stem} cannot be found at "
                f"file path {run_path.parent}"
            )

        utils.message_user(f"The order of the loaded runs is:" f"{all_run_names}")

        return all_run_paths, all_run_names, run_name

    def get_multi_run_names_paths(
        self,
        run_names: List[str],
    ) -> Tuple[List[Path], str]:
        """
        Get the paths to the runs when there is more than one run specified.
        If it is a list of run names, they are searched, checked exist and
        assert in datetime order.

        Parameters
        ----------
        run_names : Union[List[str], str]
            The spikeglx run name (i.e. not including the gate index) or
            list of run names.

        Returns
        -------
        all_run_paths : List[Path]
            List of full filepaths for all runs used in the pipeline.

        all_run_names : List[str]
            List of run names (folder names within the subject level folder)
            to be used in the pipeline.

        run_name : str
            The name of the run used in the derivatives. For a single run,
            this will be the name of the run. When run_names is a list of run names,
            this will be an amalgamation of all run names
            (see self.make_run_name_from_multiple_run_names)
        """
        all_run_paths = [
            self.get_sub_folder_path() / f"{name}_g0" for name in run_names
        ]

        if not utils.list_of_files_are_in_datetime_order(all_run_paths, "creation"):
            warnings.warn(
                "The runs provided are not in creation datetime order.\n"
                "They will be concatenated in the order provided."
            )

        pp_run_name = self.make_run_name_from_multiple_run_names(run_names)

        return all_run_paths, pp_run_name

    def make_run_name_from_multiple_run_names(self, run_names: List[str]) -> str:
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

        pp_run_name = "_".join(all_names)

        return pp_run_name

    def get_expected_sorter_path(self, sorter: str) -> Path:
        return utils.make_sorter_base_output_path(
            self.base_path, self.sub_name, self.pp_run_name, sorter
        )

    # Load and Save --------------------------------------------------------------------

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

    def save_all_preprocessed_data(self, overwrite: bool = False) -> None:
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
            if self.preprocessed_data_path.is_dir():
                shutil.rmtree(self.preprocessed_data_path)
        self._save_data_class()
        self._save_preprocessed_binary()
        self._save_sync_channel()

    def _save_preprocessed_binary(self) -> None:
        """
        Save the fully preprocessed data (i.e. last step in the
        preprocessing chain) to binary file. This is required for sorting.
        """
        recording, __ = utils.get_dict_value_from_step_num(self, "last")
        recording.save(folder=self._pp_binary_data_path, chunk_memory="10M")

    def _save_sync_channel(self) -> None:
        """ """
        assert self.sync is not None, "Sync channel on PreprocessData is None"
        self.sync.save(folder=self._sync_channel_data_path, chunk_memory="10M")

    def _save_data_class(self) -> None:
        """
        Save the key attributes of this class to a .yaml file.
        """
        assert self.pp_steps is not None, "type narrow `pp_steps`."

        utils.cast_pp_steps_values(self.pp_steps, "list")

        attributes_to_save = {
            "base_path": self.base_path.as_posix(),
            "sub_name": self.sub_name,
            "pp_run_name": self.pp_run_name,
            "pp_steps": self.pp_steps,
            "all_run_paths": [path_.as_posix() for path_ in self.all_run_paths],
            "all_run_names": [name for name in self.all_run_names],
            "preprocessed_data_path": self.preprocessed_data_path.as_posix(),
            "_pp_binary_data_path": self._pp_binary_data_path.as_posix(),
            "_pp_data_attributes_path": self._pp_data_attributes_path.as_posix(),
            "_sync_channel_data_path": self._sync_channel_data_path.as_posix(),
        }
        if not self.preprocessed_data_path.is_dir():
            os.makedirs(self.preprocessed_data_path)

        with open(
            self._pp_data_attributes_path,
            "w",
        ) as attributes:
            yaml.dump(attributes_to_save, attributes, sort_keys=False)

    # Handle Paths ---------------------------------------------------------------------

    def _set_preprocessing_output_path(self) -> None:
        """
        Set the folder tree where preprocessing output will be
        saved. This is canonical and should not change.

        TODO: move this to a canonical_filepaths module.
        """

        run_path = (
            self.base_path / "derivatives" / self.sub_name / f"{self.pp_run_name}"
        )
        self.preprocessed_data_path = run_path / "preprocessed"

        self._pp_data_attributes_path = (
            self.preprocessed_data_path / utils.canonical_names("preprocessed_yaml")
        )
        self._pp_binary_data_path = self.preprocessed_data_path / "si_recording"
        self._sync_channel_data_path = run_path / "sync_channel"

    def get_sub_folder_path(self) -> Path:
        """
        Get the path to the rawdata subject folder.

        Returns
        -------
        sub_folder_path : Path
            Path to the self.sub_name folder in the `rawdata` path folder.
        """
        sub_folder_path = Path(self.base_path / self.top_level_folder / self.sub_name)
        return sub_folder_path

    # Validate Inputs ------------------------------------------------------------------

    def validate_inputs(
        self, base_path: Union[str, Path], sub_name: str, run_names: Union[str, list]
    ) -> Tuple[Path, List[str], Path]:
        """
        Check the rawdata path, subject path exists and ensure run_names
        is a list of strings without SpikeGLX gate number of the run names.

        Parameters
        ----------
        base_path : Union[str, Path]
            Path to the base folder in which `rawdata` folder containing
            all rawdata (i.e. list of subject names) are held.

        sub_name : str
            'subject' name to preprocess data for.

        run_names : List[str]
            List of run names to process, in order they should be
            processed / concatenated.

        Returns
        -------
        base_path : Path
            `base_path` definitely as a Path object.

        run_names : List[str]
            Validated `run_names` as a List.

        rawdata_path : Path
            Path to the canonical `rawdata` path required for
            future processing.
        """
        base_path = Path(base_path)
        rawdata_path = base_path / self.top_level_folder

        assert (rawdata_path / sub_name).is_dir(), (
            f"Subject directory not found. {sub_name} "
            f"is not a folder in {rawdata_path}"
        )

        assert rawdata_path.is_dir(), (
            f"Ensure there is a folder in base path called 'rawdata'.\n"
            f"No rawdata directory found at {rawdata_path}\n"
            f"where subject-level folders are placed."
        )
        if not isinstance(run_names, list):
            run_names = [run_names]

        for name in run_names:
            assert "g0" not in name.split("_"), (
                f"gate index should not be on the run name. Remove _g0 from\n" f"{name}"
            )

        for name in run_names:
            gate_idx_in_name = fnmatch.filter(name.split("_"), "g?")
            assert len(gate_idx_in_name) == 0, (
                f"Gate with index larger than 0 is not supported. This is found "
                f"in run name {name}. "
            )
        return base_path, run_names, rawdata_path
