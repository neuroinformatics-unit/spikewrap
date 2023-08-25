import fnmatch
from collections import UserDict
from collections.abc import ItemsView, KeysView, ValuesView
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Callable, Dict, List, Literal

from ..utils import utils


@dataclass
class BaseUserDict(UserDict):
    """
    Base class for `PreprocessingData` and `SortingData`
    used for checking and formatting `base_path`, `sub_name`
    and `run_names`. The layout of the `rawdata` and
    `derivatives` folder is identical up to the run
    folder, allowing use of this class for
    preprocessing and sorting.

    Base UserDict that implements the
    keys(), values() and items() convenience functions."""

    base_path: Path
    sub_name: str
    sessions_and_runs: Dict

    def __post_init__(self) -> None:
        self.data: Dict = {}
        self.base_path = Path(self.base_path)
        self.check_run_names_are_formatted_as_list()

    def check_run_names_are_formatted_as_list(self) -> None:
        """"""
        for key, value in self.sessions_and_runs.items():
            if not isinstance(value, List):
                assert isinstance(
                    value, str
                ), "Run names must be string or list of strings"
                self.sessions_and_runs[key] = [value]

    def preprocessing_sessions_and_runs(self):  # TODO: type hint
        """"""
        ordered_ses_names = list(
            chain(*[[ses] * len(runs) for ses, runs in self.sessions_and_runs.items()])
        )
        ordered_run_names = list(
            chain(*[runs for runs in self.sessions_and_runs.values()])
        )

        return list(zip(ordered_ses_names, ordered_run_names))

    def _validate_inputs(
        self,
        top_level_folder: Literal["rawdata", "derivatives"],
        get_top_level_folder: Callable,
        get_sub_level_folder: Callable,
        get_sub_path: Callable,
        get_run_path: Callable,
    ) -> None:
        """
        Check the rawdata / derivatives path, subject path exists
        and ensure run_names is a list of strings.

        Parameters
        ----------
        run_names : List[str]
            List of run names to process, in order they should be
            processed / concatenated.

        Returns
        -------
        run_names : List[str]
            Validated `run_names` as a List.
        """
        assert get_top_level_folder().is_dir(), (
            f"Ensure there is a folder in base path called '"
            f"{top_level_folder}'.\n"
            f"No {top_level_folder} directory found at "
            f"{get_top_level_folder()}\n"
            f"where subject-level folders must be placed."
        )

        assert get_sub_level_folder().is_dir(), (
            f"Subject directory not found. {self.sub_name} "
            f"is not a folder in {get_top_level_folder()}"
        )

        for ses_name in self.sessions_and_runs.keys():
            assert (
                ses_path := get_sub_path(ses_name)
            ).is_dir(), f"{ses_name} was not found at folder path {ses_path}"

            for run_name in self.sessions_and_runs[ses_name]:
                assert (run_path := get_run_path(ses_name, run_name)).is_dir(), (
                    f"The run folder {run_path.stem} cannot be found at "
                    f"file path {run_path.parent}."
                )

                gate_str = fnmatch.filter(run_name.split("_"), "g?")

                assert len(gate_str) > 0, (
                    f"The SpikeGLX gate index should be in the run name. "
                    f"It was not found in the name {run_name}."
                    f"\nEnsure the gate number is in the SpikeGLX-output filename."
                )

                assert len(gate_str) == 1, (
                    f"The SpikeGLX gate appears in the name "
                    f"{run_name} more than once"
                )

                assert int(gate_str[0][1:]) == 0, (
                    f"Gate with index larger than 0 is not supported. This is found "
                    f"in run name {run_name}. "
                )

    # Rawdata Paths --------------------------------------------------------------

    def get_rawdata_top_level_path(self) -> Path:
        return self.base_path / "rawdata"

    def get_rawdata_sub_path(self) -> Path:
        return self.get_rawdata_top_level_path() / self.sub_name

    def get_rawdata_ses_path(self, ses_name: str) -> Path:
        return self.get_rawdata_sub_path() / ses_name

    def get_rawdata_run_path(self, ses_name: str, run_name: str) -> Path:
        return self.get_rawdata_ses_path(ses_name) / "ephys" / run_name

    # Derivatives Paths --------------------------------------------------------------

    def get_derivatives_top_level_path(self) -> Path:
        return self.base_path / "derivatives" / "spikewrap"

    def get_derivatives_sub_path(self) -> Path:
        return self.get_derivatives_top_level_path() / self.sub_name

    def get_derivatives_ses_path(self, ses_name: str) -> Path:
        return self.get_derivatives_sub_path() / ses_name

    def get_derivatives_run_path(self, ses_name: str, run_name: str) -> Path:
        return self.get_derivatives_ses_path(ses_name) / run_name

    # Preprocessing Paths --------------------------------------------------------------

    def get_preprocessing_path(self, ses_name: str, run_name: str) -> Path:
        """
        Set the folder tree where preprocessing output will be
        saved. This is canonical and should not change.
        """
        preprocessed_output_path = (
            self.get_derivatives_run_path(ses_name, run_name) / "preprocessed"
        )
        return preprocessed_output_path

    def _get_pp_binary_data_path(self, ses_name: str, run_name: str) -> Path:
        return self.get_preprocessing_path(ses_name, run_name) / "si_recording"

    def _get_sync_channel_data_path(self, ses_name: str, run_name: str) -> Path:
        return self.get_preprocessing_path(ses_name, run_name) / "sync_channel"

    def get_preprocessing_info_path(self, ses_name: str, run_name: str) -> Path:
        return self.get_preprocessing_path(ses_name, run_name) / utils.canonical_names(
            "preprocessed_yaml"
        )

    def keys(self) -> KeysView:
        return self.data.keys()

    def items(self) -> ItemsView:
        return self.data.items()

    def values(self) -> ValuesView:
        return self.data.values()
