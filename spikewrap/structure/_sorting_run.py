import shutil
from pathlib import Path
from typing import Literal

import spikeinterface
import spikeinterface.full as si
from spikeinterface.sorters import run_sorter
from spikeinterface.sorters.runsorter import SORTER_DOCKER_MAP

from spikewrap.structure._preprocess_run import (
    ConcatPreprocessRun,
    SeparatePreprocessRun,
)
from spikewrap.utils import _managing_sorters, _slurm


class BaseSortingRun:
    """ """

    def __init__(
        self, run_name, session_output_path, output_path, preprocessed_recording
    ):
        self._run_name = run_name
        self._session_output_path = session_output_path
        self._output_path = output_path
        self._preprocessed_recording = preprocessed_recording

    def sort(
        self,
        overwrite: bool,
        sorting_configs: dict,
        run_sorter_method: str,
        per_shank: bool,
        slurm: bool | dict,
    ):
        """

        Parameters
        ----------

        """
        if slurm:
            self._sort_slurm(
                overwrite, sorting_configs, run_sorter_method, per_shank, slurm
            )
            return

        assert len(sorting_configs) == 1, "Only one sorter supported."
        ((sorter, sorter_kwargs),) = sorting_configs.items()

        run_docker, run_singularity = self._configure_run_sorter_method(
            sorter,
            run_sorter_method,
        )

        if per_shank:
            self.split_per_shank()

        self.handle_overwrite_output_path(overwrite)

        for rec_name, recording in self._preprocessed_recording.items():

            out_path = self._output_path
            if rec_name != "grouped":
                out_path = out_path / rec_name

            run_sorter(
                sorter_name=sorter,
                recording=recording,
                folder=out_path,
                verbose=True,
                docker_image=run_docker,
                singularity_image=run_singularity,
                remove_existing_folder=False,
                **sorter_kwargs,
            )

    # TODO: only delete "sorting" but not preprocessing!
    def handle_overwrite_output_path(self, overwrite):
        """ """
        if self._output_path.is_dir():
            if overwrite:
                shutil.rmtree(self._output_path)
            else:
                raise RuntimeError("need `overwrite`.")

    def _sort_slurm(
        self,
        overwrite: bool,
        sorting_configs: dict,
        run_sorter_method: str | Path,
        per_shank: bool,
        slurm: bool | dict,
    ):
        """ """
        slurm_ops: dict | bool = slurm if isinstance(slurm, dict) else False

        _slurm.run_in_slurm(
            slurm_ops,
            func_to_run=self.sort,
            func_opts={
                "overwrite": overwrite,
                "sorting_configs": sorting_configs,
                "run_sorter_method": run_sorter_method,
                "per_shank": per_shank,
                "overwrite": overwrite,
                "slurm": False,
            },
            log_base_path=self._output_path,
        )

    def split_per_shank(self):
        """ """
        if "grouped" not in self._preprocessed_recording:
            raise RuntimeError(
                "`per_shank=True` but the recording was already split per shank for preprocessing."
            )
        assert (
            len(self._preprocessed_recording) == 1
        ), "There should only be a single recording before splitting by shank."

        recording = self._preprocessed_recording["grouped"]

        if recording.get_property("group") is None:
            raise ValueError(
                f"Cannot split run {self._run_name} by shank as there is no 'group' property."
            )

        split_recording = recording.split_by("group")

        self._preprocessed_recording = {
            f"shank_{key}": value for key, value in split_recording.items()
        }

    def get_singularity_image_path(
        self, sorter: str
    ) -> Path:  # TODO: maybe pass this from above.
        """ """
        spikeinterface_version = spikeinterface.__version__

        sorter_path = (
            self._session_output_path.parent.parent.parent  # TODO: hacky, this is the folder containing rawdata / derivatives
            / "sorter_images"
            / sorter
            / spikeinterface_version
            / SORTER_DOCKER_MAP[sorter]
        )

        if not sorter_path.is_file():
            _managing_sorters._download_sorter(sorter, sorter_path)

        return sorter_path

    def _configure_run_sorter_method(
        self, sorter: str, run_sorter_method: str | Path
    ) -> tuple[bool, Literal[False] | Path]:
        """ """
        kilosort_matlab_list = ["kilosort", "kilosort2", "kilosort2_5", "kilosort3"]
        matlab_list = kilosort_matlab_list + ["HDSort", "IronClust", "Waveclus"]

        run_singularity: Literal[False] | Path

        run_docker = run_singularity = False

        if run_sorter_method == "local":
            if sorter in matlab_list:
                raise ValueError("Some error")

        elif isinstance(run_sorter_method, str) or isinstance(run_sorter_method, Path):

            repo_path = Path(run_sorter_method)

            if not repo_path.is_dir():
                raise FileNotFoundError(
                    f"No repository for {sorter} found at: {repo_path}"
                )

            assert sorter in matlab_list, "MUST BE KILOSORT"

            if sorter in kilosort_matlab_list:
                pass
                # check mex files are found in kilosort and raise if not!
                # raise if not a real file.
                # if sorter == "":
                #    HDSortSorter.set_hdsort_path()

            assert Path(run_sorter_method)

            setter_functions = {
                "kilosort": si.KilosortSorter.set_kilosort_path,
                "kilosort2": si.Kilosort2Sorter.set_kilosort2_path,
                "kilosort2_5": si.Kilosort2_5Sorter.set_kilosort2_5_path,
                "kilosort3": si.Kilosort3Sorter.set_kilosort3_path,
                "HDSort": si.HDSortSorter.set_hdsort_path,
                "IronClust": si.IronClustSorter.set_ironclust_path,
                "Waveclus": si.WaveClusSorter.set_waveclus_path,
            }

            setter_functions[sorter](run_sorter_method)

        elif run_sorter_method == "docker":
            assert _checks._docker_desktop_is_running(), (
                f"The sorter {sorter} requires a virtual machine image to run, but "
                f"Docker is not running. Open Docker Desktop to start Docker."
            )
            run_docker = True

        elif run_sorter_method == "singularity":
            if not _checks._system_call_success("singularity version"):
                raise RuntimeError(
                    "`singularity` is not installed, cannot run the sorter with singularity."
                )

            run_singularity = self.get_singularity_image_path(sorter)

        return run_docker, run_singularity


