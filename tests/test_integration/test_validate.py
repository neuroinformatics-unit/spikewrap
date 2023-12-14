import os

import pytest

from spikewrap.pipeline import full_pipeline
from spikewrap.pipeline.load_data import load_data
from spikewrap.pipeline.postprocess import run_postprocess
from spikewrap.pipeline.preprocess import run_preprocessing
from spikewrap.pipeline.sort import run_sorting

from .base import BaseTest  # noqa

# TODO: OWN FUNCTION
DEFAULT_SORTER = "mountainsort5"
DEFAULT_FORMAT = "spikeinterface"


class TestValidate(BaseTest):
    @pytest.mark.parametrize("test_info", [DEFAULT_FORMAT], indirect=True)
    def test_validate_full_pipeline(self, test_info):
        """
        A very basic test to run all preprocessing and check now error occurs.
        Not all preprocessing steps are compatible, so other steps are tested in
        `test_preprocessing_options_2`.
        """
        self.remove_all_except_first_run_and_sessions(test_info)

        base_path = "not_a_real_base_path"
        with pytest.raises(AssertionError) as e:
            self.run_full_pipeline(base_path, *test_info[1:], DEFAULT_FORMAT)
        assert "Ensure there is a folder in base path called 'rawdata'" in str(e.value)

        base_path = None
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(base_path, *test_info[1:], DEFAULT_FORMAT)
        assert str(e.value) == "`base_path` must be a str or pathlib Path object."

        sub_name = "not a real sub name"
        with pytest.raises(AssertionError) as e:
            self.run_full_pipeline(test_info[0], sub_name, test_info[2], DEFAULT_FORMAT)
        assert (
            "Subject directory not found. not a real sub name is not a folder in"
            in str(e.value)
        )

        sub_name = None
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(test_info[0], sub_name, test_info[2], DEFAULT_FORMAT)
        assert str(e.value) == "`sub_name` must be a str (the subject name)."

        sessions_and_runs = None
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(*test_info[:-1], sessions_and_runs, DEFAULT_FORMAT)
        assert (
            str(e.value)
            == "`sessions_and_runs` must be a Dict where the keys are session names."
        )

        sessions_and_runs = {"not_a_real_ses_name": ["run_name"]}
        with pytest.raises(AssertionError) as e:
            self.run_full_pipeline(*test_info[:-1], sessions_and_runs, DEFAULT_FORMAT)
        assert "not_a_real_ses_name was not found at folder path" in str(e.value)

        sessions_and_runs = {"ses-001": None}
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(*test_info[:-1], sessions_and_runs, DEFAULT_FORMAT)

        assert (
            str(e.value)
            == "The runs within the session key for the `session_and_runs` "
            "Dict must be a list of run names or a single run name (str)."
        )

        sessions_and_runs = {"ses-001": "not_a_real_run_name"}
        with pytest.raises(AssertionError) as e:
            self.run_full_pipeline(*test_info[:-1], sessions_and_runs, DEFAULT_FORMAT)
        assert "The run folder not_a_real_run_name cannot be found at file path" in str(
            e.value
        )

        config_name = None
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(
                *test_info, config_name=config_name, data_format=DEFAULT_FORMAT
            )
        assert str(e.value) == "`config_name` must be a string."

        config_name = "not a real_config_name"
        with pytest.raises(AssertionError) as e:
            self.run_full_pipeline(
                *test_info, config_name=config_name, data_format=DEFAULT_FORMAT
            )
        assert (
            str(e.value)
            == "not a real_config_name is neither the name of an existing config or valid path to configuration file."
        )

        sorter = "not_a_real_sorter_name"
        with pytest.raises(ValueError) as e:
            self.run_full_pipeline(
                *test_info, sorter=sorter, data_format=DEFAULT_FORMAT
            )
        assert "`sorter` must be one of" in str(e.value)

        concat_ses = "False"
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(
                *test_info, concatenate_sessions=concat_ses, data_format=DEFAULT_FORMAT
            )
        assert str(e.value) == "`concat_sessions_for_sorting` must be a bool."

        concat_run = "False"
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(
                *test_info, concatenate_runs=concat_run, data_format=DEFAULT_FORMAT
            )
        assert str(e.value) == "`concat_runs_for_sorting` must be a bool."

        concat_ses = True  # TODO: delete from other one
        concat_run = False
        with pytest.raises(ValueError) as e:
            self.run_full_pipeline(
                *test_info,
                concatenate_sessions=concat_ses,
                concatenate_runs=concat_run,
                data_format=DEFAULT_FORMAT,
            )
        assert (
            str(e.value)
            == "`concatenate_runs` must be `True` if `concatenate_sessions` is `True`"
        )

        existing_preprocessed_data = "bad_name"
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(
                *test_info,
                existing_preprocessed_data=existing_preprocessed_data,
                data_format=DEFAULT_FORMAT,
            )
        assert (
            str(e.value)
            == "`existing_preprocessed_data` must be one of typing.Literal['overwrite', 'skip_if_exists', 'fail_if_exists']"
        )

        existing_sorting_output = "bad_name"
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(
                *test_info,
                existing_sorting_output=existing_sorting_output,
                data_format=DEFAULT_FORMAT,
            )
        assert (
            str(e.value)
            == "`existing_sorting_output` must be one of typing.Literal['overwrite', 'skip_if_exists', 'fail_if_exists']"
        )

        overwrite_postprocessing = "False"
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(
                *test_info,
                overwrite_postprocessing=overwrite_postprocessing,
                data_format=DEFAULT_FORMAT,
            )
        assert str(e.value) == "`overwrite_postprocessing` must be a bool."

        delete_intermediate_files = ("recording.dat", "bad_name")
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(
                *test_info,
                delete_intermediate_files=delete_intermediate_files,
                data_format=DEFAULT_FORMAT,
            )
        assert "`delete_intermediate_files` must be one of" in str(e.value)

        slurm_batch = None
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(
                *test_info, slurm_batch=slurm_batch, data_format=DEFAULT_FORMAT
            )  # TODO: check all naming. (why slurm BATCH?) just slurm would be better
        assert "`slurm_batch` must be `True` or a Dict of slurm settings." in str(
            e.value
        )

        slurm_batch = {"gpus_per_node_x": 1}
        with pytest.raises(ValueError) as e:
            self.run_full_pipeline(
                *test_info, slurm_batch=slurm_batch, data_format=DEFAULT_FORMAT
            )
        assert (
            "The `slurm batch key gpus_per_node_x is incorrect. "
            "Must be one of" in str(e.value)
        )

    @pytest.mark.parametrize("test_info", [DEFAULT_FORMAT], indirect=True)
    def test_validate_run_preprocess(self, test_info):
        self.remove_all_except_first_run_and_sessions(test_info)

        pp_steps, __, __ = full_pipeline.get_configs("test_preprocessing_1")

        with pytest.raises(TypeError) as e:
            run_preprocessing(
                preprocess_data=None,
                pp_steps=pp_steps,
                handle_existing_data="overwrite",
                preprocess_per_shank=False,
            )
        assert (
            str(e.value)
            == "`preprocess_data` must be a `PreprocessingData` class instance."
        )

        preprocess_data = load_data(*test_info[:3], data_format=DEFAULT_FORMAT)

        with pytest.raises(AssertionError) as e:
            run_preprocessing(
                preprocess_data=preprocess_data,
                pp_steps="bad_name",
                handle_existing_data="overwrite",
                preprocess_per_shank=False,
            )
        assert (
            str(e.value)
            == "bad_name is neither the name of an existing config or valid path to configuration file."
        )

        with pytest.raises(TypeError) as e:
            run_preprocessing(
                preprocess_data=preprocess_data,
                pp_steps=pp_steps,
                handle_existing_data="bad_name",
                preprocess_per_shank=False,
            )
        assert "`handle_existing_data` must be `False` or one of" in str(e.value)

        with pytest.raises(TypeError) as e:
            run_preprocessing(
                preprocess_data=preprocess_data,
                pp_steps=pp_steps,
                handle_existing_data="overwrite",
                slurm_batch="bad_type",
                preprocess_per_shank=False,
            )
        assert (
            str(e.value) == "`slurm_batch` must be `True` or a Dict of slurm settings."
        )

        with pytest.raises(TypeError) as e:
            run_preprocessing(
                preprocess_data=preprocess_data,
                pp_steps=pp_steps,
                handle_existing_data="overwrite",
                log="bad_type",
                preprocess_per_shank=False,
            )
            assert str(e.value) == "`log` must be `bool`."

    @pytest.mark.parametrize("test_info", [DEFAULT_FORMAT], indirect=True)
    def test_validate_run_sorting(self, test_info):
        """
        Sorting shares nearly all kwargs with `run_full_pipeline`, except for
        `sorter_options. If `sorter_options`- is successfully passed to
        `validate_arguments` and checked, then all other args should be properly
        checked and any fail would be caught in test_validate_full_pipeline.

        Choice of sorter here is arbitrary, just included so that it does not error
        before `sorter_options` is checked.
        """
        with pytest.raises(TypeError) as e:
            run_sorting(*test_info, sorter="mountainsort5", sorter_options="bad_name")
        assert (
            str(e.value)
            == "`sorter_options` must be a Dict of values to pass to the SpikeInterface sorting function."
        )

    def test_validate_run_postprocessing(self):
        """
        Any arguments shared with `run_full_pipeline are not tested here,
        see `test_validate_run_sorting()` docstring.
        """
        with pytest.raises(TypeError) as e:
            run_postprocess(sorting_path=None)
        assert str(e.value) == "`sorting_path` must be a str or pathlib Path object."

        with pytest.raises(FileNotFoundError) as e:
            run_postprocess(sorting_path="not_a_real_path")
        assert (
            str(e.value)
            == "No folder found at not_a_real_path. Postprocessing was not performed."
        )

        for bad_value in [None, "bad_name"]:
            with pytest.raises(BaseException) as e:
                run_postprocess(
                    sorting_path=os.getcwd(), existing_waveform_data=bad_value
                )
            assert "`existing_waveform_data` must be `False` or one of" in str(e.value)

        with pytest.raises(FileNotFoundError) as e:
            run_postprocess(
                sorting_path=os.getcwd(),
                existing_waveform_data="overwrite",
                waveform_options={},
            )
        assert (
            "The path is not to the 'sorting' folder. Output was not found at"
            in str(e.value)
        )

    @pytest.mark.parametrize("test_info", [DEFAULT_FORMAT], indirect=True)
    def test_validate_empty_sessions_and_runs(self, test_info):
        base_path, sub_name, sessions_and_runs = test_info

        sessions_and_runs = {}

        with pytest.raises(ValueError) as e:
            self.run_full_pipeline(
                base_path, sub_name, sessions_and_runs, DEFAULT_FORMAT
            )
        assert str(e.value) == "`sessions_and_runs` cannot be empty."

        sessions_and_runs = {"ses-001": []}

        with pytest.raises(ValueError) as e:
            self.run_full_pipeline(
                base_path, sub_name, sessions_and_runs, DEFAULT_FORMAT
            )
        assert str(e.value) == "`sessions_and_runs` cannot contain empty runs."

        sessions_and_runs = {
            "ses-001": ["run-001"],
            "ses-002": [],
        }
        with pytest.raises(ValueError) as e:
            self.run_full_pipeline(
                base_path, sub_name, sessions_and_runs, DEFAULT_FORMAT
            )

        assert str(e.value) == "`sessions_and_runs` cannot contain empty runs."

    @pytest.mark.parametrize("test_info", [DEFAULT_FORMAT], indirect=True)
    def test_run_all_with_concatenate_is_blocked(self, test_info):
        base_path, sub_name, sessions_and_runs = test_info
        sessions_and_runs["ses-001"] = ["all"]

        with pytest.raises(ValueError) as e:
            self.run_full_pipeline(
                base_path,
                sub_name,
                sessions_and_runs,
                DEFAULT_FORMAT,
                concatenate_runs=True,
            )

        assert (
            "Using the 'all' option for `sessions_and_runs` is currently "
            "not supported when concatenating runs for sorting." in str(e.value)
        )
