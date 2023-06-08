from swc_ephys.pipeline.visualise import visualise_preprocessing_output

preprocessing_path = (
    r"X:\neuroinformatics\scratch\jziminski\ephys\test_data\steve_multi_run\1119617\time-mid\derivatives\1119617\all\preprocessed"
)

visualise_preprocessing_output(
    preprocessing_path,
    time_range=(1, 2),
    as_subplot=True,
)  # Note this accepts any argument that .visualise() does
