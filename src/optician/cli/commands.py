import argparse
import os
import sys

from optician.vc_client import GithubClient
from optician.db_client import DbClient as db
from optician.diff_tracker import DiffTracker
from optician.lookml_generator import LookMLGenerator
from optician.logger import Logger

CONSOLE_LOGGER = Logger().get_logger()


def cli():
    parser = argparse.ArgumentParser(description="Command line interface for optician")

    subparsers = parser.add_subparsers(dest="command", title="commands", metavar="")

    # track_diff_models parser
    diff_tracker_parser = subparsers.add_parser("diff_tracker", help="Run diff tracker")
    diff_tracker_parser.add_argument(
        "--db_type",
        type=str,
        help="Database type (bigquery, redshift, snowflake)",
        required=True,
    )
    diff_tracker_parser.add_argument(
        "--dataset1_name", type=str, help="Dataset 1", required=True
    )
    diff_tracker_parser.add_argument(
        "--dataset2_name", type=str, help="Dataset 2", required=True
    )
    diff_tracker_parser.add_argument(
        "--project", type=str, help="Project ID", required=True
    )
    # This argument is optional, but if it is not provided it will default to False
    diff_tracker_parser.add_argument(
        "--full-refresh",
        help="Full refresh of LookML base views",
        action=argparse.BooleanOptionalAction,
    )
    diff_tracker_parser.add_argument(
        "--service_account", type=str, help="Google Service Account", required=False
    )
    diff_tracker_parser.add_argument(
        "--models",
        type=str,
        help="List of models to compare (comma separated) or file path",
    )
    diff_tracker_parser.add_argument("--output", type=str, help="Output file path")

    # generate_lookml parser
    generate_lookml_parser = subparsers.add_parser(
        "generate_lookml", help="Run generate LookML"
    )
    generate_lookml_parser.add_argument(
        "--db_type",
        type=str,
        help="Database type (bigquery, redshift, snowflake)",
        required=True,
    )
    generate_lookml_parser.add_argument(
        "--project", type=str, help="Project ID", required=True
    )
    generate_lookml_parser.add_argument(
        "--dataset", type=str, help="Dataset ID to read the models from", required=True
    )
    generate_lookml_parser.add_argument(
        "--tables",
        type=str,
        help="List of Table IDs separated by comma or provide a file path",
        required=True,
    )
    generate_lookml_parser.add_argument(
        "--output-dir", type=str, help="Output Directory", required=False
    )
    generate_lookml_parser.add_argument(
        "--override-dataset-id", type=str, help="Override Dataset ID", required=False
    )
    generate_lookml_parser.add_argument(
        "--service-account", type=str, help="Service Account", required=False
    )

    # push_to_looker
    push_to_looker_parser = subparsers.add_parser(
        "push_to_looker", help="Run Push to Looker"
    )
    push_to_looker_parser.add_argument(
        "--token", type=str, help="GitHub Token", required=True
    )
    push_to_looker_parser.add_argument(
        "--repo", type=str, help="GitHub Repo", required=True
    )
    push_to_looker_parser.add_argument(
        "--user-email", type=str, help="GitHub User Email", required=False
    )
    push_to_looker_parser.add_argument(
        "--input-dir",
        type=str,
        help="Path that contains new files to be committed",
        required=True,
    )
    push_to_looker_parser.add_argument(
        "--output-dir",
        type=str,
        help="Directory to write the LookML files to",
        required=True,
    )
    push_to_looker_parser.add_argument(
        "--branch-name",
        type=str,
        help="Name of the branch to be created",
        required=True,
    )
    push_to_looker_parser.add_argument(
        "--base-branch",
        type=str,
        help="Name of the base branch",
        default="main",
    )

    args = parser.parse_args()
    if args.command == "diff_tracker":
        models = args.models.split(",")
        if len(models) == 1:
            # If the tables argument is a file path, read the file and split on newlines
            if "." in models[0]:
                models_file_path = models[0]
                with open(models_file_path, "r") as file:
                    models = file.read().splitlines()

        CONSOLE_LOGGER.info(f"Models to be compared: {models}")

        credentials = {
            "service_account": args.service_account,
            "project_id": args.project,
            # Add other credentials for other databases here
        }

        db_client = db(db_type=args.db_type, credentials=credentials)

        dt = DiffTracker(
            dataset1_name=args.dataset1_name,
            dataset2_name=args.dataset2_name,
            db_client=db_client,
            models=models,
            full_refresh=args.full_refresh,
        )
        results = dt.get_diff_tables()
        CONSOLE_LOGGER.info(f"New models: {results['new_models']}")
        CONSOLE_LOGGER.info(f"Diff models: {results['diff_models']}")
        CONSOLE_LOGGER.info(f"Missing models: {results['missing_models']}")

        # Save output to file
        output = results["diff_models"]
        output += results["new_models"]
        with open(args.output, "w") as f:
            for o in output:
                f.write(f"{o}\n")
            pass

    elif args.command == "generate_lookml":
        tables = args.tables.split(",")
        if len(tables) == 1:
            # If the tables argument is a file path, read the file and split on newlines
            if "." in tables[0]:
                tables_file_path = tables[0]
                with open(tables_file_path, "r") as file:
                    tables = file.read().splitlines()

        CONSOLE_LOGGER.info(f"Models to be created: {tables}")

        credentials = {
            "service_account": args.service_account,
            "project_id": args.project
            # Add other credentials for other databases here
        }

        db_client = db(db_type=args.db_type, credentials=credentials)
        lookml = LookMLGenerator(db_client, args.dataset)
        lookml.generate_batch_lookml_views(
            tables=tables,
            output_dir=args.output_dir,
            override_dataset_id=args.override_dataset_id,
        )

    elif args.command == "push_to_looker":
        if not os.path.exists(args.input_dir):
            CONSOLE_LOGGER.warn(
                f"Input directory {args.input_dir} does not exist. No files to commit. Exiting..."
            )

        else:
            # Create Github client

            G = GithubClient(
                token=args.token,
                repo=args.repo,
                user_email=args.user_email,
            )

            # Create branch and commit files
            G.update_files(
                input_dir=args.input_dir,
                output_dir=args.output_dir,
                target_branch=args.branch_name,
                base_branch=args.base_branch,
            )


def execute_from_command_line():
    cli()
