import argparse
import json
import sys

from common.errors import ComponentParserError
from components import ComponentParser
from components.ComponentsRegister import ComponentsRegister
from pipeline import Pipeline
from sfg_types import PipelineData
from structure import AbstractComponent


def run_from_cli():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="CLI for text to audiobook conversion.")
    parser.add_argument(
        "--list_components",
        action="store_true",
        help="List all available components.",
    )
    parser.add_argument(
        "--list_pipelines",
        action="store_true",
        help="List all predefined pipelines.",
    )
    # TODO args for predefined pipeline like input file etc.
    parser.add_argument(
        "--pipeline",
        type=str,
        help="Specify a pipeline to use.",
        choices=["custom"]  # dummy, default, default_logging
    )
    parser.add_argument("--component", action="append", metavar="ComponentName[arg1=val2,arg2=val2]",
                        help="Specify components for custom pipeline (can be used multiple times)")

    args = parser.parse_args()

    # List available components
    if args.list_components:
        list_available_components()
        sys.exit(0)

    # TODO predefined pipelines
    if args.list_pipelines:
        print("Predefined pipelines list is not implemented yet.")
        sys.exit(1)

    if not args.pipeline:
        parser.error("--pipeline is required unless --list_components or --list_pipelines is specified")

    # Parse pipeline into components instances
    if args.pipeline == "custom":
        if not args.component:
            parser.error("At least one --component must be specified for a custom pipeline")
        try:
            pipeline = Pipeline.from_component_strings(args.component)
        except ComponentParserError as e:
            print(e)
            sys.exit(1)

    else:
        # TODO Load predefined pipelines
        print(f"Pipeline '{args.pipeline}' is not implemented yet.")
        pipeline = Pipeline([])
        sys.exit(1)

    # Run parsed pipeline
    results = pipeline.setup_and_run(PipelineData())


def list_available_components():
    """
    List all available components in the system.
    """
    components = ComponentsRegister.get_all_components()
    print(f"Available components ({len(components)} total):\n")
    for name, component in components.items():
        print(f"{name}:\n\t{component.get_help()}\n")


if __name__ == "__main__":
    run_from_cli()
