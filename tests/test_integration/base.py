from __future__ import annotations

from pathlib import Path

import numpy as np
import probeinterface as pi


class BaseTest:

    def get_pp_steps(self):
        return {"1": ["bandpass_filter", {"freq_min": 300, "freq_max": 6000}]}

    def get_no_probe_sub_path(self):
        return (
            Path(__file__).parent.parent
            / "test_data"
            / "no_probe"
            / "rawdata"
            / "sub-001"
        )

    def get_mock_probe(self):
        """
        Get an arbitrary probe to use on the test recording (16 channels).
        """
        mock_probe = pi.get_probe("imec", "NP2014")
        mock_probe = mock_probe.get_slice(np.arange(16))
        return mock_probe
