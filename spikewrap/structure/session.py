from pathlib import Path
from spikewrap.structure._run import Run, ConcatRun
from spikewrap.utils import _utils
from spikewrap.configs import config_utils
from spikewrap.process import _loading
import numpy as np


class Session:
    """
    RUN ORDER
    TODO: check what I did before, specify order! want to specify with run name but for now use idx

    Responsibilities
    - load runs
    - concatenate runs
    - preprocess runs
    - # this is very mutable class! It is responsible for managing the lifertime of its runs

    EXPLAIN what _runs are. same for runs() it is confusing...

    TODO: can set probe here for custom probe
   """
    def __init__(self, subject_path, session_name, file_format, run_names="all", output_path=None):  # TODO: check file format
        """
        """
        parent_input_path = Path(subject_path)
        self._check_input_path(parent_input_path)
        self._check_file_format(file_format)

        self._passed_run_names = run_names
        self._file_format = file_format

        self._parent_input_path = parent_input_path
        self._ses_name = session_name
        self._output_path = Path(output_path) if output_path else self._output_from_parent_input_path()

        self._runs = {}
        self._create_run_objects()

    # ---------------------------------------------------------------------------
    # Public Functions
    # ---------------------------------------------------------------------------

    def load_raw_data(self):
        for run in self._runs:
            run.load_raw_data()

    def preprocess(
            self,
            pp_steps,
            concat_runs=False,
            per_shank=False,
    ):
        """
        This must refresh everything.
        TODO: try and guess n_jobs? "estimate" as default?
        """
        if not isinstance(pp_steps, dict):
            pp_steps = config_utils.get_configs(pp_steps)

        _utils.show_preprocessing_dict(pp_steps)

        # Refresh everything
        self._create_run_objects(internal_overwrite=True)

        for run in self._runs:
            run.load_raw_data()

        if concat_runs:
            self._concat_runs()

        for run in self._runs:
            run.preprocess(
                pp_steps, per_shank
            )

    def save_preprocessed(self, overwrite=False, chunk_size=None, n_jobs=1, slurm=False):
        """
        """
        for run in self._runs:
            run.save_preprocessed(overwrite, chunk_size, n_jobs, slurm)

    def plot_preprocessed(self, run_idx="all", mode="map", time_range=(0, 1), show_channel_ids=True, show=False):

        time_range = np.array(time_range, dtype=np.float64)

        all_runs = self._runs if run_idx == "all" else self._runs[run_idx]

        all_figs = {}

        for run in all_runs:
            fig = run.plot_preprocessed(show, mode=mode, time_range=time_range, show_channel_ids=show_channel_ids)

            all_figs[run._run_name] = fig

        return all_figs

    # Helpers -----------------------------------------------------------------

    def get_run_names(self):
        return [run._run_name for run in self._runs]

    # ---------------------------------------------------------------------------
    # Private Functions
    # ---------------------------------------------------------------------------

    # Manage `Runs` -------------------------------------------------------------

    def _create_run_objects(self, internal_overwrite=False):
        """
        """
        if self._runs and not internal_overwrite:
            raise RuntimeError(f"Cannot overwrite _runs for session {self._ses_name}")

        run_paths = _loading.get_run_paths(
            self._file_format,
            self._parent_input_path / self._ses_name,
            self._passed_run_names
        )

        runs = []
        for run_path in run_paths:
            runs.append(
                Run(parent_input_path=run_path.parent,
                    run_name=run_path.name,
                    session_output_path=self._output_path,
                    file_format=self._file_format,
                )
        )
        self._runs = runs

    def _concat_runs(self):
        """
        """
        if len(self._runs) == 1:
            raise RuntimeError("Cannot concatenate runs, only one run found.")

        assert self.get_run_names() != ("concat_run"), "Expected, runs are already concatenated."  # TODO: Expose

        _utils.message_user(
            f"Concatenating runs in the following order:"
            f"{self.get_run_names()}"
        )

        self._runs=[ConcatRun(
            self._output_path, self._runs, self._file_format
        )]

    # Path Resolving -----------------------------------------------------------

    def _output_from_parent_input_path(self):
        """
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

    # Checks ------------------------------------------------------------------

    def _check_input_path(self, parent_input_path):
        """
        """
        if not parent_input_path.is_dir():
            raise FileNotFoundError(f"{parent_input_path} is not a directory.")

    def _check_file_format(self, file_format):
        supported_formats = ["spikeglx", "openephys"]
        if not file_format in supported_formats:
            raise ValueError(f"`file_format` not recognised. Must be one of: {supported_formats}")

    def _resolve_subject_input_path(self):
        """
        NeuroBlueprint or otherwise, the subject folder MUST
        be above the session folder.
        """
        sub_path = self._parent_input_path
        sub_name = sub_path.name

        return sub_path, sub_name
