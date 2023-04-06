from collections import UserDict
from collections.abc import ItemsView, KeysView, ValuesView
import pickle  # TODO: explore cPickle
import os
import utils
import spikeinterface as si
from pathlib import Path

class Data(UserDict):
    def __init__(self, base_path, sub_name, run_name, pp_steps):
        super(Data, self).__init__()

        self.base_path = Path(base_path)
        self.rawdata_path = self.base_path / "rawdata"

        assert self.rawdata_path.is_dir(), f"No data found at {rawdata_path}. \n" \
                                           f"Raw data must be in a folder rawdata that resides within base_path"

        self.sub_name = sub_name
        self.run_name = run_name
        self.pp_steps = pp_steps
        self.data = {"0-raw": None}
        self.opts = {"0-raw": None}

        # TODO: this requires gate number to be known
        # which is passed at runtime. There is probably
        # better way to handle this.
        self.run_level_path = None

        # These are dynamically set by the sorter
        # chosen at runtime.
        self.preprocessed_output_path = None
        self.sorter_output_path = None
        self.waveform_output_path = None
        self.preprocessed_data_class_path = None
        self.preprocessed_binary_data_path = None
        self.waveforms_output_path = None
        self.quality_metrics_path = None

    # Load and Save ----------------------------------------------------------------------------------------------------

    def save_all_preprocessed_data(self):
        self.save_preprocessed_binary()
        self.save_data_class()

    def save_preprocessed_binary(self):
        """
        Will error if path already exists
        """
        recording, __ = utils.get_dict_value_from_step_num(self, "last")
        recording.save(folder=self.preprocessed_binary_data_path)

    def load_preprocessed_binary(self):
        return si.load_extractor(self.preprocessed_binary_data_path)

    def save_data_class(self):
        if not self.preprocessed_output_path.is_dir():
            os.makedirs(self.preprocessed_output_path)

        with open(self.preprocessed_data_class_path, "wb") as file:
            pickle.dump(self, file, pickle.HIGHEST_PROTOCOL)

    # Handle Paths -----------------------------------------------------------------------------------------------------

    def set_preprocessing_output_path(self):
        assert self.run_level_path is not None, "must set run_level_path before sorter_output_path"

        self.preprocessed_output_path = self.base_path / "derivatives" / self.run_level_path.relative_to(self.rawdata_path) / "preprocessed"
        self.preprocessed_data_class_path = self.preprocessed_output_path / "data_class.pkl"
        self.preprocessed_binary_data_path = self.preprocessed_output_path / "si_recording"

    def set_sorter_output_paths(self, sorter):
        assert self.run_level_path is not None, "must set run_level_path before sorter_output_path"

        self.sorter_base_output_path = self.base_path / "derivatives" / self.run_level_path.relative_to(self.rawdata_path) / f"{sorter}-sorting"
        self.sorter_run_output_path = self.sorter_base_output_path / "sorter_output"  # canonical name, is where SI automatically saves sorter output,
        self.waveforms_output_path = self.sorter_base_output_path / "waveforms"
        self.quality_metrics_path = self.sorter_base_output_path / "quality_metrics.csv"

    # UserDict Overrides -----------------------------------------------------------------------------------------------

    def keys(self) -> KeysView:
        return self.data.keys()

    def items(self) -> ItemsView:
        return self.data.items()

    def values(self) -> ValuesView:
        return self.data.values()