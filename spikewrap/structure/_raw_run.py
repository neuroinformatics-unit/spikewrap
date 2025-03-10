from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

    from probeinterface import Probe
    from spikeinterface.core import BaseRecording


import spikeinterface.full as si

from spikewrap.configs._backend import canon
from spikewrap.process import _loading
from spikewrap.process._preprocessing import _preprocess_recording  # TODO
from spikewrap.utils import _utils


class RawRun:
    """
    Base class for an electrophysiology 'run'.
    Manages loading the raw data and preprocessing it.

    Parameters
    ----------
    parent_input_path
        Path to the raw-data session folder (e.g. ses-001 or ses-001/ephys)
        in which this run is contained.
    run_name
        Folder name of this run.
    session_output_path
        Path to the output (processed) parent session-level data.
    file_format
        "spikeglx" or "openephys", acquisition software used.

    Notes
    -----
    The raw data is loaded directly into `self._raw` and this
    data is never mutated or split by shank. If splitting by
    shank when preprocessing, a copied splt-by-shank version
    is generated and used in the preprocessing.

    TODO
    ----
    The attributes should not be mutated. Use a frozen dataclass?
    """

    def __init__(
        self,
        parent_input_path: Path,
        parent_ses_name: str,
        run_name: str,
        file_format: Literal["spikeglx", "openephys"],
    ):

        self._parent_input_path = parent_input_path
        self._parent_ses_name = parent_ses_name
        self._run_name = run_name
        self._file_format = file_format

        # These properties are mutable and refreshed during
        # the lifetime of the class, by this class only.
        self._raw: dict = {}
        self._sync = None

    # ---------------------------------------------------------------------------
    # Public Functions
    # ---------------------------------------------------------------------------

    def load_raw_data(self, internal_overwrite: bool = False) -> None:
        """
        If applicable, this function should load
        SpikeInterface recording objects.
        """
        raise NotImplementedError("Implement in base class.")

    def refresh_data(self) -> None:
        """
        Completely refresh all raw and preprocessed data.
        This completely destroys all associated SpikeInterface
        recording objects.

        New raw SpikeInterface recordings are instantiated.
        This overwrites all shank splitting etc.
        """
        self._sync = None
        self.load_raw_data(internal_overwrite=True)

    def preprocess(self, pp_steps: dict, per_shank: bool) -> dict:
        """
        Preprocess the run. If ``per_shank``, the ``self._raw``
        recording is split into separate shank groups before preprocessing.

        Preprocessed recordings are saved in the same format as
        ``self._raw`` to the ``self._preprocessed`` attribute.

        Parameters
        ----------
        see session.preprocess()
        """
        assert (
            self.raw_is_loaded()
        ), "Data should already be loaded at this stage, it is managed by the Session()."

        if per_shank:
            runs_to_preprocess = self._get_split_by_shank()
        else:
            runs_to_preprocess = self._raw

        preprocessed = {}
        for shank_id, raw_rec in runs_to_preprocess.items():
            prepro_dict = {"0-raw": raw_rec}
            preprocessed[shank_id] = _preprocess_recording(prepro_dict, pp_steps)

        return preprocessed

    # Helpers -----------------------------------------------------------------

    def raw_is_loaded(self) -> bool:
        """
        Return `True` if data has been loaded as SpikeInterface recordings.
        """
        return self._raw != {}

    # ---------------------------------------------------------------------------
    # Private Functions
    # ---------------------------------------------------------------------------

    def _get_split_by_shank(self) -> dict:
        """
        Split ``self._raw`` recording my shank. By default, the ``self._raw``
        is a dictionary with one key:value pair, the recording with
        all shanks grouped.

        If split, this becomes a dict with key:value are the shank
        names and split recordings respectively.
        """
        if (recording := self._raw[canon.grouped_shankname()]).get_property(
            "group"
        ) is None:
            raise ValueError(
                f"Cannot split run {self._run_name} by shank as there is no 'group' property."
            )

        _raw = recording.split_by("group")
        _raw = {f"shank_{key}": value for key, value in _raw.items()}  # TODO: RENAME

        _utils.message_user(
            f"Split run: {self._run_name} by shank. There are {len(_raw)} shanks. "
        )

        return _raw


# -----------------------------------------------------------------------------
# Separate Runs Class
# -----------------------------------------------------------------------------


