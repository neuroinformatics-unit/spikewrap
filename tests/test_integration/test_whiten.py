from __future__ import annotations

import numpy as np
import pytest
from base import BaseTest
from spikeinterface.preprocessing import whiten

import spikewrap as sw


class TestWhiten(BaseTest):

    @pytest.fixture(scope="function")
    def session(self, tmp_path):
        """
        Sets up a session fixture to load raw spike data.
        This fixture ensures that each test runs in isolation with temporary data.
        """
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
        Compare the output of applying SpikeInterface's `whiten()` directly on the raw recording
        with the output obtained after running Spikewrap’s whitening preprocessing.

        This ensures that Spikewrap's implementation of whitening is consistent with the
        standard whitening approach from SpikeInterface.
        """

        # Whitening configuration used for preprocessing
        whitening_config = {
            "1": [
                "whiten",
                {
                    "apply_mean": True,  # Subtract mean before whitening
                    "mode": "global",  # Apply whitening across all channels
                    "dtype": "float32",  # Ensure floating-point precision
                    "int_scale": 1.0,  # Internal scaling factor
                    "chunk_size": 1000,  # Process data in chunks of 500 samples
                    "num_chunks_per_segment": 150,  # Number of chunks per segment
                    "seed": 42,  # Seed
                    "regularize": True,  # Apply regularisation
                },
            ]
        }

        # Apply whitening using Spikewrap preprocessing
        session.preprocess(whitening_config)
        spikewrap_whitened = session._pp_runs[0]

        # Extract whitened data and transformation matrix from Spikewrap
        underlying_recording = spikewrap_whitened._preprocessed["grouped"][
            "1-raw-whiten"
        ]
        sw_data = underlying_recording.get_traces()  # Get the whitened traces
        W_sw = np.array(
            spikewrap_whitened._preprocessed["grouped"]["1-raw-whiten"]._kwargs["W"]
        )  # Whitening matrix

        # Apply whitening using SpikeInterface directly on raw recording
        raw_recording = session._raw_runs[0]._raw["grouped"]
        whitening_kwargs = whitening_config["1"][1]
        si_whitened = whiten(
            raw_recording, **whitening_kwargs
        )  # Apply SpikeInterface whitening
        si_data = si_whitened.get_traces()  # Get whitened traces
        W_si = np.array(si_whitened._kwargs["W"])  # Extract whitening matrix

        # Verify consistency between Spikewrap and SpikeInterface results
        assert (
            si_data.shape == sw_data.shape
        ), "Shape mismatch between SpikeInterface and Spikewrap outputs"
        assert np.allclose(
            si_data, sw_data, atol=1e-5
        ), "Data mismatch: whitened traces differ"
        assert np.allclose(
            W_si, W_sw, atol=1e-5
        ), f"Whitening matrix mismatch: difference norm {np.linalg.norm(W_si - W_sw):.4f}"
