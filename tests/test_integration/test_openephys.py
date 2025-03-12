import pytest
from unittest.mock import patch
from pathlib import Path
from spikewrap.process._loading import load_data 

def create_dummy_openephys_folder(base_dir):
    """Create a fake OpenEphys directory with a legacy structure.openephys file."""
    session_path = base_dir / "rawdata" / "sub-001_id-000001" / "ses-01_date-20230717"
    node_path = session_path / "Record Node 103"
    node_path.mkdir(parents=True, exist_ok=True)
    # Create `structure.openephys` to simulate a legacy dataset
    (node_path / "structure.openephys").touch()
    return session_path

def test_legacy_openephys_detection(tmp_path):
    """
    Ensure that load_data() properly detects `structure.openephys` and raises an error.
    If it does NOT raise an error, explicitly fail the test.
    """
   
    session_path = create_dummy_openephys_folder(tmp_path)
    
    # check for legacy format
    legacy_format = any(session_path.rglob("structure.openephys"))

    # Try calling `load_data()` and check if it raises an error
    try:
        # Make sure load_data gets to legacy check first
        load_data(session_path, "openephys", probe=None)
        # If no error was raised, fail the test
        pytest.fail("Function is NOT detecting `structure.openephys`. Test failed.")
    except RuntimeError as e:
        # If RuntimeError is raised, check if it's the expected error
        assert "Legacy OpenEphys format is not supported." in str(e)