class SeparateRawRun(RawRun):
    """
    Represents a single electrophysiological run. Exposes Run functionality
    and ability to load the SpikeInterface recording for this run into the class.
    """

    def __init__(
        self,
        parent_input_path: Path,
        parent_ses_name: str,
        run_name: str,
        file_format: Literal["spikeglx", "openephys"],
        probe: Probe | None,
    ):
        self._parent_input_path: Path
        self._probe = probe

        super(SeparateRawRun, self).__init__(
            parent_input_path,
            parent_ses_name,
            run_name,
            file_format,
        )

    def load_raw_data(self, internal_overwrite: bool = False) -> None:
        """
        Fill the run with SpikeInterface recording objects.

        For multi-shank recordings, all shanks are currently grouped
        and may be split later.

        Parameter
        --------
        internal_overwrite
            Flag used to confirm overwriting the class data attributes is intended.

        """
        if self.raw_is_loaded() and not internal_overwrite:
            raise RuntimeError("Cannot overwrite Run().")

        without_sync, with_sync = _loading.load_data(
            self._parent_input_path / self._run_name, self._file_format, self._probe
        )

        self._raw = {canon.grouped_shankname(): without_sync}
        self._sync = with_sync


# -----------------------------------------------------------------------------
# Concatenate Runs Class
# -----------------------------------------------------------------------------


class ConcatRawRun(RawRun):
    """
    Subclass of `Run` used for concatenating `SeparateRawRun`s and
    processing the concatenated recording.

    Differences from `SeparateRawRun`:
    1) ``load_run_data`` will raise, as it is assumed raw data has
       already been loaded as separate runs and concatenated.
    2) ``_orig_run_names`` holds the names of original, separate
       recordings in the order they were concatenated.
    """

    def __init__(
        self,
        runs_list: list[SeparateRawRun],
        parent_input_path: Path,
        parent_ses_name: str,
        file_format: Literal["spikeglx", "openephys"],
    ):
        super(ConcatRawRun, self).__init__(
            parent_input_path=parent_input_path,
            parent_ses_name=parent_ses_name,
            run_name="concat_run",
            file_format=file_format,
        )

        # Get the recordings to concatenate
        (
            raw_data,
            sync_data,
            orig_run_names,
        ) = self._format_recordings_to_concat(runs_list)

        # Concatenate and store the recordings, assumes data is not
        # per-shank at this stage.
        key = canon.grouped_shankname()

        self._raw = {key: si.concatenate_recordings([data[key] for data in raw_data])}

        self._sync = (
            None if not all(sync_data) else si.concatenate_recordings(sync_data)
        )

        self._orig_run_names = orig_run_names

    def load_raw_data(self, internal_overwrite: bool = False) -> None:
        """
        Overload the base class ``load_raw_data``. This should not
        be called on this subclass, because raw-data is already loaded
        (and concatenated, to form this recording).

        Parameters
        ----------
        See base class.
        """
        raise NotImplementedError(
            "Cannot load data on a concatenated recording."
            "It is already run, and the input path does not exist."
        )

    def _format_recordings_to_concat(
        self, runs_list: list[SeparateRawRun]
    ) -> tuple[list[BaseRecording], list[BaseRecording], list[str]]:
        """
        Extracts raw data, sync data, and run names from a list of
        SeparateRawRun objects and returns the relevant data.

        No checks on whether it is suitable to concatenate the recordings
        is performed here, as this is done in the SpikeInterface function.

        Parameters
        ----------
        runs_list
            List of runs to be concatenated. Must not contain
            already-concatenated `ConcatRawRun` objects.
        """
        raw_data: list[BaseRecording] = []
        sync_data: list[BaseRecording] = []
        orig_run_names: list[str] = []

        # Extract the raw and sync recordings, and run names, while checking
        # data it is the correct format and valid for concatenation.
        for run in runs_list:
            assert run.raw_is_loaded(), (
                "Something has gone wrong, raw data should be loaded at "
                "concat run stage. Contact spikewrap team."
            )
            if isinstance(run, ConcatRawRun):
                raise ValueError(
                    "Cannot concatenate runs that have already been split by shank.\n"
                    "Something unexpected has happened. Please contact the spikewrap team."
                )

            raw_data.append(run._raw)
            sync_data.append(run._sync)
            orig_run_names.append(run._run_name)

        assert all(  # TODO: maybe delete
            list(dict_.keys()) == [canon.grouped_shankname()] for dict_ in raw_data
        ), "We should not be multi-shank at this stage."

        return raw_data, sync_data, orig_run_names
