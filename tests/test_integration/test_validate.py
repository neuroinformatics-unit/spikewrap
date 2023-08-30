import os

import pytest

from spikewrap.pipeline import full_pipeline
from spikewrap.pipeline.load_data import load_data
from spikewrap.pipeline.postprocess import run_postprocess
from spikewrap.pipeline.preprocess import run_preprocess
from spikewrap.pipeline.sort import run_sorting

from .base import BaseTest

DEFAULT_SORTER = "mountainsort5"


class TestValidate(BaseTest):
    def test_validate_full_pipeline(self, test_info):
        """
        A very basic test to run all preprocessing and check now error occurs.
        Not all preprocessing steps are compatible, so other steps are tested in
        `test_preprocessing_options_2`.
        """
        self.remove_all_except_first_run_and_sessions(test_info)

        base_path = "not_a_real_base_path"
        with pytest.raises(AssertionError) as e:
            self.run_full_pipeline(base_path, *test_info[1:])
        assert "Ensure there is a folder in base path called 'rawdata'" in str(e.value)

        base_path = None
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(base_path, *test_info[1:])
        assert str(e.value) == "`base_path` must be a str or pathlib Path object."

        sub_name = "not a real sub name"
        with pytest.raises(AssertionError) as e:
            self.run_full_pipeline(test_info[0], sub_name, test_info[2])
        assert (
            "Subject directory not found. not a real sub name is not a folder in"
            in str(e.value)
        )

        sub_name = None
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(test_info[0], sub_name, test_info[2])
        assert str(e.value) == "`sub_name` must be a str (the subject name)."

        sessions_and_runs = None
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(*test_info[:-1], sessions_and_runs)
        assert (
            str(e.value)
            == "`sessions_and_runs` must be a Dict where the keys are session names."
        )

        sessions_and_runs = {"not_a_real_ses_name": ["run_name"]}
        with pytest.raises(AssertionError) as e:
            self.run_full_pipeline(*test_info[:-1], sessions_and_runs)
        assert "not_a_real_ses_name was not found at folder path" in str(e.value)

        sessions_and_runs = {"ses-001": None}
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(*test_info[:-1], sessions_and_runs)
        assert (
            str(e.value)
            == "The runs within the session key for the `session_and_runs` Dict must be a list of run names or a single run name (str)."
        )

        sessions_and_runs = {"ses-001": "not_a_real_run_name"}
        with pytest.raises(AssertionError) as e:
            self.run_full_pipeline(*test_info[:-1], sessions_and_runs)
        assert "The run folder not_a_real_run_name cannot be found at file path" in str(
            e.value
        )

        config_name = None
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(*test_info, config_name=config_name)
        assert str(e.value) == "`config_name` must be a string."

        config_name = "not a real_config_name"
        with pytest.raises(AssertionError) as e:
            self.run_full_pipeline(*test_info, config_name=config_name)
        assert (
            str(e.value)
            == "not a real_config_name is neither the name of an existing config or valid path to configuration file."
        )

        sorter = "not_a_real_sorter_name"
        with pytest.raises(ValueError) as e:
            self.run_full_pipeline(*test_info, sorter=sorter)
        assert "`sorter` must be one of" in str(e.value)

        concat_ses = "False"
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(*test_info, concatenate_sessions=concat_ses)
        assert str(e.value) == "`concat_sessions_for_sorting` must be a bool."

        concat_run = "False"
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(*test_info, concatenate_runs=concat_run)
        assert str(e.value) == "`concat_runs_for_sorting` must be a bool."

        concat_ses = True  # TODO: delete from other one
        concat_run = False
        with pytest.raises(ValueError) as e:
            self.run_full_pipeline(
                *test_info, concatenate_sessions=concat_ses, concatenate_runs=concat_run
            )
        assert (
            str(e.value)
            == "`concatenate_runs` must be `True` if `concatenate_sessions` is `True`"
        )

        existing_preprocessed_data = "bad_name"
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(
                *test_info, existing_preprocessed_data=existing_preprocessed_data
            )
        assert (
            str(e.value)
            == "`existing_preprocessed_data` must be one of typing.Literal['overwrite', 'skip_if_exists', 'fail_if_exists']"
        )

        existing_sorting_output = "bad_name"
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(
                *test_info, existing_sorting_output=existing_sorting_output
            )
        assert (
            str(e.value)
            == "`existing_sorting_output` must be one of typing.Literal['overwrite', 'skip_if_exists', 'fail_if_exists']"
        )

        overwrite_postprocessing = "False"
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(
                *test_info, overwrite_postprocessing=overwrite_postprocessing
            )
        assert str(e.value) == "`overwrite_postprocessing` must be a bool."

        delete_intermediate_files = ("recording.dat", "bad_name")
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(
                *test_info, delete_intermediate_files=delete_intermediate_files
            )
        assert "`delete_intermediate_files` must be one of" in str(e.value)

        slurm_batch = None
        with pytest.raises(TypeError) as e:
            self.run_full_pipeline(
                *test_info, slurm_batch=slurm_batch
            )  # TODO: check all naming. (why slurm BATCH?) just slurm would be better
        assert "`slurm_batch` must be `True` or a Dict of slurm settings." in str(
            e.value
        )

        slurm_batch = {"gpus_per_node_x": 1}
        with pytest.raises(ValueError) as e:
            self.run_full_pipeline(*test_info, slurm_batch=slurm_batch)
        assert (
            "The `slurm batch key gpus_per_node_x is incorrect. "
            "Must be one of" in str(e.value)
        )

    def test_validate_run_preprocess(self, test_info):
        self.remove_all_except_first_run_and_sessions(test_info)

        pp_steps, __, __ = full_pipeline.get_configs("test_preprocessing_1")

        with pytest.raises(TypeError) as e:
            run_preprocess(
                preprocess_data=None, pp_steps=pp_steps, save_to_file="overwrite"
            )
        assert (
            str(e.value)
            == "`preprocess_data` must be a `PreprocessingData` class instance."
        )

        preprocess_data = load_data(*test_info[:3])

        with pytest.raises(AssertionError) as e:
            run_preprocess(
                preprocess_data=preprocess_data,
                pp_steps="bad_name",
                save_to_file="overwrite",
            )
        assert (
            str(e.value)
            == "bad_name is neither the name of an existing config or valid path to configuration file."
        )

        with pytest.raises(TypeError) as e:
            run_preprocess(
                preprocess_data=preprocess_data,
                pp_steps=pp_steps,
                save_to_file="bad_name",
            )
        assert "`save_to_file` must be `False` or one of" in str(e.value)

        with pytest.raises(TypeError) as e:
            run_preprocess(
                preprocess_data=preprocess_data,
                pp_steps=pp_steps,
                save_to_file="overwrite",
                slurm_batch="bad_type",
            )
        assert (
            str(e.value) == "`slurm_batch` must be `True` or a Dict of slurm settings."
        )

        with pytest.raises(TypeError) as e:
            run_preprocess(
                preprocess_data=preprocess_data,
                pp_steps=pp_steps,
                save_to_file="overwrite",
                log="bad_type",
            )
            assert str(e.value) == "`log` must be `bool`."

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

    def test_validate_run_postprocessing(self, test_info):
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
