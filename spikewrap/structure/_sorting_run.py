import shutil
from pathlib import Path
from typing import Literal

import spikeinterface
import spikeinterface.full as si
from spikeinterface.sorters import run_sorter
from spikeinterface.sorters.runsorter import SORTER_DOCKER_MAP

from spikewrap.structure._preprocess_run import PreprocessedRun
from spikewrap.utils import _checks, _managing_sorters, _slurm


class BaseSortingRun:
    """
    Class to manage the sorting of preprocessed data. Writes the sorting output
    to disk using SpikeInterface's `run_sorter`.

    Notes
    -----
    This class does not mutate its inputs. It holds the preprocessed recording
    object, and will copy and split by-shank on the fly if sorting per-shank.
    """

    def __init__(
        self, run_name, session_output_path, output_path, preprocessed_recording
    ):
        self._run_name = run_name
        self._session_output_path = session_output_path
        self._output_path = output_path
        self._preprocessed_recording = preprocessed_recording

    def sort(
        self,
        sorting_configs: dict,
        run_sorter_method: str,
        per_shank: bool,
        overwrite: bool,
        slurm: bool | dict,
    ):
        """
                Run sorting using SpikeInterface's `run_sorter`.

                Parameters
                ----------
                sorting_configs
                    A dictionary containing the sorting options, with key is the
                    sorter name and value a dictionary of kwargs to pass to the sorter.

                See `session.sort()` for other parameters.

                Notes
                -----
                This function will coordinate deleting existing outputs if they
                exist and `overwrite` is true. `_configure_run_sorter_method` will
                perform many checks on docker / singularity image as well as call
                SpikeInterface functions to set the matlab path if required.
        `"""
        if slurm:
            self._sort_slurm(
                sorting_configs, run_sorter_method, per_shank, overwrite, slurm
            )
            return

        assert len(sorting_configs) == 1, "Only one sorter supported."
        ((sorter, sorter_kwargs),) = sorting_configs.items()

        run_docker, run_singularity = self._configure_run_sorter_method(
            sorter,
            run_sorter_method,
        )

        self.handle_overwrite_output_path(overwrite)

        if per_shank:
            preprocessed_recording = self.split_per_shank()
        else:
            preprocessed_recording = self._preprocessed_recording

        for shank_id, recording in preprocessed_recording.items():

            out_path = self._output_path
            if shank_id != "grouped":
                out_path = out_path / shank_id

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

    def handle_overwrite_output_path(self, overwrite):
        """
        Handle overwriting of the output `sorting` folder.
        """
        if self._output_path.is_dir():
            if overwrite:
                shutil.rmtree(self._output_path)
            else:
                raise RuntimeError("need `overwrite`.")

    def _sort_slurm(
        self,
        sorting_configs: dict,
        run_sorter_method: str | Path,
        per_shank: bool,
        overwrite: bool,
        slurm: bool | dict,
    ):
        """
        See `save_preprocessed_slurm` for details on this mechanism. Briefly,
        we need to re-call the sorting function in the slurm environment.
        """
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

    def split_per_shank(self):
        """
        Return the preprocessed recording split by shank (if it
        currently not split by shank, i.e. the shank id is "grouped").
        """
        if "grouped" not in self._preprocessed_recording:
            raise RuntimeError(
                "`per_shank=True` but the recording was already split per shank for preprocessing."
                "Set to `False`."
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

        preprocessed_recording = {
            f"shank_{key}": value for key, value in split_recording.items()
        }
        return preprocessed_recording

    def get_singularity_image_path(self, sorter: str) -> Path:
        """
        Get the path to where the singularity image is stored (at the
        same level as "rawdata" and "derivatives" as these are shared
        across the project).
        """
        spikeinterface_version = spikeinterface.__version__

        sorter_path = (
            self._session_output_path.parent.parent.parent  # TODO: hacky? :(
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
        """
         This function configures how the sorter is run. There are four
         possible options:

         1) "local". This assumes the sorter is written in python and can be
            run in the current python environment. This includes sorters such
            as kilosort4 and mountainsort.

         2) For matlab-based sorters, spikeinterface can take a path to the repository
            and run the sorting from there. To do this, we need to call the appropriate
            `set_<sorter>_path` function.

        3) We can run on docker or singularity. For docker, the docker desktop client
           manages image downloading. For singularity, we need to do this ourselves.
           By default, spikeinterface will download the sorter to the working directory
           when the script is called. It is better to download it manually and
           move it to a central place so it can be reused.

         TODO
         ----
         Tidy this up!
        """
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


class SeparateSortingRun(BaseSortingRun):
    def __init__(
        self,
        pp_run: PreprocessedRun,
        session_output_path: Path,
    ):
        """
        A class to handle sorting of an individual preprocessed run.
        """
        run_name = pp_run._run_name
        output_path = session_output_path / run_name / "sorting"

        preprocessed_recording = pp_run._preprocessed

        super().__init__(
            run_name, session_output_path, output_path, preprocessed_recording
        )


class ConcatSortingRun(BaseSortingRun):
    def __init__(self, pp_runs_list: list[PreprocessedRun], session_output_path: Path):
        """
        A class to handle the sorting of a concatenation of a set of separate preprocess runs.

        This class:
            1) concatenates the passed recordings into a single recording.
            2) sets the `_orig_run_names` variable containing the concatenates
               run names (in concatenation order).
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
