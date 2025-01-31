from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import matplotlib

from pathlib import Path

import numpy as np

from spikewrap.configs import config_utils
from spikewrap.process import _loading
from spikewrap.structure._run import ConcatRun, SeparateRun
from spikewrap.utils import _utils


class Session:
    """
    Represents an electrophysiological recording session, consisting of a single or multiple runs.

    Exposes ``preprocess()``, ``plot_preprocessed()`, and ``save_preprocessed()`` functions to handle preprocessing of all runs.

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

    Notes
    -----
    The responsibility of this class is to manage the processing of runs
    contained within the session. Runs are held in ``self._runs``, a list of
    ``SeparateRun`` or ``ConcatRun`` classes. Runs are loaded from raw data
    as separate runs, and will be converted to a ``ConcatRun`` if concatenated.

    The attributes on this class (except for ``self._runs``) are to be treated
    as constant for the lifetime of the class. For example, the output path
    should not be changed during the class instance lifetime.

    When ``preprocess`` is called, all runs are re-loaded and operations performed
    from scratch. This is to cleanly handle concatenation of runs and possible
    splitting of multi-shank recordings. This is more robust than attempting
    to continually concatenate / split runs and shanks.
    """

    def __init__(
        self,
        subject_path: Path | str,
        session_name: str,
        file_format: Literal["spikeglx", "openephys"],
        run_names: Literal["all"] | list[str] = "all",
        output_path: Path | None = None,
    ):
        """ """
        parent_input_path = Path(subject_path)
        self._check_input_path(parent_input_path)
        self._check_file_format(file_format)

        # These parameters should be treated as constant and never changed
        # during the lifetime of the class. Use the properties (which do not
        # expose a setter) for both internal and external calls.
        self._passed_run_names = run_names
        self._file_format = file_format

        self._parent_input_path = parent_input_path
        self._ses_name = session_name
        self._output_path = (
            Path(output_path) if output_path else self._output_from_parent_input_path()
        )

        # self._runs may be updated during the lifetime of the object,
        # but is private to this class.
        self._runs: list[SeparateRun | ConcatRun] = []
        self._create_run_objects()

    # ---------------------------------------------------------------------------
    # Public Functions
    # ---------------------------------------------------------------------------

    def load_raw_data(self) -> None:
        """
        Load the raw data from each run into SpikeInterface
        recording objects.

        This function can be used to check data is loading successfully,
        but can be skipped, with ``preprocess()`` run directly.

        Data is loaded lazily at this stage (recording objects are created
        but no data is actually loaded from disk).
        """
        _utils.message_user(
            f"Loading runs from session path: {self._parent_input_path}"
        )

        for run in self._runs:
            _utils.message_user(f"Loading run: {run._run_name}")
            run.load_raw_data()

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
            Use ``session.get_run_names()`` to check the order of concatenation.
        per_shank
            If ``True``, perform preprocessing on each shank separately.
        """
        pp_steps = self._infer_pp_steps_from_configs_argument(configs)

        _utils.show_preprocessing_configs(pp_steps)

        self._create_run_objects(internal_overwrite=True)  # refresh everything

        for run in self._runs:
            run.load_raw_data()

        if concat_runs:
            self._concat_runs()

        for run in self._runs:
            run.preprocess(pp_steps, per_shank)

    def save_preprocessed(  # TODO: document, each run is in a separate SLURM job! keep like this for now
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
        for run in self._runs:
            run.save_preprocessed(overwrite, chunk_duration_s, n_jobs, slurm)

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
            - If an integer, plots preprocessed data for the run at the specified index in ``self._runs``.
        mode
            Determines the plotting style, a heatmap-style or line plot.
        time_range
            Time range (start, end), in seconds, to plot. e.g. (0.0, 1.0)
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

        all_runs = self._runs if run_idx == "all" else [self._runs[run_idx]]

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

    # Getters -----------------------------------------------------------------

    def get_run_names(self) -> list[str]:
        """
        Return a list of run names from the self._runs list.

        If run concatenation is performed, the order of this
        list will be the order of concatenation. If concatenation
        was already performed, the run name will be ``"concat_run"``.
        """
        return [run._run_name for run in self._runs]

    def parent_input_path(self) -> Path:  # TODO: add docs
        return self._parent_input_path

    def get_passed_run_names(self) -> Literal["all"] | list[str]:
        return self._passed_run_names

    def get_output_path(self):
        return self._output_path

    # ---------------------------------------------------------------------------
    # Private Functions
    # ---------------------------------------------------------------------------

    # Manage `Runs` -------------------------------------------------------------

    def _create_run_objects(self, internal_overwrite: bool = False) -> None:
        """
        Fill self._runs with a list of `SeparateRun` objects, each
        holding data for the run. The objects are instantiated here but
        recordings are not loaded, these are loaded with self.load_raw_data().

        This function overwrites all exiting runs.

        Parameters
        ----------
        internal_overwrite
            Safety flag to ensure overwriting existing runs is intended.
        """
        if self._runs and not internal_overwrite:
            raise RuntimeError(f"Cannot overwrite _runs for session {self._ses_name}")

        session_path = (
            self._parent_input_path / self._ses_name
        )  # will not include "ephys"

        run_paths = _loading.get_run_paths(
            self._file_format,
            session_path,
            self._passed_run_names,
        )

        runs: list[SeparateRun] = []

        for run_path in run_paths:
            runs.append(
                SeparateRun(
                    parent_input_path=run_path.parent,  # may include "ephys" if NeuroBlueprint
                    parent_ses_name=self._ses_name,
                    run_name=run_path.name,
                    session_output_path=self._output_path,
                    file_format=self._file_format,
                )
            )
        self._runs = runs  # type: ignore

    def _concat_runs(self) -> None:
        """
        Concatenate multiple separate runs into a single consolidated `ConcatRun`.

        `SeparateRun` and `ConcatRun` both expose processing functionality
        can be substituted for one another in this context.
        """
        if len(self._runs) == 1:
            raise RuntimeError("Cannot concatenate runs, only one run found.")

        assert self.get_run_names() != (
            "concat_run"
        ), "Expected, runs are already concatenated."  # TODO: Expose

        _utils.message_user(
            f"Concatenating runs in the following order:" f"{self.get_run_names()}"
        )

        assert all(
            [isinstance(run, SeparateRun) for run in self._runs]
        ), "All runs must be type `SeparateRun` for `ConcatRun"

        self._runs = [
            ConcatRun(
                self._runs,  # type: ignore
                self._parent_input_path,
                self._ses_name,
                self._output_path,
                self._file_format,
            )
        ]

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
                f"folder structure (expected 'rawdata'->subject->session\n"
                f"in path {self._parent_input_path}\n"
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
    def _infer_pp_steps_from_configs_argument(configs) -> dict[str, list]:
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
                pp_steps = config_utils.load_config_dict(configs)["preprocessing"]
            else:
                pp_steps, _ = config_utils.get_configs(configs)
        else:
            # maybe the user did not include the "preprocessing" top level
            pp_steps = configs.get("preprocessing", configs)

        return pp_steps
