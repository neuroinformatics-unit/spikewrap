import fnmatch
import os
import pickle  # TODO: explore cPickle
from collections import UserDict
from collections.abc import ItemsView, KeysView, ValuesView
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import spikeinterface as si
from spikeinterface.core.base import BaseExtractor

from ..utils import utils


class Data(UserDict):
    def __init__(
        self,
        base_path: Union[Path, str],
        sub_name: str,
        run_names: str,
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

        base_path : path where the rawdata folder containing subjects

        sub_name : subject to preprocess. The subject top level dir should reside in
                   base_path/rawdata/

        run_names : the spikeglx run name (i.e. not including the gate index) or
                    list of run names, or keyword "all".

        pp_steps : preprocessing step dictionary, see swc_ephys/configs
        """
        super(Data, self).__init__()

        self.base_path, checked_run_names, self.rawdata_path = self.validate_inputs(
            run_names, base_path
        )

        self.sub_name = sub_name

        (
            self.run_level_path,
            self.all_run_paths,
            self.all_run_names,
            self.run_name,
        ) = self.create_runs_from_single_or_multiple_run_names(checked_run_names)

        utils.message_user(f"The order of the loaded runs is:" f"{self.all_run_names}")

        self.pp_steps = pp_steps
        self.data: Dict = {"0-raw": None}
        self.opts: Dict = {"0-raw": None}

        # These are dynamically set by the sorter
        # chosen at runtime.
        self.preprocessed_output_path = Path()
        self.sorter_base_output_path = Path()
        self.sorter_run_output_path = Path()
        self.waveform_output_path = Path()
        self.preprocessed_data_class_path = Path()
        self.preprocessed_binary_data_path = Path()
        self.waveforms_output_path = Path()
        self.quality_metrics_path = Path()

    def validate_inputs(
        self, run_names: Union[str, list], base_path: Union[str, Path]
    ) -> Tuple[Path, List[str], Path]:
        """
        Check the rawdata path exists and ensure run_names
        is a list of strings.
        """
        base_path = Path(base_path)
        rawdata_path = base_path / "rawdata"

        assert rawdata_path.is_dir(), (
            f"Ensure there is a folder in base path called 'rawdata'.\n"
            f"No rawdata directory found at {rawdata_path}\n"
            f"where subject-level folders are placed."
        )
        if not isinstance(run_names, list):
            run_names = [run_names]
            assert not (
                "all" in run_names and len(run_names) != 1
            ), "'all' run name must be used on its own."

        for name in run_names:
            assert "g0" not in name.split("_"), (
                f"gate index should not be on the run name. Remove _g0 from\n" f"{name}"
            )

        for name in run_names:  # TODO: clean_up ...
            gate_idx_in_name = fnmatch.filter(name.split("_"), "g?")
            assert len(gate_idx_in_name) == 0, (
                f"Gate with index larger than 0 is not supported. This is found "
                f"in run name {name}. "
            )

        return base_path, run_names, rawdata_path

    # Load and Save --------------------------------------------------------------------

    def create_runs_from_single_or_multiple_run_names(
        self,
        run_names: List[str],
    ) -> Tuple[Path, List[Path], List[str], str]:
        """ """
        if run_names == ["all"] or len(run_names) > 1:
            all_run_paths, run_name = self.get_multi_run_names_paths(run_names)
        else:
            all_run_paths = [self.make_run_path(f"{run_names[0]}_g0")]
            run_name = run_names[0]

        assert len(run_names) > 0, (
            f"No runs found for {run_names}. "
            f"Make sure to specify run_names without gate / trigger (e.g. no _g0)."
        )

        # Just a sign-off confidence check can remove later
        utils.assert_list_of_files_are_in_datetime_order(all_run_paths)
        run_level_path = self.make_run_path(run_name)

        all_run_names = [path_.stem for path_ in all_run_paths]

        return run_level_path, all_run_paths, all_run_names, run_name

    def get_multi_run_names_paths(
        self,
        run_names: List[str],
    ) -> Tuple[List[Path], str]:
        """ """
        search_run_paths = list(
            Path(self.base_path / "rawdata" / self.sub_name).glob("*_g0")
        )

        if run_names == ["all"]:
            search_run_paths = utils.sort_list_of_paths_by_datetime_order(
                search_run_paths
            )
            utils.assert_list_of_files_are_in_datetime_order(
                search_run_paths, "modification"
            )
        else:
            if run_names != ["all"]:
                check_run_names = [f"{name}_g0" for name in run_names]
                search_run_paths = [
                    name for name in search_run_paths if name.stem in check_run_names
                ]

            utils.assert_list_of_files_are_in_datetime_order(
                search_run_paths, "creation"
            )

        all_run_paths = search_run_paths

        run_name = self.make_run_name_from_multiple_run_names(run_names)

        return all_run_paths, run_name

    def make_run_name_from_multiple_run_names(self, run_names: List[str]) -> str:
        """
        TODO
        ----
        This is somewhat experimental, need to see
        a) how this works generally
        b) how to handle _g0 (does it make sense to have on output?

        In general this won't mess anything up, just may lead to some unintuitive
        output run names
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

        run_name = "_".join(all_names)

        return run_name

    def save_all_preprocessed_data(self):
        self.save_preprocessed_binary()
        self.save_data_class()

    def save_preprocessed_binary(self):
        """
        Will error if path already exists
        """
        recording, __ = utils.get_dict_value_from_step_num(self, "last")
        recording.save(folder=self.preprocessed_binary_data_path)

    def load_preprocessed_binary(self) -> BaseExtractor:
        return si.load_extractor(self.preprocessed_binary_data_path)

    def save_data_class(self):
        print("CALLED {self.preprocessed_output_path}")
        if not self.preprocessed_output_path.is_dir():
            os.makedirs(self.preprocessed_output_path)

        with open(self.preprocessed_data_class_path, "wb") as file:
            pickle.dump(self, file, pickle.HIGHEST_PROTOCOL)

    # Handle Paths ---------------------------------------------------------------------

    def set_preprocessing_output_path(self):
        assert (
            self.run_level_path is not None
        ), "must set run_level_path before sorter_output_path"

        self.preprocessed_output_path = (
            self.base_path
            / "derivatives"
            / self.run_level_path.relative_to(self.rawdata_path)
            / "preprocessed"
        )
        self.preprocessed_data_class_path = (
            self.preprocessed_output_path / "data_class.pkl"
        )
        self.preprocessed_binary_data_path = (
            self.preprocessed_output_path / "si_recording"
        )

    def set_sorter_output_paths(self, sorter: str):
        """ """
        assert (
            self.run_level_path is not None
        ), "must set run_level_path before sorter_output_path"

        self.sorter_base_output_path = (
            self.base_path
            / "derivatives"
            / self.run_level_path.relative_to(self.rawdata_path)
            / f"{sorter}-sorting"
        )
        # canonical name, is where spikeinterface automatically saves sorter output
        self.sorter_run_output_path = self.sorter_base_output_path / "sorter_output"

        self.waveforms_output_path = self.sorter_base_output_path / "waveforms"
        self.quality_metrics_path = self.sorter_base_output_path / "quality_metrics.csv"

    # UserDict Overrides ---------------------------------------------------------------

    def keys(self) -> KeysView:
        return self.data.keys()

    def items(self) -> ItemsView:
        return self.data.items()

    def values(self) -> ValuesView:
        return self.data.values()

    # ----------------------------------------------------------------------------------

    def make_run_path(self, run_name: str) -> Path:
        return self.base_path / "rawdata" / self.sub_name / f"{run_name}"

    def get_probe_group_num(self):
        """
        This is shank num

        TODO
        ---
        This is getting out of scope for this class, which should really be
        file-path related. Understand how shank index on the probe property
        maps to real-world shank
        """
        num_groups = np.unique(self["0-raw"].get_property("group")).size
        return num_groups
