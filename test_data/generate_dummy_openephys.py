import json
from pathlib import Path

import numpy as np

# Define paths
base_dir = Path("./dummy_openephys")
record_node = base_dir / "Record Node 103"
ephys_dir = record_node / "experiment1" / "recording1"

# Create required folders
ephys_dir.mkdir(parents=True, exist_ok=True)

# ✅ Write real dummy neural data to `continuous.dat`
num_samples = 10000  # Simulating 10,000 samples
num_channels = 4  # Simulating 4-channel recording
sampling_rate = 30000  # 30 kHz, typical for Neuropixels

# Generate random int16 data
dummy_data = np.random.randint(
    -32768, 32767, size=(num_samples, num_channels), dtype=np.int16
)
with open(ephys_dir / "continuous.dat", "wb") as f:
    f.write(dummy_data.tobytes())

# ✅ Ensure `structure.oebin` references a valid stream
oebin_content = {
    "GUI version": "0.6.0",
    "processors": [
        {
            "name": "Record Node 103",
            "id": 103,
            "recorded_data": "binary",
            "streams": [{"stream_name": "Neuropixels-AP", "stream_id": "0"}],
        }
    ],
    "format": "OpenEphysBinary",
}

# Write `structure.oebin`
with open(ephys_dir / "structure.oebin", "w") as f:
    json.dump(oebin_content, f, indent=4)

# ✅ Create minimal `settings.xml`
settings_content = """<?xml version="1.0"?>
<SETTINGS>
    <PROCESSOR name="Neuropixels-AP" id="0"/>
</SETTINGS>"""

with open(record_node / "settings.xml", "w") as f:
    f.write(settings_content)

print(f"✅ Fixed Dummy OpenEphys Binary dataset created at: {base_dir}")
