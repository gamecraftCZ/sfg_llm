from sfg_audiobook.common.errors import ComponentParserError
from sfg_audiobook.components import ComponentsRegister
from sfg_audiobook.structure import AbstractComponent


class ComponentParser:
    @staticmethod
    def parse_component_string(component_string: str) -> AbstractComponent:
        """
        Parse a component string into instantiated component.
        """
        if "[" in component_string and "]" in component_string:
            registered_name, args_str = component_string.split("[", 1)
            args_str = args_str.rstrip("]")
            args = ComponentParser.parse_component_params(args_str)
        else:
            registered_name = component_string
            args = {}

        # Only setup is run if the component is prefixed with "!", otherwise it is set up and also run.
        should_run = True
        if registered_name[0] == "!":
            registered_name = registered_name[1:]
            should_run = False

        ComponentClass = ComponentsRegister.get_component(registered_name)
        if ComponentClass is None:
            raise ComponentParserError(
                f"Component '{registered_name}' not found in registered components. Available components: {ComponentsRegister.get_all_components().keys()}")

        component = ComponentClass(args, should_run=should_run)
        return component

    @staticmethod
    def parse_component_params(params_string: str) -> dict[str, str]:
        """
        Parse a component parameters string into a dictionary.
        """
        try:
            return dict(arg.split("=") for arg in params_string.split(","))
        except ValueError:
            raise ComponentParserError(
                f"Invalid argument format in '{params_string}'. Expected 'arg1=val1,arg2=val2,...'")
