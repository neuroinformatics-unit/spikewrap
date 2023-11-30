from pathlib import Path
from typing import Dict, List, Optional

import typeguard
from typeguard import CollectionCheckStrategy

from ..configs.backend.hpc import default_slurm_options
from ..data_classes.preprocessing import PreprocessingData
from ..utils import utils
from ..utils.custom_types import DeleteIntermediate, HandleExisting


def check_function_arguments(arguments):
    """
    A quick and dirty implementation of argument validation that is due for
    further development. Initially, most checks were performed at the lowest
    level with asserts. However, it will be better to perform as many checks
    as possible up front. Otherwise, the full pipeline could stop in the middle
    due to a bad argument combination (e.g. after preprocessing, before sorting).

    More and more the low-level asserts should be changed to raise exceptions and
    moved here. In some cases, this will not be possible (e.g. all path validation
    because the paths are generated in preprocessing / sorting classes).

    Further, using a validator package will be neater and reduce boilerplate.
    """
    for arg_name, arg_value in arguments.items():
        # Shared / Run Full Pipeline ---------------------------------------------------

        if arg_name == "base_path":
            if not (typecheck(arg_value, Path) or typecheck(arg_value, str)):
                raise TypeError("`base_path` must be a str or pathlib Path object.")

        elif arg_name == "sub_name":
            if not typecheck(arg_value, str):
                raise TypeError("`sub_name` must be a str (the subject name).")

        elif arg_name == "sessions_and_runs":
            if not typecheck(arg_value, Dict):
                raise TypeError(
                    "`sessions_and_runs` must be a Dict where the keys are session names."
                )

            if len(arg_value) == 0:
                raise ValueError("`sessions_and_runs` cannot be empty.")

            for run_names in arg_value.values():
                if len(run_names) == 0:
                    raise ValueError("`sessions_and_runs` cannot contain empty runs.")

                if not (typecheck(run_names, List) or typecheck(run_names, str)):
                    raise TypeError(
                        "The runs within the session key for the "
                        "`session_and_runs` Dict must be a list of run names "
                        "or a single run name (str)."
                    )

        elif arg_name == "sorter":
            if not typecheck(arg_value, str):
                raise TypeError("`sorter` must be a str indicating the sorter to use.")

            supported_sorters = utils.canonical_settings("supported_sorters")

            if arg_value not in supported_sorters:
                raise ValueError(f"`sorter` must be one of {supported_sorters}")

        elif arg_name == "config_name":
            if not typecheck(arg_value, str):
                raise TypeError("`config_name` must be a string.")

        elif arg_name in ["concat_sessions_for_sorting", "concatenate_sessions"]:
            if not typecheck(arg_value, bool):
                raise TypeError(f"`{arg_name}` must be a bool.")

        elif arg_name in ["concat_runs_for_sorting", "concatenate_runs"]:
            if not typecheck(arg_value, bool):
                raise TypeError(f"`{arg_name}` must be a bool.")

        elif arg_name == "existing_preprocessed_data":
            if not typecheck(arg_value, HandleExisting):
                raise TypeError(
                    f"`existing_preprocessed_data` must be one of {HandleExisting}"
                )

        elif arg_name == "existing_sorting_output":
            if not typecheck(arg_value, HandleExisting):
                raise TypeError(
                    f"`existing_sorting_output` must be one of {HandleExisting}"
                )

        elif arg_name == "overwrite_postprocessing":
            if not typecheck(arg_value, bool):
                raise TypeError("`overwrite_postprocessing` must be a bool.")

        elif arg_name == "delete_intermediate_files":
            if not typecheck(
                arg_value,
                DeleteIntermediate,
                collection_check_strategy=CollectionCheckStrategy.ALL_ITEMS,
            ):
                raise TypeError(
                    f"`delete_intermediate_files` must be one of {DeleteIntermediate}"
                )

        elif arg_name == "slurm_batch":
            if not (typecheck(arg_value, bool) or typecheck(arg_value, Dict)):
                raise TypeError(
                    "`slurm_batch` must be `True` or a Dict of slurm settings."
                )

            if typecheck(arg_value, Dict):
                for key in arg_value.keys():
                    if key not in default_slurm_options():
                        raise ValueError(
                            f"The `slurm batch key {key} is incorrect. "
                            f"Must be one of {default_slurm_options()}"
                        )

        # Preprocessing ----------------------------------------------------------------

        elif arg_name == "preprocess_data":
            if not typecheck(arg_value, PreprocessingData):
                raise TypeError(
                    "`preprocess_data` must be a `PreprocessingData` class instance."
                )

        elif arg_name == "pp_steps":
            if not (typecheck(arg_value, Dict) or typecheck(arg_value, str)):
                raise TypeError(
                    "`pp_steps` must be a Dict of preprocessing options or a "
                    "string that matches a config yaml in the configs folder."
                )

        elif arg_name == "handle_existing_data":
            if not (arg_value is False or typecheck(arg_value, HandleExisting)):
                raise TypeError(
                    f"`handle_existing_data` must be `False` or one of {HandleExisting}."
                )

        elif arg_name == "log":
            if not typecheck(arg_value, bool):
                raise TypeError("`log` must be `bool`.")

        # Sorting ----------------------------------------------------------------------

        elif arg_name == "sorter_options":
            if not typecheck(arg_value, Optional[Dict]):
                raise TypeError(
                    "`sorter_options` must be a Dict of values to pass to "
                    "the SpikeInterface sorting function."
                )

        # Postprocessing ---------------------------------------------------------------

        elif arg_name == "sorting_path":
            if not (typecheck(arg_value, Path) or typecheck(arg_value, str)):
                raise TypeError("`sorting_path` must be a str or pathlib Path object.")

        elif arg_name == "overwrite_postprocessing":
            if not typecheck(arg_value, bool):
                raise TypeError("`overwrite_postprocessing` must be a bool.")

        elif arg_name == "existing_waveform_data":
            if not (arg_value is False or typecheck(arg_value, HandleExisting)):
                raise TypeError(
                    f"`existing_waveform_data` must be `False` or one of {HandleExisting}."
                )

        elif arg_name == "waveform_options":
            if not typecheck(arg_value, Optional[Dict]):
                raise TypeError(
                    "`sorter_options` must be a Dict of values to pass to "
                    "the SpikeInterface's `WaveformExtractor`."
                )


def typecheck(object, type, **kwargs):
    """
    Use typecheck to perform isinstance-like type
    check subscripted generics.
    """
    try:
        typeguard.check_type(object, type, **kwargs)
        return True
    except typeguard.TypeCheckError:
        return False
