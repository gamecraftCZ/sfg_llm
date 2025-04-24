from common.errors import ComponentParserError
from components import ComponentsRegister
from structure import AbstractComponent


class ComponentParser:
    @staticmethod
    def parse_component_string(component_string: str) -> AbstractComponent:
        """
        Parse a component string into instantiated component.
        """
        if "[" in component_string and "]" in component_string:
            registered_name, args_str = component_string.split("[", 1)
            args_str = args_str.rstrip("]")
            try:
                args = dict(arg.split("=") for arg in args_str.split(","))
            except ValueError:
                raise ComponentParserError(
                    f"Invalid argument format in '{args_str}'. Expected 'arg1=val1,arg2=val2,...'")
        else:
            registered_name = component_string
            args = {}

        ComponentClass = ComponentsRegister.get_component(registered_name)
        if ComponentClass is None:
            raise ComponentParserError(
                f"Component '{registered_name}' not found in registered components. Available components: {ComponentsRegister.get_all_components().keys()}")

        component = ComponentClass(args)
        return component
