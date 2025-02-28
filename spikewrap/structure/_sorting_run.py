from spikeinterface.sorters import run_sorter

from spikewrap.processing._preprocessing_run import (
    ConcatPreprocessRun,
    SeparatePreprocessRun,
)
from spikewrap.utils import _slurm, _utils


class BaseSortingRun:

    def sort(
        self,
        sorting_configs: dict,
        run_sorter_method: str,
        per_shank: bool,
        overwrite: bool,
        slurm: bool | dict,
    ):
        """

        Parameters
        ----------

        """
        if slurm:
            self._sort_slurm(
                sorting_configs, run_sorter_method, per_shank, overwrite, slurm
            )
            return

        assert len(sorting_configs) == 1, "Only one sorter supported."
        ((sorter_name, sorter_kwargs),) = sorting_configs.items()

        if per_shank:
            if "grouped" not in self._preprocessed_recording:
                raise RuntimeError(
                    "`per_shank=True` but the recording was already split per shank for preprocessing."
                )
            else:
                assert (
                    len(self._preprocessed_recording) == 1
                    and "grouped" in self._preprocessed_recording
                ), ""
                recording = self._preprocessed_recording["grouped"]

                if recording.get_property("group") is None:
                    raise ValueError(
                        f"Cannot split run {self._run_name} by shank as there is no 'group' property."
                    )
                self._preprocessed_recording = recording.split_by("group")

        if self._output_path.is_dir():
            if overwrite:
                _utils.message_user(
                    f"`overwrite=True`, so deleting all files and folders "
                    f"(except for slurm_logs) at the path:\n"
                    f"{output_path}"
                )
                _slurm._delete_folder_contents_except_slurm_logs(output_path)
            else:
                raise RuntimeError("need `overwrite`.")

        for rec_name, recording in self._preprocessed_recording.items():

            out_path = self._output_path
            if rec_name != "grouped":
                out_path = out_path / f"shank_{rec_name}"

            run_sorter(
                sorter_name=sorter_name,
                recording=recording,
                folder=out_path,
                verbose=True,
                docker_image=False,
                singularity_image=False,
                remove_existing_folder=True,  # TODO: integrate a bit better, ensure this doesn't lead anything weird..?
                **sorter_kwargs,
            )

    def _sort_slurm(
        self, sorting_configs, run_sorter_method, per_shank, overwrite, slurm
    ):
        """ """
        slurm_ops: dict | bool = slurm if isinstance(slurm, dict) else False

        kilosort_list = ["kilosort", "kilosort2", "kilosort2_5", "kilosort3"]
        matlab_list = kilosort_list + ["HDSort", "IronClust", "Waveclus"]

        run_docker, run_singularity = False
        if run_sorter_method == "local":
            if sorter in kilosort_list:
                raise ValueError("Some error")

        elif isinstance(run_sorter_method, str) or isinstance(run_sorter_method, Path):
            assert sorter in matlab_list, "MUST BE KILOSORT"
            if sorter in kilosort_list:
                pass
                # check mex files are found in kilosort and raise if not!
                # raise if not a real file.
            # if sorter == "":
            #    HDSortSorter.set_hdsort_path()

        elif run_sorter_method == "docker":
            run_docker = True
        elif run_sorter_method == "singularity":
            run_singularity = True

        _slurm.run_in_slurm(
            slurm_ops,
            func_to_run=self.sort,
            func_opts={
                "sorting_configs": sorting_configs,
                "run_sorter_method": run_sorter_method,
                "per_shank": per_shank,
                "overwrite": overwrite,
                "slurm": False,
            },
            log_base_path=self._output_path,
        )


class SortingRun(BaseSortingRun):
    def __init__(
        self,
        pp_run: ConcatPreprocessRun | SeparatePreprocessRun,
        session_output_path: Path,
    ):
        """ """
        self._run_name = pp_run._run_name
        self._output_path = session_output_path / self._run_name / "sorting"

        self._preprocessed_recording = {
            key: _utils._get_dict_value_from_step_num(preprocessed_data._data, "last")[
                0
            ]
            for key, preprocessed_data in pp_run._preprocessed.items()
        }


class ConcatSortingRun(BaseSortingRun):
    def __init__(
        self, pp_runs_list: List[SeparatePreprocessRun], session_output_path: Path
    ):
        """
        TODO

        """
        self._orig_run_names = [run._run_name for run in pp_runs_list]
        self._run_name = "concat_run"
        self._output_path = session_output_path / self._run_name / "sorting"

        shank_keys = list(pp_runs_list[0]._preprocessed.keys())

        recordings_dict = {key: [] for key in shank_keys}

        # Create a dict (key is "grouped" or shank number) of lists where the
        # lists contain all recordings to concatenate for that shank
        for run in pp_runs_list:
            for key in shank_keys:

                assert key in run._preprocessed, (
                    "Somehow grouped and per-shank recordings are mixed. "
                    "This should not happen."
                )

                preprocessed_recording = _utils._get_dict_value_from_step_num(
                    run._preprocessed[key]._data, "last"
                )[0]

                recordings_dict[key].append(preprocessed_recording)

        # Concatenate the lists for each shank into a single recording
        for key in shank_keys:
            recordings_dict[key] = si.concatenate_recordings(recordings_dict[key])

        self._preprocessed_recording = recordings_dict
