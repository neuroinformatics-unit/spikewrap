from pathlib import Path
from typing import Dict, Union

import spikeinterface as si
import yaml
from spikeinterface.core.base import BaseExtractor

from ..utils import utils
from .base import BaseUserDict


class SortingData(BaseUserDict):
    """
    """
    def __init__(self, preprocessed_output_path: Union[str, Path]):
        """
        """
        super(SortingData, self).__init__()

        self.preprocessed_output_path = Path(preprocessed_output_path)
        self.check_preprocessed_output_path_exists()

        self.top_level_folder = "derivatives"
        self.init_data_key = "0-preprocessed"  # TODO: this is not nice
        self.pp_info = self.load_preprocess_data_attributes()

        # Note the base-path can diverge if accessed from different
        # location than where the pp was saved. TODO explain properly.
        self.base_path = Path(self.pp_info["base_path"])
        self.sub_name = self.pp_info["sub_name"]
        self.pp_run_name = self.pp_info["pp_run_name"]

        # These paths are set when the sorter
        # is known, set_sorter_output_paths()
        self.sorter_base_output_path = Path()
        self.sorter_run_output_path = Path()
        self.waveforms_output_path = Path()
        self.quality_metrics_path = Path()

        # This is set later, depending on
        # concatenated or not.
        self.data: Dict = {"0-preprocessed": None}

    def check_preprocessed_output_path_exists(self) -> None:
        if not self.preprocessed_output_path.is_dir():
            raise FileNotFoundError(f"No preprocessed data found at "
                                    f"{self.preprocessed_output_path}")

    def load_preprocess_data_attributes(self) -> Dict:
        with open(
                Path(self.preprocessed_output_path) / utils.canonical_names(
                    "preprocessed_yaml")
        ) as file:
            pp_info = yaml.full_load(file)
        return pp_info

    def load_preprocessed_binary(self, concatenate: bool = True) -> BaseExtractor:
        """
        Use SpikeInterface to load the binary-data into a
        recording object.
        """
        binary_path = self.preprocessed_output_path / "si_recording"  # TODO: configs
      
        if not binary_path.is_dir():
            raise FileNotFoundError(
                f"No preprocessed SI binary-containing folder "
                f"found at {binary_path}."
            )
        recording = si.load_extractor(binary_path)

        if concatenate:
            recording = utils.concatenate_runs(recording)

        self.data["0-preprocessed"] = recording

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