class SortingRun(BaseSortingRun):
    def __init__(
        self,
        pp_run: ConcatPreprocessRun | SeparatePreprocessRun,
        session_output_path: Path,
    ):
        """ """
        run_name = pp_run._run_name
        output_path = session_output_path / run_name / "sorting"

        preprocessed_recording = pp_run._preprocessed

        super().__init__(
            run_name, session_output_path, output_path, preprocessed_recording
        )


class ConcatSortingRun(BaseSortingRun):
    def __init__(
        self, pp_runs_list: list[SeparatePreprocessRun], session_output_path: Path
    ):
        """
        TODO

        """
        run_name = "concat_run"
        output_path = session_output_path / run_name / "sorting"

        shank_keys = list(pp_runs_list[0]._preprocessed.keys())

        preprocessed_recording: dict = {key: [] for key in shank_keys}

        # Create a dict (key is "grouped" or shank number) of lists where the
        # lists contain all recordings to concatenate for that shank
        for run in pp_runs_list:
            for key in shank_keys:

                assert key in run._preprocessed, (
                    "Somehow grouped and per-shank recordings are mixed. "
                    "This should not happen."
                )
                preprocessed_recording[key].append(run._preprocessed[key])

        # Concatenate the lists for each shank into a single recording
        for key in shank_keys:
            preprocessed_recording[key] = si.concatenate_recordings(
                preprocessed_recording[key]
            )

        super().__init__(
            run_name, session_output_path, output_path, preprocessed_recording
        )
        self._orig_run_names = [run._run_name for run in pp_runs_list]
