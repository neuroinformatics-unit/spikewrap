import fnmatch
import os
import shutil
import warnings
from collections import UserDict
from collections.abc import ItemsView, KeysView, ValuesView
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import spikeinterface as si
import yaml
from spikeinterface.core.base import BaseExtractor

from ..utils import utils

# PreprocessData
# TODO: these classes will be extremely similar, inherit from common
# base abstract class.
# TODO: actually, completely separate the responsibilities
# of these classes and have PreprocessData an attribute of SortingData.


class PreprocessData(UserDict):
    def __init__(
        self,
        base_path: Union[Path, str],
        sub_name: str,
        run_names: Union[List[str], str],
        pp_steps: Optional[Dict] = None,
    ):
        """
        Dictionary to store spikeinterface preprocessing objects. These are
        lazy and preprocessing only run when the recording.get_traces() is
        called, or the data is saved to binary.

        Details on the preprocessing steps are held in the dictionary keys e.g.
        e.g. 0-raw, 1-raw-bandpass_filter, 2-raw_bandpass_filter-common_average

        recording objects are held in the value.

        The class also contains information on the path. The paths to the
        raw_data file are stored based on the variables set when the class
        was initialised. The derivatives paths are generated on the fly
        (e.g. set_sorter_output_paths) so that different sorters can be used
        dynamically.

        The class also contains methods for writing the class itself and
        spikeinterface recordings to disk, as required for sorting.

        Parameters
        ----------

        base_path : Union[Path, str]
            path where the rawdata folder containing subjects

        sub_name : str
            subject to preprocess. The subject top level dir should reside in
            base_path/rawdata/

        run_names : Union[List[str], str]
            the spikeglx run name (i.e. not including the gate index) or
            list of run names.

        pp_steps : Optional[Dict]
            preprocessing step dictionary, see swc_ephys/configs
        """
        super(PreprocessData, self).__init__()

        self.top_level_folder = "rawdata"
        self.init_data_key = "0_raw"

        self.base_path, checked_run_names, self.rawdata_path = self.validate_inputs(
            run_names,
            base_path,
            sub_name,
        )

        self.sub_name = sub_name

        (
            self.all_run_paths,
            self.all_run_names,
            self.pp_run_name,
        ) = self.create_runs_from_single_or_multiple_run_names(checked_run_names)

        utils.message_user(f"The order of the loaded runs is:" f"{self.all_run_names}")

        self.pp_steps = pp_steps
        self.data: Dict = {"0-raw": None}
        self.opts: Dict = {"0-raw": None}  # TODO rename

        self.preprocessed_output_path = Path()
        self.preprocessed_data_class_path = Path()
        self.preprocessed_binary_data_path = Path()
        self.set_preprocessing_output_path()

    # Handle Multiple Runs -------------------------------------------------------------
    def load_preprocessed_binary(self) -> BaseExtractor:
        """
        Use SpikeInterface to load the binary-data into a
        recording object.
        """
        return si.load_extractor(self.preprocessed_binary_data_path)

    def create_runs_from_single_or_multiple_run_names(
        self,
        run_names: List[str],
    ) -> Tuple[List[Path], List[str], str]:
        """
        The run_names may be a single run, or a list of
        runs to process. Return a list of paths to the runs found on the system.
        enforces that the runs are in datetime order.

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
        if len(run_names) > 1:
            all_run_paths, run_name = self.get_multi_run_names_paths(run_names)
        else:
            all_run_paths = [self.make_run_path(f"{run_names[0]}_g0")]
            run_name = run_names[0]

        assert len(run_names) > 0, (
            f"No runs found for {run_names}. "
            f"Make sure to specify run_names without gate / trigger (e.g. no _g0)."
        )

        all_run_names = [path_.stem for path_ in all_run_paths]

        return all_run_paths, all_run_names, run_name

    def get_multi_run_names_paths(
        self,
        run_names: List[str],
    ) -> Tuple[List[Path], str]:
        """
        Get the paths to the runs when there is more that one run specified.
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

        for path_ in all_run_paths:
            assert path_.is_dir(), f"No run folder found at {path_}"

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

    # Load and Save --------------------------------------------------------------------

    def save_all_preprocessed_data(self, overwrite: bool = False) -> None:
        """
        Save the preprocessed output data to binary, as well
        as this class as a .pkl file. Both are saved in a folder called
        'preprocessed' in derivatives/<sub_name>/<pp_run_name>
        """
        if overwrite:
            if self.preprocessed_output_path.is_dir():
                shutil.rmtree(self.preprocessed_output_path)
        self._save_data_class()
        self._save_preprocessed_binary()

    def _save_preprocessed_binary(self) -> None:
        """
        Save the fully preprocessed data (i.e. last step in the preprocessing
        chain) to binary file. This is required for sorting.
        """
        recording, __ = utils.get_dict_value_from_step_num(self, "last")
        recording.save(folder=self.preprocessed_binary_data_path, chunk_memory="10M")

    def _save_data_class(self) -> None:
        """
        Save this data class as a .pkl file.
        """
        utils.cast_pp_steps_values(self.pp_steps, "list")

        attributes_to_save = {
            "base_path": self.base_path.as_posix(),
            "sub_name": self.sub_name,
            "pp_run_name": self.pp_run_name,
            "pp_steps": self.pp_steps,
            "all_run_paths": [path_.as_posix() for path_ in self.all_run_paths],
            "all_run_names": [name for name in self.all_run_names],
            "preprocessed_output_path": self.preprocessed_output_path.as_posix(),
        }
        if not self.preprocessed_output_path.is_dir():
            os.makedirs(self.preprocessed_output_path)

        with open(
            self.preprocessed_output_path / "preprocess_data_attributes.yaml", "w"
        ) as attributes:  # TODO: save filename in config somewhere
            yaml.dump(attributes_to_save, attributes, sort_keys=False)

    # Handle Paths ---------------------------------------------------------------------

    def set_preprocessing_output_path(self) -> None:
        """
        Set the canonical folder names for the output data
        (in derivatives).
        """
        self.preprocessed_output_path = (
            self.base_path
            / "derivatives"
            / self.sub_name
            / f"{self.pp_run_name}"
            / "preprocessed"
        )
        self.preprocessed_data_class_path = (
            self.preprocessed_output_path / "data_class.pkl"
        )
        self.preprocessed_binary_data_path = (
            self.preprocessed_output_path / "si_recording"
        )

    def make_run_path(self, run_name: str) -> Path:
        """
        Get the path to the rawdata ephys run for the subject,
        """
        return self.get_sub_folder_path() / f"{run_name}"

    def get_sub_folder_path(self):
        """
        Get the path to the rawdata subject folder.
        """
        return Path(self.base_path / self.top_level_folder / self.sub_name)

    # UserDict Overrides ---------------------------------------------------------------

    def keys(self) -> KeysView:
        return self.data.keys()

    def items(self) -> ItemsView:
        return self.data.items()

    def values(self) -> ValuesView:
        return self.data.values()

    # Validate Inputs ------------------------------------------------------------------

    def validate_inputs(  # TODO: extend this to derivatives...
        self, run_names: Union[str, list], base_path: Union[str, Path], sub_name: str
    ) -> Tuple[Path, List[str], Path]:
        """
        Check the rawdata path exists and ensure run_names
        is a list of strings.
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

    # Misc. ----------------------------------------------------------------------------

    def get_probe_group_num(self) -> int:
        """
        This is shank num

        TODO
        ---
        This is getting out of scope for this class, which should really be
        file-path related. Understand how shank index on the probe property
        maps to real-world shank
        """
        num_groups = np.unique(self[self.init_data_key].get_property("group")).size
        return num_groups


class SortingData(PreprocessData):
    # super UserDict only,
    def __init__(self, base_path: Union[Path, str], sub_name: str, pp_run_name: str):
        """ """
        super(SortingData, self)  # no init, see how well this works.

        # TODO: I think will be cool to have rawdata as an optional attribute here
        # for provenance on generation. Will be able to get original
        # rawdata paths at least.
        self.top_level_folder = "derivatives"
        self.init_data_key = "0_preprocessed"  # TODO: this is not nice

        self.base_path = base_path
        self.sub_name = sub_name
        self.pp_run_name = pp_run_name

        self.all_run_names = [
            self.pp_run_name
        ]  # TODO: hacky wor-around for visualise.py

        self.preprocessed_output_path = Path()
        self.preprocessed_data_class_path = Path()
        self.preprocessed_binary_data_path = Path()
        self.set_preprocessing_output_path()

        self.sorter_base_output_path = Path()
        self.sorter_run_output_path = Path()
        self.waveforms_output_path = Path()
        self.quality_metrics_path = Path()

        # TODO: check this naming, only for consistency with
        #  visualise_preprocessing_output
        self.data = {"0_preprocessed": None}
        # self.set_sorter_output_paths(sorter)  TODO: do this outside of class, think this is intutiive...

    def load_preprocessed_binary(self, concatenate: bool = True) -> BaseExtractor:
        """
        Use SpikeInterface to load the binary-data into a
        recording object.
        """
        if not self.preprocessed_binary_data_path.is_dir():
            raise FileNotFoundError(
                f"No preprocessed SI binary-containing folder "
                f"found at {self.preprocessed_binary_data_path}."
            )  # TODO: add on passing custom base_path
        recording = si.load_extractor(self.preprocessed_binary_data_path)

        if concatenate:
            recording = utils.concatenate_runs(recording)

        self.data["0_preprocessed"] = recording

    def set_sorter_output_paths(self, sorter: str) -> None:
        """
        Set the sorter-specific output paths. The same data may be
        sorted multiple times by different sorters.

        sort_base_output_path : str
            canonical name, is where spikeinterface
            automatically saves sorter output
        """
        self.sorter_base_output_path = (
            self.base_path
            / "derivatives"
            / self.sub_name
            / f"{self.pp_run_name}"
            / f"{sorter}-sorting"
        )

        self.sorter_run_output_path = self.sorter_base_output_path / "sorter_output"
        self.waveforms_output_path = self.sorter_base_output_path / "waveforms"
        self.quality_metrics_path = self.sorter_base_output_path / "quality_metrics.csv"
