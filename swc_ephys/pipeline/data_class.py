import copy
import os
import pickle  # TODO: explore cPickle
from collections import UserDict
from collections.abc import ItemsView, KeysView, ValuesView
from pathlib import Path
from typing import Dict, Union, Optional

import spikeinterface as si
from spikeinterface.core.base import BaseExtractor

from ..utils import utils


class Data(UserDict):
    def __init__(
        self, base_path: Union[Path, str], sub_name: str, run_names: str, pp_steps: Optional[Dict] = None,
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

        run_name : the spikeglx run name (i.e. not including the gate index)

        pp_steps : preprocessing step dictionary, see swc_ephys/configs
        """
        super(Data, self).__init__()

        self.base_path = Path(base_path)
        self.rawdata_path = self.base_path / "rawdata"

        assert self.rawdata_path.is_dir(), (
            f"No data found at {self.rawdata_path}. \n"
            f"Raw data must be in a folder rawdata that resides within base_path"
        )

        self.sub_name = sub_name
        self.all_run_names = run_names
        self.all_run_paths = None  # Holds the full path to all runs used
        self.run_name = None   # This is the output run name used for concatenating multiple runs
        self.pp_steps = pp_steps
        self.data: Dict = {"0-raw": None}
        self.opts: Dict = {"0-raw": None}

        # TODO: this requires gate number to be known
        # which is passed at runtime. There is probably
        # better way to handle this.
        self.run_level_path = Path()  # TODO: new name I think this is output path now 

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

        self.handle_multiple_runs()  # TODO: change name this is key function even for single run

    # Load and Save --------------------------------------------------------------------

    def handle_multiple_runs(self):
        """
        """
        make_run_path = lambda name: self.base_path / "rawdata" / self.sub_name / f"{name}"  # TODO just use an actual function...

        if self.all_run_names == ["all"] or len(self.all_run_names) > 1:  # TOOD: rename as run_name

            search_run_paths = list((self.base_path / "rawdata" / self.sub_name).glob(f"*_g0")) # TODO: this is a dumb way to search? too dependent on g0?

            if self.all_run_names == ["all"]:  # TODO: change all_run_names back

                # if "all" always search by datetime
                search_run_paths_by_creation_time = copy.deepcopy(search_run_paths)  # TODO: fix
                search_run_paths_by_mod_time = copy.deepcopy(search_run_paths)

                search_run_paths_by_creation_time.sort(key=os.path.getctime)
                search_run_paths_by_mod_time.sort(key=os.path.getmtime)

                assert search_run_paths_by_creation_time == search_run_paths_by_mod_time, "Run file creation time and modification time do not match. " \
                                                                                           "Contact Joe as it is not clear what to do in this case."
                search_run_paths = search_run_paths_by_creation_time
            else:
                # if the user has specified runs, for now sanity-check they are in datetime order.
                # It is highly unlikely they will want to specify out of datetime order
                # givr an option to override this?
                search_run_paths_by_creation_time = copy.deepcopy(search_run_paths)
                search_run_paths_by_creation_time.sort(key=os.path.getctime)
                assert search_run_paths == search_run_paths_by_creation_time, "run names are not specified in time order. "

            search_run_names = [path_.stem for path_ in search_run_paths]  # to List[Path] to List[str]

            if self.all_run_names != ["all"]:  # TODO: test this case
                breakpoint()
                check_run_names = [f"{name}_g0" for name in self.all_run_names]
                search_run_names = [name for name in search_run_names if
                                      name in check_run_names]

            self.all_run_paths = [make_run_path(name) for name in search_run_names]  # TODO: we go from path to name, validate then back to path. Must be better logic here

            self.run_name = self.make_run_name_from_multiple_run_names(search_run_names)
        else:
            self.all_run_paths = [make_run_path(f"{self.all_run_names[0]}_g0")]
            self.run_name = self.all_run_names[0]

        assert len(self.all_run_paths) > 0, f"No runs found for {self.run_names}. Make sure to specify run_names without gate / trigger (e.g. no _g0)."
        
        check_all_run_paths = copy.deepcopy(self.all_run_paths)  # TODO: streamline this
        check_all_run_paths.sort(key=os.path.getctime)
        assert self.all_run_paths == check_all_run_paths, "TODO: something went wrong in processing path creation times"

        self.run_level_path = make_run_path(self.run_name)  # TODO _g0 suffix handling here is a bit fiddly and not clear, TOOD new name this is output path now

    def make_run_name_from_multiple_run_names(self, run_names):

        all_names = []
        for idx, name in enumerate(run_names):
            if idx == 0:
                all_names.extend(name.split("_"))
            else:
                split_name = name.split("_")  # TODO: how to handle _g0 here
                new_name = [n for n in split_name if n not in all_names]  # TODO: is this very dumb?
                all_names.extend(new_name)

        if "g0" in all_names:
            all_names.remove("g0")

        run_name =  "_".join(all_names)

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

    def set_sorter_output_paths(self, sorter):
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
