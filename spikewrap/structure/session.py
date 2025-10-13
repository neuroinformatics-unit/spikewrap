from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import yaml

if TYPE_CHECKING:
    import matplotlib
    import submitit
    from probeinterface import Probe

import time
from pathlib import Path

import numpy as np
import spikeinterface.full as si

from spikewrap.configs import config_utils
from spikewrap.configs._backend import canon
from spikewrap.process import _loading
from spikewrap.structure._preprocess_run import PreprocessedRun
from spikewrap.structure._raw_run import (
    ConcatRawRun,
    SeparateRawRun,
)
from spikewrap.structure._sorting_run import (
    ConcatSortingRun,
    SeparateSortingRun,
)
from spikewrap.utils import _utils


class Session:
    """
    Represents an electrophysiological recording session, consisting of a single or multiple runs.
    Exposes functions for preproecssing and sorting data from the session.

    Parameters
    ----------
    subject_path
        The path to the subject's directory. This should contain the ``session_name`` directory.
    session_name
        The name of this session. Must match the session folder name in the `subject_path`.
    file_format
        Acquisition software used for recording, either ``"spikeglx"`` or ``"openephys"``.
        Determines how a session's runs are discovered.
    run_names
        Specifies which runs within the session to include. If ``"all"`` (default), includes all
        runs detected within the session. Otherwise, a ``list of str``, a list of specific run names.
        Each name must correspond to a run folder within the session. Order passed will be the concentration order.
    output_path
        The path where preprocessed data will be saved (in NeuroBlueprint style).
    probe
        A ProbeInterface probe object to set on the recordings. If `None`,
        auto-detection of probe is attempted.

    Notes
    -----
    The responsibility of this class is to manage the processing of runs
    contained within the session. Raw data are held in ``self._raw_runs``, a list of
    ``SeparateRawRun``. The sync channel (if available) is held on the raw run in a
    recording object (other channels unused) and possibly mutated.
    ``load_raw_runs()`` will refresh the run sync channels.

    self._pp_runs is filled by self.preprocess(). Copies of _raw_runs are concatenated
    and / or split-by-shank before preprocessing, which fills self._pp_runs.
    The sync channel is attached in-memory (no longer on a recording).

    self._sorting_runs contains the sorting based on self._pp_runs. Again, copies
    of preprocessing runs are concatenated and / or split by shank before sorting.

    Properties of this class should never be modified from outside the class.
    """

    def __init__(
        self,
        subject_path: Path | str,
        session_name: str,
        file_format: Literal["spikeglx", "openephys"],
        run_names: Literal["all"] | list[str] = "all",
        output_path: Path | None = None,
        probe: Probe | None = None,
    ):

        parent_input_path = Path(subject_path)
        self._check_input_path(parent_input_path)
        self._check_file_format(file_format)

        if isinstance(run_names, str) and not run_names == "all":
            run_names = [run_names]

        self._passed_run_names = run_names
        self._file_format = file_format
        self._probe = probe

        self._parent_input_path = parent_input_path
        self._ses_name = session_name
        self._output_path = (
            Path(output_path) if output_path else self._output_from_parent_input_path()
        )

        self._running_slurm_jobs: list[submitit.Job] = []

        self._raw_runs: list[SeparateRawRun] = []
        self._pp_runs: list[PreprocessedRun] = []
        self._sorting_runs: list[SeparateSortingRun | ConcatSortingRun] = []

    # ---------------------------------------------------------------------------
    # Public Functions
    # ---------------------------------------------------------------------------

    def preprocess(
        self,
        configs: dict | str | Path,
        concat_runs: bool = False,
        per_shank: bool = False,
    ) -> None:
        """
        Preprocess recordings for all runs for this session.

        This step is lazy, under the hood running the preprocessing steps from ``configs``
        on SpikeInterface recording objects. Preprocessing of data is performed on the
        fly when required (e.g. plotting, saving or sorting).

        Parameters
        ----------
        configs
            - If a ``str`` is provided, expects the name of a stored configuration file.
              See ``show_available_configs()`` and ``save_config_dict()`` for details.
            - If a ``Path`` is provided, expects the path to a valid spikewrap config YAML file.
            - A spikewrap configs dictionary, either including the ``"preprocessing"`` level
              or the ``"preprocessing"`` level itself. See documentation for details.
        concat_runs
            If ``True``, all runs will be concatenated together before preprocessing.
            Use ``session.get_raw_run_names()`` to check the order of concatenation.
        per_shank
            If ``True``, perform preprocessing on each shank separately.
        overwrite_in_memory
            If ``False`` (default), the
        """
        pp_steps = self._infer_steps_from_configs_argument(configs, "preprocessing")

        _utils.show_preprocessing_configs(pp_steps)

        if not any(self._raw_runs):
            self._load_raw_data(internal_overwrite=False)

        runs_to_preprocess: list[SeparateRawRun | ConcatRawRun]
        if concat_runs:
            runs_to_preprocess = [self._get_concat_raw_run()]
        else:
            runs_to_preprocess = self._raw_runs  # type: ignore

        self._pp_runs = []
        for run in runs_to_preprocess:

            preprocessed_run = run.preprocess(pp_steps, per_shank)

            orig_run_names = run._orig_run_names

            self._pp_runs.append(
                PreprocessedRun(
                    raw_data_path=run._parent_input_path,
                    ses_name=self._ses_name,
                    run_name=run._run_name,
                    file_format=run._file_format,
                    session_output_path=self._output_path,
                    preprocessed_data=preprocessed_run,
                    pp_steps=pp_steps,
                    orig_run_names=orig_run_names,
                )
            )

    def save_preprocessed(
        self,
        overwrite: bool = False,
        chunk_duration_s: float = 2,
        n_jobs: int = 1,
        slurm: dict | bool = False,
    ) -> None:
        """
        Save preprocessed data for all runs in the current session.

        This method iterates over each run in the session and invokes the `save_preprocessed` method
        to persist the preprocessed data. It supports options to overwrite existing data, specify
        chunk sizes for data saving, utilize parallel processing, and integrate with SLURM for
        job scheduling.

        Parameters
        ----------
        overwrite
            If `True`, existing preprocessed run data will be overwritten.
            Otherwise, an error will be raised.
        chunk_duration_s
            Size of chunks which are separately to preprocessed and written.
        n_jobs
            Number of parallel jobs to run for saving preprocessed data.
            Sets SpikeInterface's `set_global_job_kwargs`.
        slurm
            Configuration for submitting the save jobs to a SLURM workload manager.
            If `False` (default), jobs will be run locally. If `True`, job will be run in SLURM
            with default arguments. If a `dict` is provided, it should contain SLURM arguments.
            See `tutorials` in the documentation for details.
        """
        for run in self._pp_runs:
            job_if_slurm = run.save_preprocessed(
                overwrite, chunk_duration_s, n_jobs, slurm
            )
            if slurm:
                self._running_slurm_jobs.append(job_if_slurm)

    def plot_preprocessed(
        self,
        run_idx: Literal["all"] | int = "all",
        mode: Literal["map", "line"] = "map",
        time_range: tuple[float, float] = (0.0, 1.0),
        show_channel_ids: bool = True,
        show: bool = False,
        figsize: tuple[int, int] = (10, 6),
    ) -> dict[str, matplotlib.Figure]:
        """
        Plot preprocessed run data.

        One plot will be generated for each run. For preprocessing
        per-shank, each shank will appear in a subplot. Under the hood,
        calls SpikeInterface's ``plot_traces()`` function.

        Parameters
        ----------
        run_idx
            - If ``"all"``, plots preprocessed data for all runs in the session.
            - If an integer, plots preprocessed data for the run at the specified index in ``self._pp_runs``.
        mode
            Determines the plotting style, a heatmap-style or line plot.
        time_range
            Time range (start, end), in seconds, to plot. e.g. (0.0, 1.0)
            This is relative to the first sample, and not the absolute time.
            i.e. `0` is always the first timepoint.
        show_channel_ids
            If ``True``, displays the channel identifiers on the plots.
        show
            If ``True``, displays the plots immediately. If ``False``, the
            plots are generated and returned without being displayed.
        figsize
            Specifies the size of the figure in inches as ``(width, height)``.

        Returns
        -------
        dict of {str: matplotlib.Figure}
            A dictionary mapping each run's name to its corresponding ``matplotlib.Figure`` object.
        """
        time_range = np.array(time_range, dtype=np.float64)

        all_runs = self._pp_runs if run_idx == "all" else [self._pp_runs[run_idx]]

        all_figs = {}

        for run in all_runs:
            fig = run.plot_preprocessed(
                mode=mode,
                time_range=time_range,
                show_channel_ids=show_channel_ids,
                show=show,
                figsize=figsize,
            )

            all_figs[run._run_name] = fig

        return all_figs

    def sort(
        self,
        configs: str | dict,
        run_sorter_method: str = "local",
        per_shank: bool = False,
        concat_runs: bool = False,
        overwrite: bool = True,
        slurm: bool = False,
    ):
        """
        Sort the preprocessed recordings (self.get_preprocessed_run_names())
        and save the output to disk.

        Parameters
        ----------

        configs
            - If a ``str`` is provided, expects the name of a stored configuration file.
              See ``show_available_configs()`` and ``save_config_dict()`` for details.
            - If a ``Path`` is provided, expects the path to a valid spikewrap config YAML file.
            - A spikewrap configs dictionary, either including the ``"sorting"`` level
              or the ``"sorting"`` level itself. Only 1 sorter at a time currently supported.
        run_sorter_method
            - if "local", use the current python environment to run sorting (e.g. for `kilosort4`)
            - if a path (either string or Path), must be the path to a matlab repository
              used to run the sorter (e.g. kilosort 2.5 repository).
            - if "docker" or "singularity", docker or singularity will be used to run the sorting.
              singularity images are stored in a folder at the level of "rawdata" and "derivatives".
        per_shank
            If `True`, preprocessed recordings will be split by shank. If preprocessed recordings
            were already split by shank for preprocessing, this should be `False`.
        concat_runs
            If `True`, preprocessed runs will be concatenated togerher before sorting. If runs were
            already concatenated before preprocessing, this should be `False`.
        overwrite
            If `True`, existing outputs will be overwritten. Otherwise, an error will be raised
            if existing outputs are found.
        slurm
            Configuration for submitting the save jobs to a SLURM workload manager.
            If `False` (default), jobs will be run locally. If `True`, job will be run in SLURM
            with default arguments. If a `dict` is provided, it should contain SLURM arguments.
            See `tutorials` in the documentation for details.

        """
        pp_runs: list[PreprocessedRun]
        if not any(self._pp_runs):
            pp_runs = self._load_pp_runs_from_disk()
        else:
            pp_runs = self._pp_runs

        sorting_configs = self._infer_steps_from_configs_argument(configs, "sorting")

        self._sorting_runs = []

        if concat_runs:
            if len(pp_runs) == 1:
                raise ValueError(
                    f"`concat_runs=True` but there is only one preprocessed run: {pp_runs[0]._run_name}"
                )
            else:
                self._sorting_runs = [ConcatSortingRun(pp_runs, self._output_path)]
        else:
            self._sorting_runs = [
                SeparateSortingRun(pp_run, self._output_path) for pp_run in pp_runs
            ]

        for run in self._sorting_runs:
            job_if_slurm = run.sort(
                sorting_configs, run_sorter_method, per_shank, overwrite, slurm
            )
            if slurm:
                self._running_slurm_jobs.append(job_if_slurm)

    def _load_pp_runs_from_disk(self) -> list[PreprocessedRun]:
        """
        Load a list of PreprocessedRun, that have been previously saved, from disk.

        This is used to allow sorting from previously saved data, allowing `session.preprocess()`
        to be skipped. These will be loaded in the order specified in the run names passed to
        this class on instantiation. If this is "all" they will be loaded from disk in glob order.

        TODO
        ----
        It would be nice to load these into self._pp_runs so that they can be re-visualised.

        TODO
        ----
        This badly needs a tidy up
        """
        if self._passed_run_names == "all":
            # Find all folderes with "preprocessed" folder inside,
            # assuming this is an already-preprocessed run.
            run_folders = list(self._output_path.glob("*"))
            passed_run_names = []
            for run_path in run_folders:
                if run_path.is_dir() and any(run_path.glob("preprocessed")):
                    passed_run_names.append(run_path.name)

        else:
            passed_run_names = self._passed_run_names

        if "concat_run" in passed_run_names and len(passed_run_names) != 1:
            raise ValueError(
                "Cannot load `concat_run` alongside separate runs. Specify "
                "the exact runs to sort with the `run_names` argument of `Session`."
            )

        _utils.message_user(
            "Preprocessed runs were loaded from disk, in the order:"
            f"{passed_run_names}"
        )
        pp_runs = []

        for run_name in passed_run_names:

            # For each run, load the stored spikewrap info.
            run_folder = self._output_path / run_name

            file_path = run_folder / "preprocessed" / canon.spikewrap_info_filename()

            if not file_path.is_file():
                raise FileNotFoundError(
                    f"No saved preprocessed data found at: {file_path}"
                )

            with file_path.open("r") as file:
                run_info = yaml.safe_load(file)

            # Based on the number of saved shanks, load the recording objects
            # into a dictionary (keys are shank_id)
            preprocessed_shanks = {}
            for shank_id in run_info["shank_ids"]:

                if shank_id == "grouped":
                    recording_path = run_folder / "preprocessed"
                else:
                    recording_path = run_folder / "preprocessed" / shank_id

                if not recording_path.is_dir():
                    raise FileNotFoundError(
                        f"No preprocessed data found at: {recording_path}"
                    )

                recording = si.load_extractor(recording_path)

                prepro_dict = {
                    run_info["prepro_key"]: recording
                }  # TODO: check naming of this and make sure its consistent

                preprocessed_shanks[shank_id] = prepro_dict

            # Instantiate the class based on the above parameters
            run = PreprocessedRun(
                Path(run_info["raw_data_path"]),
                run_info["ses_name"],
                run_info["run_name"],
                run_info["file_format"],
                Path(run_info["session_output_path"]),
                preprocessed_shanks,
                pp_steps=run_info["pp_steps"],
                orig_run_names=run_info["orig_run_names"],
            )

            pp_runs.append(run)

        return pp_runs

    # Getters -----------------------------------------------------------------

    def wait_for_slurm(self):
        """
        Run a while loop with pause until
        all slurm jobs are complete.
        """
        while True:

            self._running_slurm_jobs = [
                job for job in self._running_slurm_jobs if not job.done()
            ]

            if not any(self._running_slurm_jobs):
                break

            time.sleep(5)

    # Getters -----------------------------------------------------------------

    def get_raw_run_names(self) -> list[str]:
        """
        Return a list of run names for the raw data.

        Their order is the order in which any concatenation
        will be performed.
        """
        return [run._run_name for run in self._raw_runs]

    def get_preprocessed_run_names(self) -> list[str]:
        """
        Return a list of names of the preprocessed data.
        If data was concatenated, the run name will be "concat_run".

        If not concatenated, their order is the order
        concatenation will take place prior to sorting
        (if ``concat_run=True``).
        """
        return [run._run_name for run in self._pp_runs]

    def parent_input_path(self) -> Path:
        """
        Name of the parent path for this sessions raw data
        (i.e. the path of the subject folder).
        """
        return self._parent_input_path

    def get_output_path(self) -> Path:
        """
        The path where processed data will be output for this session.
        """
        return self._output_path

    def load_raw_data(self, overwrite: bool = False) -> None:
        """
        Load raw data, to allow editing of the sync channel.
        Note this will overwrite any previous editing of the
        sync channel.
        """
        if any(self._raw_runs) and not overwrite:
            raise RuntimeError(
                "Runs have already been loaded for this session. "
                "Use `overwrite=True` to load again."
            )

        self._load_raw_data(internal_overwrite=overwrite)

    def get_sync_channel(self, run_idx: int):
        """
        Return the sync channel in a numpy array. Currently only
        Neuropixels (sync channel is 385th channel) supported.

        Parameters
        __________

        run_idx
            Index of the run to get the sync channel from,
            as ordered by ``self.get_raw_run_names()``.
        """
        self._assert_sync_channel_checks()

        return self._raw_runs[run_idx].get_sync_channel()

    def plot_sync_channel(
        self, run_idx: int, show: bool = True
    ) -> list[matplotlib.lines.Line2D]:
        """
        Plot the sync channel for the run.

        Parameters
        ----------

        run_idx
            Index of the run to get the sync channel from,
            as ordered by ``self.get_raw_run_names()``.
        show
            If ``True``, plt.show() is called.
        """
        self._assert_sync_channel_checks()

        return self._raw_runs[run_idx].plot_sync_channel(show)

    def silence_sync_channel(
        self, run_idx: int, periods_to_silence: list[tuple]
    ) -> None:
        """
        Set periods on the sync channel to zero.

        Parameters
        ----------

        run_idx
            Index of the run to get the sync channel from,
            as ordered by ``self.get_raw_run_names()``.
        periods_to_silence
            A list of 2-tuples, where each entry in the tuples are
            the (start, stop) sample to silence. For example,
            [(0, 10), (50, 500)] will set the samples 0 - 10 and
            50 - 500 to zero.
        """
        self._assert_sync_channel_checks()

        self._raw_runs[run_idx].silence_sync_channel(periods_to_silence)

    def save_sync_channel(
        self, overwrite: bool = False, slurm: dict | bool = False
    ) -> None:
        """
        Save all loaded runs sync channel to disk.
        """
        if not self.raw_runs_loaded():
            self._load_raw_data(internal_overwrite=False)

        for run in self._raw_runs:
            job_if_slurm = run.save_sync_channel(overwrite, slurm)

            if slurm:
                self._running_slurm_jobs.append(job_if_slurm)

    def raw_runs_loaded(self):
        return all(run._raw is not None for run in self._raw_runs)

    def _assert_sync_channel_checks(self):
        """ """
        if not any(self._raw_runs):
            raise RuntimeError(
                "Cannot work with sync channels until raw data loaded. "
                "Use `session.load_raw_data()`."
            )

        if any(self._pp_runs) or any(self._sorting_runs):
            raise RuntimeError(
                "Cannot work with the sync channel after preprocessing. "
                "Sync channel must be handled prior to preprocessing. "
                "Instantiate a new Session object to begin a new workflow. "
                "If this is annoying please contact spikewrap."
            )

    # ---------------------------------------------------------------------------
    # Private Functions
    # ---------------------------------------------------------------------------

    # Manage `Runs` -------------------------------------------------------------

    def _load_raw_data(self, internal_overwrite: bool = False) -> None:
        """
        Fill self._raw_runs with a list of `SeparateRawRun` objects,
        each holding data for the run.

        Parameters
        ----------
        internal_overwrite
            Safety flag to ensure overwriting existing runs is intended.

        Notes
        -----
        The session may include a `ephys` folder (NeuroBlueprint) but currently
        non-NeuroBlueprint (no `ephys` folder) is included. `session_path` is the
        path to the `ses-xxx` folder but `get_raw_run_paths` will detect and
        include the `ephys` folder if necessary.
        """
        if self._raw_runs and not internal_overwrite:
            raise RuntimeError(f"Cannot overwrite _runs for session {self._ses_name}")

        session_path = self._parent_input_path / self._ses_name

        run_paths = _loading.get_raw_run_paths(
            self._file_format,
            session_path,
            self._passed_run_names,
        )

        runs: list[SeparateRawRun] = []

        for run_path in run_paths:

            separate_run = SeparateRawRun(
                parent_input_path=run_path.parent,
                parent_ses_name=self._ses_name,
                run_name=run_path.name,
                file_format=self._file_format,
                probe=self._probe,
                sync_output_path=self._output_path / run_path.name,
            )
            separate_run.load_raw_data()
            runs.append(separate_run)

        self._raw_runs = runs

    def _get_concat_raw_run(self) -> ConcatRawRun:
        """
        Concatenate multiple separate runs into a single consolidated `ConcatRawRun`.

        `SeparateRawRun` and `ConcatRawRun` both expose processing functionality
        can be substituted for one another in this context.
        """
        if len(self._raw_runs) == 1:
            raise RuntimeError("Cannot concatenate runs, only one run found.")

        assert all(
            [isinstance(run, SeparateRawRun) for run in self._raw_runs]
        ), "All runs must be type `SeparateRawRun` for `ConcatRawRun"

        _utils.message_user(
            f"Concatenating raw recordings in the following order:"
            f"{self.get_raw_run_names()}"
        )

        return ConcatRawRun(
            self._raw_runs,
            self._parent_input_path,
            self._ses_name,
            self._file_format,
        )

    # Path Resolving -----------------------------------------------------------

    def _output_from_parent_input_path(self) -> Path:
        """
        Infer the output path for the processed session data given the input path.

        Assumes NeuroBlueprint style, in which the output path root is
        a `derivatives` folder in the same location of the `rawdata` folder.

        If this is not a NeuroBlueprint-organised dataset, raise ValueError and
        require explicit passing of `self._output_path`.

        Returns
        -------
        Path
            The inferred NeuroBlueprint session output path.
        """
        sub_path, sub_name = self._resolve_subject_input_path()

        rawdata_path = sub_path.parent

        if rawdata_path.name != "rawdata":
            raise ValueError(
                f"Cannot infer `output_path` from non-NeuroBlueprint "
                f"folder structure (expected 'rawdata'->subject->session "
                f"in path {self._parent_input_path}. "
                f"Pass the session output folder explicitly as `output_path`."
            )

        return rawdata_path.parent / "derivatives" / sub_name / self._ses_name / "ephys"

    # Checkers ------------------------------------------------------------------

    def _resolve_subject_input_path(self) -> tuple[Path, str]:
        """
        Return the path to the subject folder, and the subject name.

        Assumes the subject path is immediately above the session path.
        This is true whether in NeuroBlueprint or other accepted
        folder formats found in the documentation.
        """
        sub_path = self._parent_input_path
        sub_name = sub_path.name

        return sub_path, sub_name

    @staticmethod
    def _check_input_path(parent_input_path: Path) -> None:
        """
        Ensure the path to the parent (subject) folder exists.
        """
        if not parent_input_path.is_dir():
            raise FileNotFoundError(f"{parent_input_path} is not a directory.")

    @staticmethod
    def _check_file_format(file_format: Literal["spikeglx", "openephys"]) -> None:
        """
        Ensure the `file_format` is a permitted value.
        """
        supported_formats = ["spikeglx", "openephys"]

        if file_format not in supported_formats:
            raise ValueError(
                f"`file_format` not recognised. Must be one of: {supported_formats}"
            )

    @staticmethod
    def _infer_steps_from_configs_argument(
        configs, preprocessing_or_sorting
    ) -> dict[str, list]:  # TODO: RENAME !
        """
        Given the possible arguments for `configs` in `preprocess()`,
        infer the `pp_steps` dictionary of preprocessing steps to run.

        TODO
        ----
        This function should be moved when it has use outside this class e.g.
        when Subject class is introduced.
        """
        if not isinstance(configs, dict):
            if isinstance(configs, Path) or "/" in configs or "\\" in configs:
                settings = config_utils.load_config_dict(configs)[
                    preprocessing_or_sorting
                ]
            else:
                pp_steps, sorting = config_utils.get_configs(configs)
                settings = (
                    pp_steps if preprocessing_or_sorting == "preprocessing" else sorting
                )
        else:
            # maybe the user did not include the "preprocessing" or "sorting" top level
            settings = configs.get(preprocessing_or_sorting, configs)

        return settings
