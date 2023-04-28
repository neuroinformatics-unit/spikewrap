from swc_ephys.pipeline.visualise import visualise_preprocessing_output

preprocessing_path = (
    r"/home/joe/data/derivatives/1110925/1110925_test_shank1_cut/preprocessed"
)

visualise_preprocessing_output(
    preprocessing_path, time_range=(1, 2)
)  # Note this accepts any argument that .visualise() does
