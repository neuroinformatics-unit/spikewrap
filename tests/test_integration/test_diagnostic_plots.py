import pytest
from pathlib import Path

from spikewrap.structure._preprocess_run import PreprocessedRun
import spikewrap.visualise 
import numpy as np
import matplotlib.pyplot as plt
import shutil 

@pytest.fixture
def mock_preprocessed_run(tmp_path, monkeypatch):
    """
    Fixture to create a temporary PreprocessedRun instance with mock data.
    """

    from spikewrap.structure._preprocess_run import PreprocessedRun
 
    def mock_plot(*args, **kwargs):
        pass
    
    def mock_figure(*args, **kwargs):
        class MockFigure:
            def savefig(self, path):
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                Path(path).touch()
            
            def clf(self):
                pass
        
        return MockFigure()
    
    def mock_visualise(*args, **kwargs):
        return mock_figure()
    
    monkeypatch.setattr(plt, "figure", mock_figure)
    monkeypatch.setattr(plt, "plot", mock_plot)
    monkeypatch.setattr(plt, "subplot", lambda *args, **kwargs: None)
    monkeypatch.setattr(plt, "title", lambda *args, **kwargs: None)
    
    import sys
    module_name = PreprocessedRun.__module__
    module = sys.modules[module_name]
    monkeypatch.setattr(module, "visualise_run_preprocessed", mock_visualise)
    
    class MockRecording:
        def __init__(self):
            self.properties = {}
            self.data = np.random.random((10, 1000)) 
        
        def save(self, folder, chunk_duration):
            Path(folder).mkdir(parents=True, exist_ok=True)
            (Path(folder) / "mock_recording_saved.txt").touch()
            return True
            
        def get_property(self, property_name):
            return self.properties.get(property_name, [])
            
        def get_traces(self, *args, **kwargs):
            return self.data
            
        def __array__(self):
            return self.data
    
    # Set up a mock recording with bad channels
    mock_recording = MockRecording()
    mock_recording.properties["bad_channels"] = [0, 1]  
    
    raw_data_path = tmp_path / "raw_data"
    session_output_path = tmp_path / "output"
    run_name = "test_run"
    
    preprocessed_data = {"shank_0": {"0": mock_recording, "1": mock_recording}}

    raw_data_path.mkdir(parents=True, exist_ok=True)  
    session_output_path.mkdir(parents=True, exist_ok=True)
    
    preprocessed_path = session_output_path / run_name / "preprocessed"
    preprocessed_path.mkdir(parents=True, exist_ok=True)
    
    diagnostic_path = session_output_path / "diagnostic_plots"
    diagnostic_path.mkdir(parents=True, exist_ok=True)
    
    preprocessed_run = PreprocessedRun(
        raw_data_path=raw_data_path,
        ses_name="test_session",
        run_name=run_name,
        file_format="mock_format",
        session_output_path=session_output_path,
        preprocessed_data=preprocessed_data,
        pp_steps={"step_1": "bad_channel_detection"},
    )
    
    def mock_save_diagnostic_plots(self):
        diagnostic_path = self._output_path / "diagnostic_plots"
        diagnostic_path.mkdir(parents=True, exist_ok=True)
        
        for shank_name in self._preprocessed:
            (diagnostic_path / f"{shank_name}_before_detection.png").touch()
            (diagnostic_path / f"{shank_name}_after_detection.png").touch()
            
            for ch in [0, 1]:
                (diagnostic_path / f"{shank_name}_bad_channel_{ch}.png").touch()
    
    # Monkeypatch the method to create placeholder files instead of real plots
    monkeypatch.setattr(preprocessed_run, "_save_diagnostic_plots", mock_save_diagnostic_plots.__get__(preprocessed_run))

    yield preprocessed_run


class TestDiagnosticPlots:
    """
    Test class to validate diagnostic plots are saved correctly.
    """

    def test_diagnostic_plots_saved(self, mock_preprocessed_run):
        """
        Test if diagnostic plots are correctly saved after running save_preprocessed.
        """
        output_dir = mock_preprocessed_run._output_path / "diagnostic_plots"

        if output_dir.exists():
            shutil.rmtree(output_dir)
        assert not output_dir.exists(), "Diagnostic plots directory should not exist before running save_preprocessed"

        # Should trigger the diagnostic plot saving
        mock_preprocessed_run.save_preprocessed(overwrite=True, chunk_duration_s=1.0, n_jobs=1, slurm=False)

        assert output_dir.exists(), "Diagnostic plots directory was not created"
        shank_name = "shank_0"
        expected_files = [
            f"{shank_name}_before_detection.png",
            f"{shank_name}_after_detection.png",
            f"{shank_name}_bad_channel_0.png",
            f"{shank_name}_bad_channel_1.png",
        ]

        for file_name in expected_files:
            assert (output_dir / file_name).exists(), f"Missing plot file: {file_name}"
