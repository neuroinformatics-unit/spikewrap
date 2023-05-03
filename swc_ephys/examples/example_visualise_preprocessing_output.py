from swc_ephys.pipeline.visualise import visualise_preprocessing_output

preprocessing_path = (
    "/home/joe/data/steve_multi_run/derivatives/1119617/all/preprocessed"
)

visualise_preprocessing_output(
    preprocessing_path,
    time_range=(1, 2),
    as_subplot=True,
)  # Note this accepts any argument that .visualise() does
