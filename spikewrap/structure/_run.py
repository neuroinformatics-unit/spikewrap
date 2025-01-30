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
    # Responsibilities:
        - hold raw data of the run (either split per shank or grouped)
        - hold preprocessed data of the run (either split per shank or grouped)
        - save sync channel when is saved across all runs
        - handle overwriting (at the run level)

    Note the inheritence...
    """

    def __init__(
        self,
        parent_input_path: Path | None,
        run_name: str,
        session_output_path: Path,
        file_format: Literal["spikeglx", "openephys"],
    ):
        # These parameters should be treated as constant and never changed
        # during the lifetime of the class. Use the properties (which do not
        # expose a setter) for both internal and external calls.
        self._parent_input_path = parent_input_path
        self._run_name = run_name
        self._output_path = session_output_path / run_name
        self._file_format = file_format

        # These properties are mutable and refreshed during
        # the lifetime of the class, by this class only.
        self._raw: dict = {}
        self._preprocessed: dict = {}

        self._sync = None

    # TODO: I think just remove these...? this is not a public class, very confusing..
    @property
    def parent_input_path(self) -> Path | None:
        return self._parent_input_path

    @property
    def run_name(self) -> str:
        return self._run_name

    @property
    def output_path(self) -> Path:
        return self._output_path

    @property
    def file_format(self) -> Literal["spikeglx", "openephys"]:
        return self._file_format

    # ---------------------------------------------------------------------------
    # Public Functions
    # ---------------------------------------------------------------------------

    def load_raw_data(self, internal_overwrite: bool = False) -> None:
        """
        TODO: again, figure out lifetime!
        I think its okay....
        """
        raise NotImplementedError

    def refresh_data(self) -> None:
        """ """
        self._preprocessed = {}
        self._sync = None
        self.load_raw_data(internal_overwrite=True)

    def preprocess(self, pp_steps: dict, per_shank: bool) -> None:
        """
        Note because this class is fresh, we can assume only run once.
        IMMUTABLE CLASS! ONE-SHOT CLASS!
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
                raw_rec, pp_steps, self.output_path, rec_name
            )

    def save_preprocessed(
        self, overwrite: bool, chunk_size: dict | None, n_jobs: int, slurm: dict | bool
    ) -> None:
        """ """
        if slurm:
            self._save_preprocessed_slurm(overwrite, chunk_size, n_jobs, slurm)
            return

        _utils.message_user(f"Saving data for: {self.run_name}...")

        if n_jobs != 1:
            si.set_global_job_kwargs(n_jobs=n_jobs)

        if self.output_path.is_dir():  # getter func?
            if overwrite:
                self._delete_existing_run_except_slurm_logs(self.output_path)
            else:
                raise RuntimeError(
                    f"`overwrite` is `False` but data already exists at the run path: {self.output_path}."
                )

        self._save_sync_channel()

        for preprocessed in self._preprocessed.values():
            preprocessed.save_binary(chunk_size)

    @staticmethod
    def _delete_existing_run_except_slurm_logs(output_path):
        # TODO: move
        # Do not delete slurm logs for a run, keep these forever for provennance.
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
        if not self._preprocessing_is_run():
            raise RuntimeError("Preprocessing has not been run.")

        fig = visualise_run_preprocessed(
            self.run_name,
            show,
            self._preprocessed,
            mode=mode,
            time_range=time_range,
            show_channel_ids=show_channel_ids,
            figsize=figsize,
        )

        return fig

    # Helpers -----------------------------------------------------------------

    def raw_is_loaded(self) -> bool:
        return self._raw != {}

    # ---------------------------------------------------------------------------
    # Private Functions
    # ---------------------------------------------------------------------------

    def _split_by_shank(self) -> None:
        """ """
        assert not self._is_split_by_shank(), (
            f"Attempting to split by shank, but the recording"
            f"in run: {self.run_name} has already been split."
            f"This should not happen. Please contact the spikewrap team."
        )

        if (recording := self._raw[canon.grouped_shankname()]).get_property(
            "group"
        ) is None:
            raise ValueError(
                f"Cannot split run {self.run_name} by shank as there is no 'group' property."
            )

        self._raw = recording.split_by("group")
        self._raw = {str(key): value for key, value in self._raw.items()}

        _utils.message_user(
            f"Split run: {self.run_name} by shank. There are {len(self._raw)} shanks. "
        )

    def _save_preprocessed_slurm(
        self, overwrite: bool, chunk_size: dict | None, n_jobs: int, slurm: dict | bool
    ) -> None:
        """ """
        slurm_ops: dict | bool = slurm if isinstance(slurm, dict) else False

        _slurm.run_in_slurm(
            slurm_ops,
            func_to_run=self.save_preprocessed,
            func_opts={
                "overwrite": overwrite,
                "chunk_size": chunk_size,
                "n_jobs": n_jobs,
                "slurm": False,
            },
            log_base_path=self.output_path,
        )

    def _save_sync_channel(self) -> None:
        """
        Save the sync channel separately. In SI, sorting cannot proceed
        if the sync channel is loaded to ensure it does not interfere with
        sorting. As such, the sync channel is handled separately here.
        """
        sync_output_path = self.output_path / canon.sync_folder()

        _utils.message_user(f"Saving sync channel for: {self.run_name}...")

        if self._sync:
            _saving.save_sync_channel(self._sync, sync_output_path, self._file_format)

    # Helpers -----------------------------------------------------------------

    def _is_split_by_shank(self) -> bool:
        """ """
        return len(self._raw) > 1

    def _preprocessing_is_run(self) -> bool:
        """ """
        return any(self._preprocessed)


