from pathlib import Path

# TODO: this might not work after normal pip install...
def get_example_data_path():  # TODO: test this!
    return Path(__file__).parents[1] / "examples" / "example_tiny_data"
