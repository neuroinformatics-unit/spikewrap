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
        self._output_path = pp_run._output_path

    def sort(self, sorting_configs, run_method, per_shank, overwrite, slurm):
        # do some checks on sorter, either installed, or not installed etc.
        # run method... parse it properly to produce run_sorter outputs
        # handle overwrite
        if not run_method == "local":
            raise NotImplementedError()

        assert len(sorting_configs) == 1
        sorter_name = list(sorting_configs.keys())[0]  # TODO: handle multiple
        sorter_kwargs = sorting_configs[sorter_name]

        if per_shank:
            if "grouped" not in self._preprocessed_recording:
                raise RuntimeError("is already!")
            else:
                self._split_by_shank()

        # if overwrite:
        # handle overwrite

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
