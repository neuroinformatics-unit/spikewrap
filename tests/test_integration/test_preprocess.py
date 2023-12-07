import copy

import numpy as np
import pytest
import spikeinterface.preprocessing as spre
from spikeinterface import (
    load_extractor,
    order_channels_by_depth,
)

from spikewrap.pipeline.load_data import load_data
from spikewrap.pipeline.preprocess import run_preprocessing

from .base import BaseTest  # noqa


class TestPreprocessingPipeline(BaseTest):
    def test_smoke_preprocess_per_shank(self, test_info):
        """ """
        self.remove_all_except_first_run_and_sessions(test_info)

        preprocess_data = load_data(*test_info[:3])

        pp_steps = {"1": ("highpass_spatial_filter", {})}

        with pytest.raises(AssertionError) as e:
            run_preprocessing(
                preprocess_data,
                pp_steps,
                handle_existing_data="fail_if_exists",
                preprocess_per_shank=False,
            )

        assert "The recording contains multiple groups!" in str(e.value)

        run_preprocessing(
            preprocess_data,
            pp_steps,
            handle_existing_data="fail_if_exists",
            preprocess_per_shank=True,
        )

    def test_preprocess_per_shank_against_manually(self, test_info):
        """
        TODO: needs to be split up into multple tests. Currently it is
        slow so not worth it.
        # zscore is quite slow with aggregate channels.
        # TODO: need to test all runs?! no...
        # TODO: all tests will now fail due to chunk size change...
        # if chunk size is too small they will fail in future...

        # Run preprocessing per-shank through spikewrap with the preprocessing
        # steps defined in `pp_steps`.
        """
        self.remove_all_except_first_run_and_sessions(test_info)

        preprocess_data = load_data(*test_info[:3])

        # zscore is quite slow with aggregate channels.
        pp_steps = {
            "1": ("phase_shift", {}),
            "2": ("bandpass_filter", {}),
            "3": ("common_reference", {}),
            "4": ("scale", {"gain": 2}),
            "5": ("highpass_spatial_filter", {}),
        }

        run_preprocessing(
            preprocess_data,
            pp_steps,
            handle_existing_data="overwrite",
            preprocess_per_shank=True,
        )

        # Now, we take the base recording and re-apply all preprocessing steps
        # manually in SI, which we are sure is correct. This is done by
        # recursively reapplying the preprocessing steps to `test_recording`.
        base_recording = preprocess_data["ses-001"]["run-001_1119617_LSE1_shank12_g0"][
            "0-raw"
        ]

        split_recording = base_recording.split_by("group")
        not_split_recording = copy.deepcopy(base_recording)

        test_recording = split_recording

        # fmt: off
        for pp_info, pp_dict_name, same_when_pp_together in zip(
            [[spre.phase_shift, {}], [spre.bandpass_filter, {}],          [spre.common_reference, {}],                          [spre.scale, {"gain": 2}],                                   [spre.highpass_spatial_filter, {}]],
            ["1-raw-phase_shift",    "2-raw-phase_shift-bandpass_filter", "3-raw-phase_shift-bandpass_filter-common_reference", "4-raw-phase_shift-bandpass_filter-common_reference-scale", "5-raw-phase_shift-bandpass_filter-common_reference-scale-highpass_spatial_filter"],
            [True,                    True,                                False,                                                False,                                                      False]
        ):
            # Apply the preprocessing directly to each shank
            pp_func, pp_kwargs = pp_info
            test_recording = {key: pp_func(recording, **pp_kwargs) for key, recording in test_recording.items()}

            # Get the preprocessed data from spikewrap
            spikewrap_preprocessed_recording = preprocess_data["ses-001"]["run-001_1119617_LSE1_shank12_g0"][pp_dict_name]

            # Check these match exactly
            assert np.array_equal(self.get_concatenated_data_from_split_recording(test_recording),
                                  spikewrap_preprocessed_recording.get_traces())

            # Check a version that is preprocessed without being split is not
            # the same as the split version.
            # Note cannot perform `highpass_spatial_filter` globally.
            if pp_func != spre.highpass_spatial_filter:
                not_split_recording = pp_func(not_split_recording)
                reorder = order_channels_by_depth(spikewrap_preprocessed_recording)[0]
                assert np.array_equal(not_split_recording.get_traces(),  spikewrap_preprocessed_recording.get_traces()[:, reorder]) is same_when_pp_together
        # fmt: on

        # Do a final quick check that the saved data matches the final
        # preprocessing step.
        output_path = (
            test_info[0]
            / "derivatives"
            / "spikewrap"
            / test_info[1]
            / "ses-001"
            / "ephys"
            / test_info[2]["ses-001"][0]
        )  # hacky...
        saved_data = load_extractor(output_path / "preprocessing" / "si_recording")

        stored_data = preprocess_data["ses-001"]["run-001_1119617_LSE1_shank12_g0"][
            "5-raw-phase_shift-bandpass_filter-common_reference-scale-highpass_spatial_filter"
        ]
        assert np.allclose(
            saved_data.get_traces(), stored_data.get_traces(), rtol=1, atol=1e-8
        )

    def get_concatenated_data_from_split_recording(self, split_recording):
        """ """
        all_data_list = []
        for rec in split_recording.values():
            all_data_list.append(rec.get_traces())

        all_data = np.hstack(all_data_list)
        return all_data

    def test_confidence_check_details(self, test_info):
        """ """
        self.remove_all_except_first_run_and_sessions(test_info)

        preprocess_data = load_data(*test_info[:3])

        # zscore is quite slow with aggregate channels.
        pp_steps = {"1": ("common_reference", {"operator": "average"})}
        run_preprocessing(
            preprocess_data,
            pp_steps,
            handle_existing_data="overwrite",
            preprocess_per_shank=True,
        )

        base_recording = preprocess_data["ses-001"]["run-001_1119617_LSE1_shank12_g0"][
            "0-raw"
        ]  # TODO:@ this shouldnbt be hard coded
        test_recording = base_recording.split_by("group")

        spikewrap_recording = preprocess_data["ses-001"][
            "run-001_1119617_LSE1_shank12_g0"
        ]["1-raw-common_reference"]
        spikewrap_data = spikewrap_recording.get_traces()

        groups = spikewrap_recording.get_property("group")

        all_channels_means = np.mean(base_recording.get_traces(), axis=1)

        for shank_idx, shank_rec in enumerate(test_recording.values()):
            test_data = shank_rec.get_traces()
            means = np.mean(test_data, axis=1)
            test_demeaned = test_data - means[:, np.newaxis]

            demeaned_wrong_mean = test_data - all_channels_means[:, np.newaxis]

            assert np.allclose(
                test_demeaned,
                spikewrap_data[:, np.where(groups == shank_idx)[0]],
                rtol=0,
                atol=1e-10,
            )
            assert not np.array_equal(
                demeaned_wrong_mean, spikewrap_data[:, np.where(groups == shank_idx)]
            )
