from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

    import matplotlib
    from spikeinterface.core import BaseRecording

import shutil

import numpy as np
import spikeinterface.full as si

from spikewrap.configs._backend import canon
from spikewrap.process import _loading, _saving
from spikewrap.structure._preprocessed import Preprocessed
from spikewrap.utils import _slurm, _utils
from spikewrap.visualise._visualise import visualise_run_preprocessed


class BaseRun:
    """
    Base class for an electrophysiology 'run'. Manages loading data,
    preprocessing and saving of the run.

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
    This class instance should manage data for the same run
    throughout its lifetimes, the format, paths and run name
    should not change.

    The _raw, _preprocessed, _sync attributes may be loaded
    repeatedly from the passed paths in order to 'refresh'
    their state (for example, preprocessed with different options,
    or reset to grouped recordings instead of separate shank).
    """

    def __init__(
        self,
        parent_input_path: Path,
        parent_ses_name: str,
        run_name: str,
        session_output_path: Path,
        file_format: Literal["spikeglx", "openephys"],
    ):
        # These parameters should be treated as constant and never changed
        # during the lifetime of the class. Use the properties (which do not
        # expose a setter) for both internal and external calls.
        self._parent_input_path = parent_input_path
        self._parent_ses_name = parent_ses_name
        self._run_name = run_name
        self._output_path = session_output_path / run_name
        self._file_format = file_format

        # These properties are mutable and refreshed during
        # the lifetime of the class, by this class only.
        self._raw: dict = {}
        self._preprocessed: dict = {}
        self._sync = None

    # ---------------------------------------------------------------------------
    # Public Functions
    # ---------------------------------------------------------------------------

    def load_raw_data(self, internal_overwrite: bool = False) -> None:
        """
        IF applicable, this function should load
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
        self._preprocessed = {}
        self._sync = None
        self.load_raw_data(internal_overwrite=True)

    def preprocess(self, pp_steps: dict, per_shank: bool) -> None:
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
            not self._preprocessing_is_run()
        ), "Preprocessing was already run, can only be run once per class instance."

        assert (
            self.raw_is_loaded()
        ), "Data should already be loaded at this stage, it is managed by the Session()."

        if per_shank:
            self._split_by_shank()

        for key, raw_rec in self._raw.items():
            rec_name = f"shank_{key}" if key != canon.grouped_shankname() else key

            self._preprocessed[key] = Preprocessed(
                raw_rec, pp_steps, self._output_path, rec_name
            )

    def save_preprocessed(
        self, overwrite: bool, chunk_duration_s: float, n_jobs: int, slurm: dict | bool
    ) -> None:
        """
        Save the fully preprocessed run to binary.

        see the public session.save_preprocessed()
        """
        if slurm:
            self._save_preprocessed_slurm(overwrite, chunk_duration_s, n_jobs, slurm)
            return

        _utils.message_user(f"Saving data for: {self._run_name}...")

        if n_jobs != 1:
            si.set_global_job_kwargs(n_jobs=n_jobs)

        if self._output_path.is_dir():
            if overwrite:
                self._delete_existing_run_except_slurm_logs(self._output_path)
            else:
                raise RuntimeError(
                    f"`overwrite` is `False` but data already exists at the run path: {self._output_path}."
                )

        self._save_sync_channel()

        for preprocessed in self._preprocessed.values():
            preprocessed.save_binary(chunk_duration_s)

    @staticmethod
    def _delete_existing_run_except_slurm_logs(output_path):
        """
        When overwriting the data for this run, delete
        everything except the ``"slurm_logs"`` folder.
        """
        _utils.message_user(
            f"`overwrite=True`, so deleting all files and folders "
            f"(except for slurm_logs) at the path:\n"
            f"{output_path}"
        )

        for path_ in output_path.iterdir():
            if path_.name != "slurm_logs":
                if path_.is_file():
                    path_.unlink()
                elif path_.is_dir():
                    shutil.rmtree(path_)

    def plot_preprocessed(
        self,
        mode: Literal["map", "line"],
        time_range: tuple[float, float],
        show_channel_ids: bool,
        show: bool,
        figsize: tuple[int, int],
    ) -> matplotlib.Figure:
        """
        Plot the fully preprocessed data for this run.

        Parameters
        ----------
        mode
            The type of plot to generate. ``"map"`` for a heatmap and ``"line"`` for a line plot.
        time_range
            The time range (start, end) to plot the data within, in seconds.
        show_channel_ids
            If True, the plot will display channel IDs.
        show
              If True, the plot will be displayed immediately (``plt.show()`` call).
        figsize
            The dimensions (width, height) of the figure in inches.
        """
        if not self._preprocessing_is_run():
            raise RuntimeError("Preprocessing has not been run.")

        fig = visualise_run_preprocessed(
            self._run_name,
            show,
            self._preprocessed,
            ses_name=self._parent_ses_name,
            mode=mode,
            time_range=time_range,
            show_channel_ids=show_channel_ids,
            figsize=figsize,
        )

        return fig

    # Helpers -----------------------------------------------------------------

    def raw_is_loaded(self) -> bool:
        """
        Return `True` if data has been loaded as SpikeInterface recordings.
        """
        return self._raw != {}

    # ---------------------------------------------------------------------------
    # Private Functions
    # ---------------------------------------------------------------------------

    def _split_by_shank(self) -> None:
        """
        Split ``self._raw`` recording my shank. By default, the ``self._raw``
        is a dictionary with one key:value pair, the recording with
        all shanks grouped.

        If split, this becomes a dict with key:value are the shank
        names and split recordings respectively.
        """
        assert not self._is_split_by_shank(), (
            f"Attempting to split by shank, but the recording"
            f"in run: {self._run_name} has already been split."
            f"This should not happen. Please contact the spikewrap team."
        )

        if (recording := self._raw[canon.grouped_shankname()]).get_property(
            "group"
        ) is None:
            raise ValueError(
                f"Cannot split run {self._run_name} by shank as there is no 'group' property."
            )

        self._raw = recording.split_by("group")
        self._raw = {str(key): value for key, value in self._raw.items()}

        _utils.message_user(
            f"Split run: {self._run_name} by shank. There are {len(self._raw)} shanks. "
        )

    def _save_preprocessed_slurm(
        self, overwrite: bool, chunk_duration_s: float, n_jobs: int, slurm: dict | bool
    ) -> None:
        """
        Use ``submitit`` to run the ``save_preprocessed``
        function for this run in a SLURM job.

        Parameters
        ----------
        see ``save_preprocessed``

        Notes
        -----
        This function is a little confusing because it is recursive. ``submitit``
        works by pickling the class / method to run, requesting a job and running
        the pickled method from within the SLURM job.

        Therefore, we need to tell ``submitit`` to run ``save_preprocessed`` with
        the passed kwargs from within the SLURM job, but we do not want to run it
        from within a SLURM job again because we will spawn infinite SLURM jobs!
        So when we run the function from within the SLURM job, we must set ``slurm=False``.
        """
        slurm_ops: dict | bool = slurm if isinstance(slurm, dict) else False

        _slurm.run_in_slurm(
            slurm_ops,
            func_to_run=self.save_preprocessed,
            func_opts={
                "overwrite": overwrite,
                "chunk_duration_s": chunk_duration_s,
                "n_jobs": n_jobs,
                "slurm": False,
            },
            log_base_path=self._output_path,
        )

    def _save_sync_channel(self) -> None:
        """
        Save the sync channel as a ``.npy`` file.

        In SI, sorting cannot proceed if the sync channel is loaded to ensure
        it does not interfere with sorting. As such, a separate recording with the
        sync channel present is maintained and handled separately here.
        """
        sync_output_path = self._output_path / canon.sync_folder()

        _utils.message_user(f"Saving sync channel for: {self._run_name}...")

        if self._sync:
            _saving.save_sync_channel(self._sync, sync_output_path, self._file_format)

    # Helpers -----------------------------------------------------------------

    def _is_split_by_shank(self) -> bool:
        """
        Returns ``True`` if this run recording has been split into separate shanks.
        """
        return len(self._raw) > 1

    def _preprocessing_is_run(self) -> bool:
        """
        Returns ``True`` if this run has been preprocesed.
        """
        return any(self._preprocessed)


# -----------------------------------------------------------------------------
# Separate Runs Class
# -----------------------------------------------------------------------------


class SeparateRun(BaseRun):
    """
    Represents a single electrophysiological run. Exposes Run functionality
    and ability to load the SpikeInterface recording for this run into the class.

    If concatenated, a list of `SeparateRuns` are converted to a `ConcatRun`.
    """

    def __init__(
        self,
        parent_input_path: Path,
        parent_ses_name: str,
        run_name: str,
        session_output_path: Path,
        file_format: Literal["spikeglx", "openephys"],
    ):
        self._parent_input_path: Path

        super(SeparateRun, self).__init__(
            parent_input_path,
            parent_ses_name,
            run_name,
            session_output_path,
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
            self._parent_input_path / self._run_name, self._file_format
        )

        self._raw = {canon.grouped_shankname(): without_sync}
        self._sync = with_sync


# -----------------------------------------------------------------------------
# Concatenate Runs Class
# -----------------------------------------------------------------------------


class ConcatRun(BaseRun):
    """
    Subclass of `Run` used for concatenating `SeparateRun`s and
    processing the concatenated recording.

    Differences from `SeparateRun`:
    1) ``load_run_data`` will raise, as it is assumed raw data has
       already been loaded as separate runs and concatenated.
    2) ``_orig_run_names`` holds the names of original, separate
       recordings in the order they were concatenated.
    """

    def __init__(
        self,
        runs_list: list[SeparateRun],
        parent_input_path: Path,
        parent_ses_name: str,
        session_output_path: Path,
        file_format: Literal["spikeglx", "openephys"],
    ):
        super(ConcatRun, self).__init__(
            parent_input_path=parent_input_path,
            parent_ses_name=parent_ses_name,
            run_name="concat_run",
            session_output_path=session_output_path,
            file_format=file_format,
        )

        # Get the recordings to concatenate
        (
            raw_data,
            sync_data,
            orig_run_names,
        ) = self._check_and_format_recordings_to_concat(runs_list)

        # Concatenate and store the recordings, assumes data is not
        # per-shank at this stage.
        key = canon.grouped_shankname()

        self._raw = {key: si.concatenate_recordings([data[key] for data in raw_data])}

        self._sync = (
            None if not all(sync_data) else si.concatenate_recordings(sync_data)
        )

        self._preprocessed = {}

        self._orig_run_names = orig_run_names

    def save_preprocessed(
        self, overwrite: bool, chunk_duration_s: float, n_jobs: int, slurm: dict | bool
    ) -> None:
        """
        Overloads the base ``save_preprocessed`` function to also write
        the original run names to disk to the concatenated run output folder.

        Parameters
        ----------
        See base class.
        """
        super().save_preprocessed(overwrite, chunk_duration_s, n_jobs, slurm)

        with open(self._output_path / "orig_run_names.txt", "w") as f:
            f.write("\n".join(self._orig_run_names))

    def load_raw_data(self, internal_overwrite: bool = False) -> None:
        """
        Overload the base class ``load_raw_data``. This should not
        be called on this subclass, because raw-data is already loaded
        (and concatenated, to form this recording).

        `ConcatRun` should only be preprocessed and saved.

        Parameters
        ----------
        See base class.
        """
        raise NotImplementedError(
            "Cannot load data on a concatenated recording."
            "It is already run, and the input path does not exist."
        )

    def _check_and_format_recordings_to_concat(
        self, runs_list: list[SeparateRun]
    ) -> tuple[list[BaseRecording], list[BaseRecording], list[str]]:
        """
        Extracts raw data, sync data, and run names from a list of SeparateRun
        objects, checks if they can be concatenated, and returns the relevant data.

        Parameters
        ----------
        runs_list
            List of runs to be concatenated. Must not contain
            already-concatenated `ConcatRun` objects.
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
            if run._is_split_by_shank():
                raise ValueError(
                    "Cannot concatenate runs that have already been split by shank.\n"
                    "Something unexpected has happened. Please contact the spikewrap team."
                )

            assert (
                run._preprocessed == {}
            ), f"{run._preprocessed}: Preprocessing already run, this is not expected. Contact spikewrap team."

            raw_data.append(run._raw)
            sync_data.append(run._sync)
            orig_run_names.append(run._run_name)

        assert all(
            list(dict_.keys()) == [canon.grouped_shankname()] for dict_ in raw_data
        ), "We should not be multi-shank at this stage."
        assert self._preprocessed == {}, "Something has gone wrong in the inheritance."

        # Check channel locations match, if probe is set. Otherwise, we must
        # assume channel ordering is the same across recordings...?
        has_contacts = True
        try:
            all_contacts = [rec["grouped"].get_channel_locations() for rec in raw_data]
        except:
            has_contacts = False

        if has_contacts:
            if not all(
                [np.array_equal(contact, all_contacts[0]) for contact in all_contacts]
            ):
                raise RuntimeError(
                    f"Cannot concatenate recordings with different channel organisation."
                    f"This occurred for runs in folder: {self._parent_input_path}"
                )

        # Check sampling frequencies match.
        all_sampling_frequency = [
            rec["grouped"].get_sampling_frequency() for rec in raw_data
        ]
        if not np.unique(all_sampling_frequency).size == 1:
            raise RuntimeError(
                f"Cannot concatenate recordings with different sampling frequencies."
                f"This occurred for runs in folder: {self._parent_input_path}"
            )

        return raw_data, sync_data, orig_run_names
