import warnings
from pathlib import Path
from typing import Dict, Union

import spikeinterface as si
import yaml

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

    def __init__(self, preprocessed_data_path: Union[str, Path]):
        """ """
        super(SortingData, self).__init__()

        self.preprocessed_data_path = Path(preprocessed_data_path)
        self.check_preprocessed_data_path_exists()

        self.top_level_folder = "derivatives"
        self.init_data_key = "0-preprocessed"
        self.pp_info = self.load_preprocess_data_attributes()

        self.base_path = Path(self.pp_info["base_path"])
        self.show_warning_if_base_path_diverged()

        self.sub_name = self.pp_info["sub_name"]
        self.pp_run_name = self.pp_info["pp_run_name"]

        # These paths are set when the sorter
        # is known, set_sorter_output_paths()
        self.sorter_base_output_path = Path()
        self.sorter_run_output_path = Path()
        self.waveforms_output_path = Path()
        self.quality_metrics_path = Path()
        self.unit_locations_path = Path()

        # This is set later, depending on
        # concatenated or not.
        self.data: Dict = {"0-preprocessed": None}

    def show_warning_if_base_path_diverged(self):
        """
        It is expected that the passed preprocessed data output path
        is in the same location as the data was saved during preprocessed,
        as stored in the PreprocessData attribute. This can be broken
        however, in the case of accessing the same folder as a mounted drive.
        """
        pp_base_path = [
            path
            for path in self.preprocessed_data_path.parents
            if path.stem == "derivatives"
        ][0]
        if pp_base_path != self.base_path:
            warnings.warn(
                f"The base path of the `preprocessed_data_path` does not match the "
                f"`base_path` contained used to run the preprocessing. This is expected "
                f"if running the same folder from a different location (e.g. mounted drive). "
                f"Otherwise, check the base paths are correct.\n"
                f"passed base path: {self.preprocessed_data_path}\n"
                f"original base path: {self.base_path}"
            )

    def check_preprocessed_data_path_exists(self) -> None:
        """
        Ensure the preprocessed data path exists, otherwise
        it cannot be loaded and sorting will fail.
        """
        if not self.preprocessed_data_path.is_dir():
            raise FileNotFoundError(
                f"No preprocessed data found at " f"{self.preprocessed_data_path}"
            )

    def load_preprocess_data_attributes(self) -> Dict:
        """
        Load the PreprocessingData attributes that were
        saved when writing the preprocessed data to file.

        These fields are used to set the sorting and other
        output paths, and for provenance.
        """
        with open(
            Path(self.preprocessed_data_path)
            / utils.canonical_names("preprocessed_yaml")
        ) as file:
            pp_info = yaml.full_load(file)
        return pp_info

    def load_preprocessed_binary(self, concatenate: bool = True):
        """
        Use SpikeInterface to load the binary-data into a recording object.

        Parameters
        ----------
        concatenate : bool
            If `True`, all segments in the loaded SpikeInterface
            recording object will be concatenated into a single
            segment.
        """
        binary_path = self.preprocessed_data_path / "si_recording"  # TODO: configs

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
        self.sorter_base_output_path = utils.make_sorter_base_output_path(
            self.base_path, self.sub_name, self.pp_run_name, sorter
        )

        self.sorter_run_output_path = self.sorter_base_output_path / "sorter_output"
        self.waveforms_output_path = self.sorter_base_output_path / "waveforms"
        self.quality_metrics_path = self.sorter_base_output_path / "quality_metrics.csv"
        self.unit_locations_path = self.sorter_base_output_path / "unit_locations.csv"
