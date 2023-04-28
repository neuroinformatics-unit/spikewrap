from swc_ephys.pipeline.visualise import visualise_preprocessing_output

preprocessing_path = (
    # "/home/joe/data/derivatives/1110925/1110925_test_shank1_cut/preprocessed"
    "/home/joe/data/steve_multi_run/derivatives/1119617/all/preprocessed"
    # r"/home/joe/data/derivatives/1110925/1110925_test_shank1_cut/preprocessed"
)

visualise_preprocessing_output(
    preprocessing_path,
    time_range=(1, 2),
    as_subplot=True,
)  # Note this accepts any argument that .visualise() does
