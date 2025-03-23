from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

    import matplotlib
    import numpy as np
    import submitit
    from probeinterface import Probe
    from spikeinterface.core import BaseRecording

import matplotlib.pyplot as plt
import numpy as np
import spikeinterface.full as si

from spikewrap.configs._backend import canon
from spikewrap.process import _loading
from spikewrap.process._preprocessing import _preprocess_recording  # TODO
from spikewrap.utils import _slurm, _utils


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
    sync_output_path
        For `SeparateRawRun`, where the sync channel is saved.
        Should be same path as preprocessed data output.

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
        sync_output_path: Path | None,
    ):

        self._parent_input_path = parent_input_path
        self._parent_ses_name = parent_ses_name
        self._run_name = run_name
        self._file_format = file_format
        self._sync_output_path = sync_output_path  # TODO: this name is confusing because it seems like the folder to the sync path but it is just to the run output path... should probably rename a lot

        # _raw should not change throughout the lifetime of the class
        # self._sync may be edited in place.
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
        # Sync Channel
        # ---------------------------------------------------------------------------

    def plot_sync_channel(self, show: bool) -> list[matplotlib.lines.Line2D]:
        """
        TODO
        ----
        -  move this into _visualise
        - make it cleaner / look nicer.
        """
        traces = self.get_sync_channel()

        plot = plt.plot(traces)

        if show:
            plt.show()

        return plot

    def get_sync_channel(self) -> np.ndarray:
        """
        Return the sync channel data (from the self._sync
        recording that holds the sync-attached recording).
        """
        if not self.raw_is_loaded():
            raise RuntimeError("Raw data is not yet loaded. Use `load_raw_data()`.")

        if not self._sync:
            raise ValueError("No sync channel found on this run.")

        select_sync_recording = self._sync.select_channels(
            [self._sync.get_channel_ids()[-1]]
        )

        rec_to_check = self._raw[list(self._raw.keys())[0]]

        traces = select_sync_recording.get_traces()

        assert (
            traces.size == rec_to_check.get_num_samples()
        ), "Somehow the sync channel does not have the same number of samples as the recording!"

        return select_sync_recording.get_traces()

    def silence_sync_channel(self, periods_to_silence: list[tuple]) -> None:
        """
        Silence the sync-channel recording. Note this will zero all
        channels in the recording, but we only care about the sync channel!
        """
        # TODO: copy.
        if not self.raw_is_loaded():
            raise RuntimeError("Raw data is not yet loaded. Use `load_raw_data()`.")

        if not self._sync:
            raise ValueError("No sync channel found on this run.")

        self._sync = si.silence_periods(
            recording=self._sync, list_periods=[periods_to_silence], mode="zeros"
        )

    def save_sync_channel(
        self, overwrite: bool = False, slurm: bool | dict = False
    ) -> None | submitit.Job:
        """
        Save the sync channel as a ``.npy`` file.

        In SI, sorting cannot proceed if the sync channel is loaded to ensure
        it does not interfere with sorting. As such, a separate recording with the
        sync channel present is maintained and handled separately here.
        """
        if self._sync is not None:

            if slurm:
                job = self._save_sync_channel_slurm(overwrite, slurm)
                return job

            sync_output_folder = self._sync_output_path / canon.sync_folder()

            if sync_output_folder.is_dir():
                if overwrite:
                    shutil.rmtree(sync_output_folder)
                else:
                    raise RuntimeError(
                        f"`overwrite=False` but sync data already exists at: {sync_output_folder}"
                    )

            sync_data = self.get_sync_channel()

            _utils.message_user(f"Saving sync channel for: {self._run_name}...")

            assert sync_data.size == self._raw["grouped"].get_num_samples()

            # Save the sync channel
            assert self._sync_output_path is not None

            sync_output_folder.mkdir(parents=True, exist_ok=True)
            np.save(sync_output_folder / canon.saved_sync_filename(), sync_data)

        return None

    def _save_sync_channel_slurm(self, overwrite: bool, slurm: dict | bool) -> None:
        """ """
        slurm_ops: dict | bool = slurm if isinstance(slurm, dict) else False

        assert (
            self._sync_output_path is not None
        ), "SeparateRawRun only contains self._sync_output_path"

        job = _slurm._run_in_slurm_core(
            slurm_ops,
            func_to_run=self._save_sync_channel_slurm,
            func_opts={
                "overwrite": overwrite,
                "slurm": False,
            },
            log_base_path=self._sync_output_path.parent,
            suffix_name="_sync",
        )

        return job

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
        sync_output_path: Path,
    ):
        self._parent_input_path: Path
        self._probe = probe
        self._orig_run_names = None

        super(SeparateRawRun, self).__init__(
            parent_input_path, parent_ses_name, run_name, file_format, sync_output_path
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
    3) `sync_output_path` is `None` because sync channel is handled
       at the separate-run level.
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
            sync_output_path=None,
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
