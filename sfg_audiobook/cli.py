import argparse
import json
import sys

from common.ComponentParserError import ComponentParserError
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
        components = [parse_component_string(component_string) for i, component_string in enumerate(args.component)]
        for i, component in enumerate(components):
            component.set_name(f"{component.__class__.__name__}_{i}")

    else:
        # TODO Load predefined pipelines
        print(f"Pipeline '{args.pipeline}' is not implemented yet.")
        components = []
        sys.exit(1)

    # Run parsed pipeline
    pipeline = Pipeline(components)
    results = pipeline.setup_and_run(PipelineData())


def list_available_components():
    """
    List all available components in the system.
    """
    components = ComponentsRegister.get_all_components()
    print(f"Available components ({len(components)} total):\n")
    for name, component in components.items():
        print(f"{name}:\n\t{component.get_help()}\n")

def parse_component_string(component_string: str) -> AbstractComponent:
    """
    Parse a component string into instantiated component.
    """
    try:
        if "[" in component_string and "]" in component_string:
            registered_name, args_str = component_string.split("[", 1)
            args_str = args_str.rstrip("]")
            try:
                args = dict(arg.split("=") for arg in args_str.split(","))
            except ValueError:
                raise ComponentParserError(f"Invalid argument format in '{args_str}'. Expected 'arg1=val1,arg2=val2,...'")
        else:
            registered_name = component_string
            args = {}

        ComponentClass = ComponentsRegister.get_component(registered_name)
        if ComponentClass is None:
            raise ComponentParserError(f"Component '{registered_name}' not found in registered components. Available components: {ComponentsRegister.get_all_components().keys()}")

        component = ComponentClass(args)
        return component
    except ComponentParserError as e:
        print(f"Error parsing component string '{component_string}': {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run_from_cli()
