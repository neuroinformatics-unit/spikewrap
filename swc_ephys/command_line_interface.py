import argparse

from .pipeline.full_pipeline import run_full_pipeline

parser = argparse.ArgumentParser()

parser.add_argument(
    "base_path",
    type=str,
    help="The base path where the data is stored, containing the rawdata folder.",
)

parser.add_argument(
    "sub_name",
    type=str,
    help="subject name, should match a subject folder name in rawdata.",
)

parser.add_argument(
    "run_name",
    type=str,
    help="spikeglx run name for the subject. Should not contain the gate. e.g.\n"
    "1110925_test_shank1",
)

parser.add_argument(
    "--config-name",
    "--config_name",
    type=str,
    default="test",
    help="name of the configuration file to use.",
)

parser.add_argument(
    "--sorter",
    type=str,
    default="kilosort2_5",
    help="name of the sorter to use.",
)

parser.add_argument(
    "--use-existing-preprocessed-file",
    "--use_existing_preprocessed_file",
    action="store_true",
    help="If true, during sorting an existing preprocessing data folder\n"
    "for the subject will be used if it already exists.",
)


def main():
    args = parser.parse_args()

    run_full_pipeline(
        base_path=args.base_path,
        sub_name=args.sub_name,
        run_name=args.run_name,
        config_name=args.config_name,
        sorter=args.sorter,
        use_existing_preprocessed_file=args.use_existing_preprocessed_file,
    )


if __name__ == "__main__":
    main()
