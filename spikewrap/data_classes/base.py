import fnmatch
from collections import UserDict
from collections.abc import ItemsView, KeysView, ValuesView
from pathlib import Path
from typing import List, Literal, Optional, Union

from ..utils import utils


class BaseUserDict(UserDict):
    """
    Base class for `PreprocessingData` and `SortingData`
    used for checking and formatting `base_path`, `sub_name`
    and `run_names`. The layout of the `rawdata` and
    `derivatives` folder is identical up to the run
    folder, allowing use of this class for
    preprocessing and sorting.

    Base UserDict that implements the
    keys(), values() and items() convenience functions.
    """

    def __init__(
        self,
        base_path: Union[str, Path],
        sub_name: str,
        run_names: Union[List[str], str],
    ) -> None:
        super(BaseUserDict, self).__init__()

        self.base_path = Path(base_path)
        self.sub_name = sub_name

        self.run_names = self.validate_inputs(
            run_names,
        )

    def _top_level_folder(self) -> Literal["rawdata", "derivatives"]:
        """
        The name of the top level folder, either 'rawdata' for
        preprocessing (i.e. loaded from rawdata) or `derivatives`
        for sorting (i.e. loaded from derivatives).
        """
        raise NotImplementedError

    def validate_inputs(self, run_names: Union[str, List[str]]) -> List[str]:
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
        top_level_folder_path = self.base_path / self._top_level_folder()

        assert (top_level_folder_path / self.sub_name).is_dir(), (
            f"Subject directory not found. {self.sub_name} "
            f"is not a folder in {top_level_folder_path}"
        )

        assert top_level_folder_path.is_dir(), (
            f"Ensure there is a folder in base path called '{self._top_level_folder()}'.\n"
            f"No {self._top_level_folder()} directory found at {top_level_folder_path}\n"
            f"where subject-level folders must be placed."
        )

        if not isinstance(run_names, list):
            run_names = [run_names]

        for run_name in run_names:
            gate_str = fnmatch.filter(run_name.split("_"), "g?")

            assert len(gate_str) > 0, (
                f"The SpikeGLX gate index should be in the run name. "
                f"It was not found in the name {run_name}."
                f"\nEnsure the gate number is in the SpikeGLX-output filename."
            )

            assert len(gate_str) == 1, (
                f"The SpikeGLX gate appears in the name " f"{run_name} more than once"
            )

            assert int(gate_str[0][1:]) == 0, (
                f"Gate with index larger than 0 is not supported. This is found "
                f"in run name {run_name}. "
            )

            run_path = self.get_run_path(run_name)
            assert run_path.is_dir(), (
                f"The run folder {run_path.stem} cannot be found at "
                f"file path {run_path.parent}."
            )

        return run_names

    def get_run_path(self, run_name: Optional[str] = None) -> Path:
        return self.get_sub_folder_path() / f"{run_name}"

    def get_sub_folder_path(self) -> Path:
        """
        Get the path to the rawdata subject folder.

        Returns
        -------
        sub_folder_path : Path
            Path to the self.sub_name folder in the `rawdata` path folder.
        """
        sub_folder_path = Path(
            self.base_path / self._top_level_folder() / self.sub_name
        )
        return sub_folder_path

    # Preprocessing Paths --------------------------------------------------------------

    def get_preprocessing_path(self, run_name: Optional[str] = None) -> Path:
        """
        Set the folder tree where preprocessing output will be
        saved. This is canonical and should not change.
        """
        preprocessed_output_path = (
            self.base_path
            / "derivatives"
            / self.sub_name
            / f"{run_name}"
            / "preprocessed"
        )
        return preprocessed_output_path

    def _get_pp_binary_data_path(self, run_name: Optional[str] = None) -> Path:
        return self.get_preprocessing_path(run_name) / "si_recording"

    def _get_sync_channel_data_path(self, run_name: Optional[str] = None) -> Path:
        return self.get_preprocessing_path(run_name) / "sync_channel"

    def _get_preprocessing_info_path(self, run_name: Optional[str] = None) -> Path:
        return self.get_preprocessing_path(run_name) / utils.canonical_names(
            "preprocessed_yaml"
        )

    def keys(self) -> KeysView:
        return self.data.keys()

    def items(self) -> ItemsView:
        return self.data.items()

    def values(self) -> ValuesView:
        return self.data.values()
