from spikewrap.process import _loading, _saving
from spikewrap.structure._preprocessed import Preprocessed
from spikewrap.utils import _utils, _slurm
import shutil
import spikeinterface.full as si
from spikewrap.visualise._visualise import visualise_run_preprocessed
from spikewrap.configs._backend import canon


# if class does not expose a property, do not use its attributes,
# will be markd private.

class Run:
    """
    This is immutable.

    # Responsibilities:
        - hold raw data of the run (either split per shank or grouped)
        - hold preprocessed data of the run (either split per shank or grouped)
        - save sync channel when is saved across all runs
        - handle overwriting (at the run level)

    Note the inheritence...
    """
    def __init__(self, parent_input_path, run_name, session_output_path, file_format):

        # these are fixed, must never be changed in the lifetime of the class
        self._parent_input_path = parent_input_path
        self._run_name = run_name
        self._output_path = session_output_path / self._run_name
        self._file_format = file_format

        # data holders, expose as properties.
        self._raw = {}
        self._preprocessed = {}
        self._sync = None

    # TODO: make it explicit with getter / setter these attributes are const!?
    #
    # ---------------------------------------------------------------------------
    # Public Functions
    # ---------------------------------------------------------------------------

    def load_raw_data(self, internal_overwrite=False):
        """
        TODO: again, figure out lifetime!
        I think its okay....
        """
        if self.raw_is_loaded() and not internal_overwrite:
            raise RuntimeError("Cannot overwrite Run().")

        without_sync, with_sync = _loading.load_data(
            self._parent_input_path / self._run_name,
            self._file_format
        )

        self._raw = {canon.grouped_shankname(): without_sync}
        self._sync = with_sync

    def refresh_data(self):
        """
        """
        self._preprocessed = {}
        self._sync = None
        self.load_raw_data(internal_overwrite=True)

    def preprocess(self, pp_steps, per_shank):
        """
        Note because this class is fresh, we can assume only run once.
        IMMUTABLE CLASS! ONE-SHOT CLASS!
        """
        assert not self._preprocessing_is_run(), "Preprocessing was already run, can only be run once per class instance."

        assert self.raw_is_loaded(), "Data should already be loaded at this stage, it is managed by the Session()."

        if per_shank:
            self._split_by_shank()

        for key, raw_rec in self._raw.items():
            rec_name = f"shank_{key}" if key != canon.grouped_shankname() else key

            self._preprocessed[key] = Preprocessed(
                raw_rec, pp_steps, self._output_path, rec_name
            )

    def save_preprocessed(self, overwrite, chunk_size, n_jobs, slurm):
        """
        """
        if slurm:
            self._save_preprocessed_slurm(overwrite, chunk_size, n_jobs, slurm)
            return

        _utils.message_user(f"Saving data for: {self._run_name}...")

        if n_jobs != 1:
            si.set_global_job_kwargs(n_jobs=n_jobs)

        if self._output_path.is_dir():  # getter func?
            if overwrite:
                shutil.rmtree(self._output_path)
            else:
                raise RuntimeError(f"`overwrite` is `False` but data already exists at the run path: {run_path}.")

        self._save_sync_channel()

        for preprocessed in self._preprocessed.values():
            preprocessed.save_binary(chunk_size)

    def plot_preprocessed(self, show, mode, time_range, show_channel_ids):

        if not self._preprocessing_is_run():
            raise RuntimeError("Preprocessing has not been run.")

        fig = visualise_run_preprocessed(
            self._run_name,
            show,
            self._preprocessed,
            mode=mode,
            time_range=time_range,
            show_channel_ids=show_channel_ids
        )

        return fig

    # Helpers -----------------------------------------------------------------

    def raw_is_loaded(self):
        return self._raw != {}

    # ---------------------------------------------------------------------------
    # Private Functions
    # ---------------------------------------------------------------------------

    def _split_by_shank(self):
        """
        """
        assert not self._is_split_by_shank(), (f"Attempting to split by shank, but the recording"
                                               f"in run: {self._run_name} has already been split."
                                               f"This should not happen. Please contact the spikewrap team.")

        if (recording := self._raw[canon.grouped_shankname()]).get_property("group") is None:
            raise ValueError(f"Cannot split run {self._run_name} by shank as there is no 'group' property.")

        self._raw = recording.split_by("group")
        self._raw = {str(key): value for key, value in self._raw.items()}

        _utils.message_user(f"Split run: {self._run_name} by shank. There are {len(self._raw)} shanks. ")


    def _save_preprocessed_slurm(self, overwrite, chunk_size, n_jobs, slurm):
        """
        """
        slurm_ops = slurm if isinstance(slurm, dict) else None

        _slurm.run_in_slurm(
            slurm_ops,
            lambda: self.save_preprocessed(overwrite, chunk_size, n_jobs, False),
            {},
            log_base_path=self._output_path
        )

    def _save_sync_channel(
        self
    ) -> None:
        """
        Save the sync channel separately. In SI, sorting cannot proceed
        if the sync channel is loaded to ensure it does not interfere with
        sorting. As such, the sync channel is handled separately here.
        """
        sync_output_path = self._output_path / canon.sync_folder()

        _utils.message_user(f"Saving sync channel for: {self._run_name}...")

        if self._sync:
            _saving.save_sync_channel(self._sync, sync_output_path, self._file_format)

    # Helpers -----------------------------------------------------------------

    def _is_split_by_shank(self):
        return len(self._raw) > 1

    def _preprocessing_is_run(self):
        return any(self._preprocessed)

