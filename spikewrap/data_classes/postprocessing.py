from __future__ import annotations

from pathlib import Path
from typing import Union

import spikeinterface as si
from spikeinterface import curation
from spikeinterface.extractors import NpzSortingExtractor

from spikewrap.pipeline.sort import get_sorting_data_class
from spikewrap.utils import utils


# TODO: figure out where to put this function.
def load_saved_sorting_output(
    sorter_output_path: Path, sorter: str
) -> si.SortingExtractor:
    """ """
    if "kilosort" in sorter:
        sorting = si.extractors.read_kilosort(
            folder_path=sorter_output_path.as_posix(),
            keep_good_only=False,
        )
    elif sorter == "mountainsort5":
        sorting = NpzSortingExtractor((sorter_output_path / "firings.npz").as_posix())

    elif sorter == "tridesclous":
        sorting = si.extractors.read_tridesclous(
            folder_path=sorter_output_path.as_posix()
        )

    elif sorter == "spykingcircus":
        sorting = si.extractors.read_spykingcircus(
            folder_path=sorter_output_path.as_posix()
        )

    return sorting


class PostprocessingData:
    """ """

    def __init__(self, sorting_path: Union[str, Path]) -> None:
        self.sorting_path = Path(sorting_path)

        self.sorter_output_path = self.sorting_path / "sorter_output"
        self.sorting_info_path = self.sorting_path / utils.canonical_names(
            "sorting_yaml"
        )

        self.check_sorting_paths_exist()

        self.sorting_info = utils.load_dict_from_yaml(self.sorting_info_path)

        SortingDataClass = get_sorting_data_class(
            self.sorting_info["concatenate_sessions"],
            self.sorting_info["concatenate_runs"],
        )

        self.sorting_data = SortingDataClass(
            self.sorting_info["base_path"],
            self.sorting_info["sub_name"],
            self.sorting_info["sessions_and_runs"],
            self.sorting_info["sorter"],
            print_messages=False,
        )
        self.sorted_ses_name = self.sorting_info["sorted_ses_name"]
        self.sorted_run_name = self.sorting_info["sorted_run_name"]
        self.preprocessing_info = self.sorting_info["preprocessing"]

        self.check_that_preprocessing_data_has_not_changed_since_sorting()
        self.preprocessed_recording = self.sorting_data.get_preprocessed_recordings(
            self.sorted_ses_name, self.sorted_run_name
        )
        self.sorting_output = self.get_sorting_extractor_object()

    def check_that_preprocessing_data_has_not_changed_since_sorting(self) -> None:
        """ """
        for ses_name in self.preprocessing_info.keys():
            for run_name in self.preprocessing_info[ses_name].keys():
                preprocessing_info_path = self.sorting_data.get_preprocessing_info_path(
                    ses_name, run_name
                )

                info_currently_in_preprocessing_folder = utils.load_dict_from_yaml(
                    preprocessing_info_path
                )

                assert (
                    self.preprocessing_info[ses_name][run_name]
                    == info_currently_in_preprocessing_folder
                ), (
                    f"The preprocessing file at {preprocessing_info_path} has changed"
                    f"since sorting was run. This suggests preprocessing was re-run with"
                    f"different settings for session{ses_name} run {run_name}. "
                    f"For postprocessing, waveforms are extracted from"
                    f"the preprocessed data based on the sorting results. If the preprocessed"
                    f"data has changed, the waveforms will not be valid."
                )

    def check_sorting_paths_exist(self) -> None:
        """ """
        if not self.sorting_path.is_dir():
            raise FileNotFoundError(
                f"No folder found at {self.sorting_path}. "
                f"Postprocessing was not performed."
            )

        if not self.sorting_path.name == "sorting":
            extra_message = (
                f"The 'sorting' folder was found in this folder path. "
                f"The path to the 'sorting' folder should be passed, "
                f"i.e: {self.sorting_path / 'sorting'}"
                if any(self.sorting_path.glob("sorting"))
                else ""
            )

            raise FileNotFoundError(
                f"The path is not to the 'sorting' folder. "
                f"Output was not found at "
                f"{self.sorting_path}.\n"
                f"{extra_message}"
            )

        if not self.sorter_output_path.is_dir():
            raise FileNotFoundError(
                f"There is no 'sorter_output' folder in the 'sorting' output "
                f"folder at {self.sorter_output_path}. Check that sorting "
                f"completely successfully."
            )

        if not self.sorting_info_path.is_file():
            raise FileNotFoundError(
                f"{utils.canonical_names('sorting_yaml')} was not found at "
                f"{self.sorting_info_path}. Please check sorting finished successfully."
            )

    def get_sorting_extractor_object(self) -> si.SortingExtractor:
        """"""
        sorter_output_path = self.sorting_path / "sorter_output"

        sorter = self.sorting_data.sorter

        sorting = load_saved_sorting_output(sorter_output_path, sorter)

        sorting = sorting.remove_empty_units()

        sorting_without_excess_spikes = curation.remove_excess_spikes(
            sorting, self.preprocessed_recording
        )

        return sorting_without_excess_spikes

    def get_postprocessing_path(self) -> Path:
        return utils.make_postprocessing_path(self.sorting_path)

    def get_quality_metrics_path(self) -> Path:
        return self.get_postprocessing_path() / "quality_metrics.csv"

    def get_unit_locations_path(self) -> Path:
        return self.get_postprocessing_path() / "unit_locations.csv"
