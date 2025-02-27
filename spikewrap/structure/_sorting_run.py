import spikeinterface.full as si

from spikewrap.utils import _utils

# TODO: manage lifetime


class SortingRun:
    def __init__(self, pp_run):  # SeparatePreprocessRun
        """ """
        self._preprocessed_recording = {
            key: _utils._get_dict_value_from_step_num(preprocessed_data._data, "last")[
                0
            ]
            for key, preprocessed_data in pp_run._preprocessed.items()
        }
        self._run_names = [run.run_name for run in pp_run]
        self._output_path = pp_run._output_path

    def sort(self, sorting_configs, run_method, per_shank, overwrite, slurm):
        # do some checks on sorter, either installed, or not installed etc.
        # run method... parse it properly to produce run_sorter outputs
        # handle overwrite

        if not run_method == "local":
            raise NotImplementedError()
        breakpoint()
        assert len(sorting_configs) == 1
        sorter_name = list(sorting_configs.keys())[0]  # TODO: handle multiple
        sorter_kwargs = sorting_configs[sorter_name]

        if per_shank:
            breakpoint()
            if "grouped" not in self._preprocessed_recording:
                raise RuntimeError("is already!")
            else:
                assert len(self._preprocessed_recording) == 1, "MESSAGE"
                assert len(self._run_names) == 1, "MESSAGE"

                breakpoint()
                recording = self._preprocessed_recording["grouped"]

                if recording.get_property("group") is None:
                    raise ValueError(
                        f"Cannot split run {self._run_names[0]} by shank as there is no 'group' property."
                    )
                self._preprocessed_recording = recording.split_by("group")

        if overwrite:
            self._delete_existing_run_except_slurm_logs(
                self._output_path / "sorting"
            )  # centralise this

        # if slurm:
        #    ...

        # for shank in shank...
        for rec_name, recording in self._preprocessed_recording.items():

            out_path = self._output_path / "sorting"
            if rec_name != "grouped":
                out_path = out_path / f"shank_{rec_name}"

            si.run_sorter(
                sorter_name=sorter_name,
                recording=recording,
                folder=out_path,
                verbose=True,
                docker_image=False,
                singularity_image=False,
                **sorter_kwargs,
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
