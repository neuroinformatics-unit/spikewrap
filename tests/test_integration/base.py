import os
import shutil
from pathlib import Path

import pytest

from spikewrap.pipeline import full_pipeline


class BaseTest:
    @pytest.fixture(scope="class")
    def base_path(self):
        script_path = Path(os.path.dirname(os.path.realpath(__file__)))
        data_path = script_path.parent
        base_path = data_path / "data"
        return base_path

    @pytest.fixture(scope="function")
    def test_info(self, base_path, request):
        """ """

        if not hasattr(request, "param") or request.param == "spikeinterface":
            output_path, test_info = self.generate_fast_spikeinterface_test_data_info(
                base_path
            )
            yield test_info

        elif request.param == "spikeglx":
            output_path, test_info = self.generate_kilosort_test_data_info(base_path)
            yield test_info

        elif request.param == "multi_segment":
            output_path, test_info = self.generate_mutli_segment_test_data_info(
                base_path
            )
            yield test_info

        else:
            raise ValueError("Indirect parameterization is not recognised.")

        if output_path.is_dir():
            shutil.rmtree(output_path)

    # TODO  centralise this!!!!!!!!! ------------------------------------------------------

    def generate_kilosort_test_data_info(self, base_path):
        """"""
        base_path = base_path / "steve_multi_run" / "time-short-multises"

        sub_name = "sub-1119617"

        sessions_and_runs = {
            "ses-001": ["run-001_1119617_LSE1_shank12_g0", "run-002_made_up_g0"],
            "ses-002": [
                "run-001_1119617_pretest1_shank12_g0",
                "run-002_1119617_LSE1_shank12_g0",
            ],
            "ses-003": [
                "run-001_1119617_posttest1_shank12_g0",
                "run-002_1119617_pretest1_shank12_g0",
            ],
        }

        output_path = base_path / "derivatives"

        if output_path.is_dir():
            shutil.rmtree(output_path)

        return output_path, [base_path, sub_name, sessions_and_runs]

    def generate_mutli_segment_test_data_info(self, base_path):
        """"""
        base_path = base_path / "toy_multi_segment"
        sub_name = "sub-001_type-mutliseg"
        sessions_and_runs = {
            "ses-001": ["ses-001_run-001", "ses-001_run-002"],
        }
        output_path = base_path / "derivatives"
        if output_path.is_dir():
            shutil.rmtree(output_path)

        return output_path, [base_path, sub_name, sessions_and_runs]

    def generate_fast_spikeinterface_test_data_info(self, base_path):
        """"""
        base_path = base_path / "small_toy_data"

        sub_name = "sub-001_type-test"

        sessions_and_runs = {
            "ses-001": ["ses-001_run-001", "ses-001_run-002"],
            "ses-002": ["ses-002_run-001", "ses-002_run-002"],
            "ses-003": ["ses-003_run-001", "ses-003_run-002"],
        }

        output_path = base_path / "derivatives"
        if output_path.is_dir():
            shutil.rmtree(output_path)

        return output_path, [base_path, sub_name, sessions_and_runs]

    def remove_all_except_first_run_and_sessions(self, test_info):
        sessions_and_runs = test_info[2]
        first_ses_key = list(sessions_and_runs.keys())[0]
        sessions_and_runs = {first_ses_key: [sessions_and_runs[first_ses_key][0]]}
        test_info[2] = sessions_and_runs

    @staticmethod
    def run_full_pipeline(
        base_path,
        sub_name,
        sessions_and_runs,
        data_format,
        config_name="test_default",
        sorter="kilosort2_5",
        concatenate_sessions=False,
        concatenate_runs=False,
        existing_preprocessed_data="fail_if_exists",
        existing_sorting_output="fail_if_exists",
        overwrite_postprocessing=False,
        delete_intermediate_files=(),
        slurm_batch=False,
    ):
        return full_pipeline.run_full_pipeline(
            base_path,
            sub_name,
            sessions_and_runs,
            data_format=data_format,
            config_name=config_name,
            sorter=sorter,
            concat_sessions_for_sorting=concatenate_sessions,
            concat_runs_for_sorting=concatenate_runs,
            existing_preprocessed_data=existing_preprocessed_data,
            existing_sorting_output=existing_sorting_output,
            overwrite_postprocessing=overwrite_postprocessing,
            delete_intermediate_files=delete_intermediate_files,
            slurm_batch=slurm_batch,
        )

    def check_correct_folders_exist(
        self, test_info, concatenate_sessions, concatenate_runs, sorter="kilosort2_5"
    ):
        sub_path = test_info[0] / "derivatives" / "spikewrap" / test_info[1]
        sessions_and_runs = test_info[2]

        derivative_sessions = list(sub_path.glob("*"))

        # Logs are not saved in normal test environment because logger
        # handlers propagate from root that pytest attaches handlers too.
        # removing the handlers from spikewrap loggers specifically
        # does not help, nor does querying .handlers[:] in spikewrap itself.
        derivative_ses_names = sorted([path_.name for path_ in derivative_sessions])
        if "logs" in derivative_ses_names:
            derivative_ses_names.pop(derivative_ses_names.index("logs"))

        # Here, just testing if the paths exists
        if concatenate_sessions is False:
            assert list(sessions_and_runs.keys()) == derivative_ses_names

        else:
            assert "sorting-concat" in derivative_ses_names.pop(-1)
            assert list(sessions_and_runs.keys()) == derivative_ses_names

        if concatenate_sessions is True:
            for ses_name in sessions_and_runs.keys():
                ses_path = sub_path / ses_name / "ephys"

                run_level_sorting = list(ses_path.glob(f"*/*/{sorter}"))
                assert run_level_sorting == []
        else:
            for ses_name in sessions_and_runs.keys():
                for run_name in sessions_and_runs[ses_name]:
                    run_path = sub_path / ses_name / "ephys" / run_name
                    run_level_sorting = list(run_path.glob(sorter))

                    if concatenate_runs:
                        assert run_level_sorting == []
                    else:
                        assert len(run_level_sorting) == 1

                ses_path = sub_path / ses_name / "ephys"

                concat_all_run_names = "".join(
                    path_.name for path_ in ses_path.glob("*")
                )  # TODO: Hacky
                if concatenate_runs:
                    assert "sorting-concat" in concat_all_run_names
                else:
                    assert "sorting-concat" not in concat_all_run_names
