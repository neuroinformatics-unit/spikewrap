from __future__ import annotations

import pytest

from spikewrap.process._loading import load_data


class TestLegacyOpenEphysLoading:
    @pytest.fixture
    def legacy_openephys_session_path(self, tmp_path):
        """
        Create a fake OpenEphys directory with a legacy `structure.openephys` file,
        then return the session path.
        """
        session_path = (
            tmp_path / "rawdata" / "sub-001_id-000001" / "ses-01_date-20230717"
        )
        node_path = session_path / "Record Node 103"
        node_path.mkdir(parents=True, exist_ok=True)
        # Create `structure.openephys` to detect legacy format
        (node_path / "structure.openephys").touch()
        return session_path

    def test_legacy_openephys_detection(self, legacy_openephys_session_path):
        """
        Ensure that load_data() properly detects `structure.openephys` and raises an error.
        """
        with pytest.raises(RuntimeError) as e:
            load_data(legacy_openephys_session_path, "openephys", probe=None)
        assert "Legacy OpenEphys format is not supported." in str(e.value)
