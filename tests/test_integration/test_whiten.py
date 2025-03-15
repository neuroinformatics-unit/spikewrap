from __future__ import annotations

import numpy as np
import pytest
from base import BaseTest
from spikeinterface.preprocessing import whiten

import spikewrap as sw


class TestWhiten(BaseTest):

    @pytest.fixture(scope="function")
    def session(self, tmp_path):
        session = sw.Session(
            subject_path=sw.get_example_data_path("spikeglx") / "rawdata" / "sub-001",
            session_name="ses-001",
            file_format="spikeglx",
            run_names=["run-001_g0_imec0", "run-002_g0_imec0"],
            output_path=tmp_path,
        )
        session.load_raw_data()
        return session

    def test_whitening_consistency(self, session):
        """
        Compare the output of applying SpikeInterface's whiten() directly on the raw recording
        with the output obtained after running Spikewrap’s whitening preprocessing.
        """
        # Apply whitening using preprocessing
        whitening_config = {
            "1": [
                "whiten",
                {
                    "apply_mean": True,
                    "mode": "global",
                    "dtype": "float32",
                    "int_scale": 1.0,
                    "chunk_size": 1000,
                    "num_chunks_per_segment": 150,
                    "seed": 42,
                    # Set to True if setup is computationally efficient, use regularize_kwargs with caution
                    "regularize": True,
                },
            ]
        }
        session.preprocess(whitening_config)
        spikewrap_whitened = session._pp_runs[0]

        underlying_recording = spikewrap_whitened._preprocessed["grouped"][
            "1-raw-whiten"
        ]
        sw_data = underlying_recording.get_traces()
        W_sw = np.array(
            spikewrap_whitened._preprocessed["grouped"]["1-raw-whiten"]._kwargs["W"]
        )

        # Apply whitening using SpikeInterface
        raw_recording = session._raw_runs[0]._raw["grouped"]
        whitening_kwargs = whitening_config["1"][1]
        si_whitened = whiten(raw_recording, **whitening_kwargs)
        si_data = si_whitened.get_traces()
        W_si = np.array(si_whitened._kwargs["W"])

        assert si_data.shape == sw_data.shape, "Shape mismatch"
        assert np.allclose(si_data, sw_data, atol=1e-5), "Data mismatch"
        assert np.allclose(
            W_si, W_sw, atol=1e-5
        ), f"Matrix diff: {np.linalg.norm(W_si - W_sw):.4f}"