# -----------------------------------------------------------------------------
# Concatenate Runs Object
# -----------------------------------------------------------------------------

# maybe should take parent path and name after all. Then can make inheritence much nicer.
# parent_input_path, name, raw data...
class ConcatRun(Run):
    """

    """
    # TODO: tidy this up...
    def __init__(self, session_output_path, runs_list, file_format):
        super(ConcatRun, self).__init__(
            parent_input_path=None,
            run_name="concat_run",  # TODO: expose
            session_output_path=session_output_path,
            file_format=file_format,
        )
        # TODOI:STORE (concat_run_name())
        # TODO: do way more checks on the recordings to concatenate. For example,
        # they should all have the same number of channels, groups, etc. Checl maybe
        # this is already done in concat session functions.

        # For list of runs to concatenate, checking along the way
        raw_data = []
        sync_data = []
        orig_run_names = []

        for run in runs_list:

            assert run.raw_is_loaded(), ("Something has gone wrong, raw data should be loaded at "
                                         "concat run stage. Contact spikewrap team.")
            if run._is_split_by_shank():
                raise ValueError(
                    "Cannot concatenate runs that have already been split by shank.\n"
                    "Something unexpected has happened. Please contact the spikewrap team.")

            assert run._preprocessed == {}, f"{run._preprocessed}: Preprocessing already run, this is not expected. Contact spikewrap team."

            raw_data.append(run._raw)
            sync_data.append(run._sync)
            orig_run_names.append(run._run_name)

        assert all(list(dict_.keys()) == [canon.grouped_shankname()] for dict_ in raw_data), "triple check we dont have shanks yet"
        assert self._preprocessed == {}, "Something has gone wrong in the inheritance."

        key = canon.grouped_shankname()  # doc this

        # Concatenate and store the recordings
        self._raw = {key: si.concatenate_recordings(
            [data[key] for data in raw_data]
        )}

        self._sync = None if not all(sync_data) else si.concatenate_recordings(sync_data)

        self._preprocessed = {}
        self._orig_run_names = orig_run_names

    def load_raw_data(self):
        raise NotImplementedError("Cannot load data on a concatenated recording."
                                  "It is already run, and the input path does not exist.")