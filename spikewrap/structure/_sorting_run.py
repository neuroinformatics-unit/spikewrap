import shutil

import spikeinterface.full as si

from spikewrap.utils import _utils

# TODO: manage lifetime


class BaseSortingRun:

    def sort(self, sorting_configs, run_sorter_method, per_shank, overwrite, slurm):
        # do some checks on sorter, either installed, or not installed etc.
        # run method... parse it properly to produce run_sorter outputs
        # handle overwrite
        if slurm:
            self._sort_slurm(
                sorting_configs, run_sorter_method, per_shank, overwrite, slurm
            )
            return

        if not run_sorter_method == "local":
            raise NotImplementedError()

        assert len(sorting_configs) == 1
        sorter_name = list(sorting_configs.keys())[0]  # TODO: handle multiple
        sorter_kwargs = sorting_configs[sorter_name]

        if per_shank:
            if "grouped" not in self._preprocessed_recording:
                raise RuntimeError("is already!")
            else:
                assert len(self._preprocessed_recording) == 1, "MESSAGE"

                recording = self._preprocessed_recording["grouped"]

                if recording.get_property("group") is None:
                    raise ValueError(
                        f"Cannot split run {self._run_name} by shank as there is no 'group' property."
                    )
                self._preprocessed_recording = recording.split_by("group")

        if self._output_path.is_dir():  # TODO: check this
            if overwrite:
                self._delete_existing_run_except_slurm_logs(  # centralise this
                    self._output_path
                )
            else:
                raise RuntimeError("need `overwrite`.")

        # for shank in shank...
        for rec_name, recording in self._preprocessed_recording.items():

            out_path = self._output_path
            if rec_name != "grouped":
                out_path = out_path / f"shank_{rec_name}"

            si.run_sorter(
                sorter_name=sorter_name,
                recording=recording,
                folder=out_path,
                verbose=True,
                docker_image=False,
                singularity_image=False,
                remove_existing_folder=True,  # TODO: integrate a bit better, ensure this doesn't lead anything weird..?
                **sorter_kwargs,
            )

    def sort_slurm(
        self, sorting_configs, run_sorter_method, per_shank, overwrite, slurm
    ):
        """ """
        slurm_ops: dict | bool = slurm if isinstance(slurm, dict) else False

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

    # TODO: DIRECT COPY!
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


class SortingRun(BaseSortingRun):
    def __init__(self, pp_run, session_output_path):  # SeparatePreprocessRun
        """ """
        self._preprocessed_recording = {
            key: _utils._get_dict_value_from_step_num(preprocessed_data._data, "last")[
                0
            ]
            for key, preprocessed_data in pp_run._preprocessed.items()
        }
        self._run_name = pp_run._run_name
        self._output_path = (
            session_output_path / self._run_name / "sorting"
        )  # use below


class ConcatSortingRun(BaseSortingRun):  # TODO
    def __init__(self, pp_runs_list, session_output_path):
        """ """
        self._orig_run_names = [
            run._run_name for run in pp_runs_list
        ]  # TODO: need on ConcatSortingRun?
        self._run_name = "concat_runs"  # TODO: check this matches the preprocessing
        self._output_path = (
            session_output_path / self._run_name / "sorting"
        )  # TODO: use this above...

        shank_keys = list(pp_runs_list[0]._preprocessed.keys())
        # check keys in all

        recordings_dict = {key: [] for key in shank_keys}

        for run in pp_runs_list:
            for key in shank_keys:
                if key not in run._preprocessed:
                    raise ValueError("Say something")

                recordings_dict[key].append(
                    _utils._get_dict_value_from_step_num(
                        run._preprocessed[key]._data, "last"
                    )[0]
                )

        for key in shank_keys:
            recordings_dict[key] = si.concatenate_recordings(recordings_dict[key])

        self._preprocessed_recording = recordings_dict
