from collections import UserDict
from collections.abc import ItemsView, KeysView, ValuesView
from dataclasses import dataclass
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
)

from spikewrap.utils import utils

if TYPE_CHECKING:
    import fnmatch


@dataclass
class BaseUserDict(UserDict):
    """
    Base class for `PreprocessingData` and `SortingData`
    used for checking and formatting `base_path`, `sub_name`
    and `run_names`. The layout of the `rawdata` and
    `derivatives` folder is identical up to the run
    folder, allowing use of this class for
    preprocessing and sorting.

    This class inhereits from UserDict, which allows us to define
    a dictionary-like object with additional methods. This class can
    be accessed like a dict e.g. `self[key]`. Under the hood, the
    dictionary is stored in `self.data`. When inheriting UserDict
    it is required to implement the `keys()`, `values()` and `items()`
    convenience functions.
    """

    base_path: Path
    sub_name: str
    sessions_and_runs: Dict[str, List[str]]

    def __post_init__(self) -> None:
        self.data: Dict = {}  # necessary for UserDict.
        self.base_path = Path(self.base_path)
        self.check_run_names_are_formatted_as_list()

    def find_ses_or_sub_keyword(
        self, session_or_run_names: List[str], session_or_run: Literal["session", "run"]
    ) -> Tuple[bool, Optional[str]]:
        """"""
        has_keyword = False
        keyword = None

        if any([name.lower() in ["all", "only"] for name in session_or_run_names]):
            if len(session_or_run_names) != 1:
                raise ValueError(
                    f"If using keyword '{keyword}' it should be the only provided {session_or_run} name."
                )
            has_keyword = True
            keyword = session_or_run_names[0]

        return has_keyword, keyword

    def raise_if_only_and_has_more_than_one_folder(
        self,
        keyword: Optional[str],
        base_path: Path,
        session_or_run_paths: List[str],
        session_or_run: Literal["session", "run"],
    ):
        if keyword == "only" and len(session_or_run_paths) != 1:
            raise RuntimeError(
                f"The filepath {base_path} contains more "
                f"than one folder but the {session_or_run} keyword is "
                f"set to 'only'."
            )

    def _convert_session_and_run_keywords_to_foldernames(  # TODO: this is called from preprocessing and sorting.
        self, get_sub_path: Callable, get_ses_path: Callable
    ) -> None:
        """ """
        # TODO: is this code like datashuttle code?

        # First, check if the session names need replacing
        session_names = list(self.sessions_and_runs.keys())

        has_ses_keyword, ses_keyword = self.find_ses_or_sub_keyword(
            session_names, "session"
        )

        if has_ses_keyword and ses_keyword is not None:
            ses_name_filepaths = (sub_path := get_sub_path()).glob("ses-*")
            # TODO: is stem?
            all_session_names = [
                path_.stem for path_ in ses_name_filepaths if path_.is_dir()
            ]

            self.raise_if_only_and_has_more_than_one_folder(
                ses_keyword, sub_path, all_session_names, "session"
            )

            runs = self.sessions_and_runs[ses_keyword]

            print({name: runs for name in all_session_names})

            self.sessions_and_runs = {name: runs for name in all_session_names}

        # Next, check if the runs need replacing.
        for ses_name in self.sessions_and_runs.keys():
            this_session_run_names = self.sessions_and_runs[ses_name]

            has_run_keyword, run_keyword = self.find_ses_or_sub_keyword(
                this_session_run_names, "run"
            )

            if has_run_keyword:
                all_run_paths = (
                    ses_path := get_ses_path(ses_name)
                    / "ephys"  # TODO: this is going to be everywhere so will need own function
                ).glob("*")

                run_names = [path_.stem for path_ in all_run_paths if path_.is_dir()]

                self.raise_if_only_and_has_more_than_one_folder(
                    run_keyword, ses_path, run_names, "run"
                )

                self.sessions_and_runs[ses_name] = run_names

    def check_run_names_are_formatted_as_list(self) -> None:
        """
        `sessions_and_runs` is typed as `Dict[str, List[str]]` but the
        class will accept `Dict[str, Union[str, List[str]]]` and
        cast here. Attempted to type with the latter, or `
        MutableMapping[str, [str, Union[str, List[str]]]` but had many issues
        such as https://github.com/python/mypy/issues/8136. The main thing
        is we can work with `Dict[str, List[str]]` but if `Dict[str, str]` is
        passed n general use it will not fail.
        """
        for key, value in self.sessions_and_runs.items():
            if not isinstance(value, List):
                assert isinstance(
                    value, str
                ), "Run names must be string or list of strings"
                self.sessions_and_runs[key] = [value]

    def flat_sessions_and_runs(self) -> List[Tuple[str, str]]:
        """
        This returns the sessions and runs dictionary flattened so that
        sessions and runs can be iterated over conveniently. `ordered_run_names`
        is flattened to a long list of all runs, while `ordered_ses_name` carries
        the corresponding session for each run.
        """
        return [
            (ses, run) for ses, runs in self.sessions_and_runs.items() for run in runs
        ]

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

                if False:
                    if self.filetype == "spikeglx":
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

    def assert_if_multi_segment(self):
        for ses_name, run_name in self.flat_sessions_and_runs():
            if self[ses_name][run_name]["0-raw"].get_num_segments() != 1:
                raise ValueError(
                    "Multi-segment recordings are not currently "
                    "supported. Please get in contact!"
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
        return self.get_derivatives_sub_path() / ses_name / "ephys"

    def get_derivatives_run_path(self, ses_name: str, run_name: str) -> Path:
        return self.get_derivatives_ses_path(ses_name) / run_name

    # Preprocessing Paths --------------------------------------------------------------

    def get_preprocessing_path(self, ses_name: str, run_name: str) -> Path:
        """
        Set the folder tree where preprocessing output will be
        saved. This is canonical and should not change.
        """
        preprocessed_output_path = (
            self.get_derivatives_run_path(ses_name, run_name) / "preprocessing"
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

    @staticmethod
    def update_two_layer_dict(dict_, ses_name, run_name, value):
        """
        Convenience function to allow updating a two-layer
        dictionary even if it is empty.
        """
        if ses_name not in dict_:
            dict_[ses_name] = {}

        dict_[ses_name][run_name] = value

    def keys(self) -> KeysView:
        return self.data.keys()

    def items(self) -> ItemsView:
        return self.data.items()

    def values(self) -> ValuesView:
        return self.data.values()
