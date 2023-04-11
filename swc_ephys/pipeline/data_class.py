import os
import pickle  # TODO: explore cPickle
from collections import UserDict
from collections.abc import ItemsView, KeysView, ValuesView
from pathlib import Path
from typing import Dict, Union

import spikeinterface as si
from spikeinterface.extractors import BaseExtractor

from ..utils import utils


class Data(UserDict):
    def __init__(
        self, base_path: Union[Path, str], sub_name: str, run_name: str, pp_steps: Dict
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
        self.run_name = run_name
        self.pp_steps = pp_steps
        self.data: Dict = {"0-raw": None}
        self.opts: Dict = {"0-raw": None}

        # TODO: this requires gate number to be known
        # which is passed at runtime. There is probably
        # better way to handle this.
        self.run_level_path = Path()

        # These are dynamically set by the sorter
        # chosen at runtime.
        self.preprocessed_output_path = Path()
        self.sorter_output_path = Path()
        self.waveform_output_path = Path()
        self.preprocessed_data_class_path = Path()
        self.preprocessed_binary_data_path = Path()
        self.waveforms_output_path = Path()
        self.quality_metrics_path = Path()

    # Load and Save --------------------------------------------------------------------

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