# -----------------------------------------------------------------------------
# Separate Runs Class
# -----------------------------------------------------------------------------


class SeparateRun(BaseRun):
    """ """

    def __init__(
        self,
        parent_input_path: Path,
        run_name: str,
        session_output_path: Path,
        file_format: Literal["spikeglx", "openephys"],
    ):
        self._parent_input_path: Path

        super(SeparateRun, self).__init__(
            parent_input_path, run_name, session_output_path, file_format
        )

    @property
    def parent_input_path(self) -> Path:
        return self._parent_input_path

    def load_raw_data(self, internal_overwrite: bool = False) -> None:
        """ """
        if self.raw_is_loaded() and not internal_overwrite:
            raise RuntimeError("Cannot overwrite Run().")

        without_sync, with_sync = _loading.load_data(
            self.parent_input_path / self.run_name, self._file_format
        )

        self._raw = {canon.grouped_shankname(): without_sync}
        self._sync = with_sync


# -----------------------------------------------------------------------------
# Concatenate Runs Class
# -----------------------------------------------------------------------------


class ConcatRun(BaseRun):
    """ """

    def __init__(
        self,
        runs_list: list[SeparateRun],
        parent_input_path: Path,
        session_output_path: Path,
        file_format: Literal["spikeglx", "openephys"],
    ):
        self._parent_input_path: None

        super(ConcatRun, self).__init__(
            parent_input_path=parent_input_path,
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

    @property
    def parent_input_path(self) -> None:
        return self._parent_input_path

    @property
    def orig_run_names(self) -> list[str]:
        """ """
        return self._orig_run_names

    def load_raw_data(self, internal_overwrite: bool = False) -> None:
        """ """
        raise NotImplementedError(
            "Cannot load data on a concatenated recording."
            "It is already run, and the input path does not exist."
        )

    def save_preprocessed(
        self, overwrite: bool, chunk_size: dict | None, n_jobs: int, slurm: dict | bool
    ) -> None:
        """
        This way of handling run concat provenance is basic and will be superseded.
        """
        super().save_preprocessed(overwrite, chunk_size, n_jobs, slurm)

        with open(self.output_path / "orig_run_names.txt", "w") as f:
            f.write("\n".join(self.orig_run_names))

    def _check_and_format_recordings_to_concat(
        self, runs_list: list[SeparateRun]
    ) -> tuple[list[BaseRecording], list[BaseRecording], list[str]]:
        """ """
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
            orig_run_names.append(run.run_name)

        assert all(
            list(dict_.keys()) == [canon.grouped_shankname()] for dict_ in raw_data
        ), "We should not be multi-shank at this stage."
        assert self._preprocessed == {}, "Something has gone wrong in the inheritance."

        # Check key features of the recordings match before concatenation

        all_contacts = [rec["grouped"].get_channel_locations() for rec in raw_data]
        all_sampling_frequency = [
            rec["grouped"].get_sampling_frequency() for rec in raw_data
        ]
        if not all(
            [np.array_equal(contact, all_contacts[0]) for contact in all_contacts]
        ):
            raise RuntimeError(
                f"Cannot concatenate recordings with different channel organisation."
                f"This occurred for runs in folder: {self.parent_input_path}"
            )

        if not np.unique(all_sampling_frequency).size == 1:
            raise RuntimeError(
                f"Cannot concatenate recordings with different sampling frequencies."
                f"This occurred for runs in folder: {self.parent_input_path}"
            )

        return raw_data, sync_data, orig_run_names
