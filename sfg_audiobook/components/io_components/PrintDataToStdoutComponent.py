from common.errors import ComponentParserError
from components.ComponentsRegister import ComponentsRegister
from sfg_types import PipelineData
from structure.AbstractComponent import AbstractComponent


class PrintDataToStdoutComponent(AbstractComponent):
    """
    Saves whole pipeline data to a file.
    """
    _available_attributes = set(PipelineData.model_fields.keys())

    def __init__(self, params: dict[str, str], *args, **kwargs) -> None:
        super().__init__(params, *args, **kwargs)
        if "attrs" not in params:
            self._attributes = self._available_attributes
        else:  # Attributes specified
            attrs = params["attrs"]
            exclude_mode = False
            if params["attrs"].startswith("!"):
                attrs = attrs[1:]
                exclude_mode = True
            # Attributes are separated by space
            attr_strs = [attr for attr in attrs.split(";") if attr]
            if len(attr_strs) == 0:
                raise ComponentParserError("No attributes specified.")
            for attr_str in attr_strs:
                if attr_str not in self._available_attributes:
                    raise ComponentParserError(f"Attribute '{attr_str}' not available. Available attributes: {self._available_attributes}")
            if exclude_mode:
                self._attributes = self._available_attributes - set(attr_strs)
            else:
                self._attributes = set(attr_strs)

    @staticmethod
    def get_help() -> str:
        return f"""Prints whole pipeline data to standard output.
\tAttributes: attrs (optional) (';' separated list of attributes to print ({PrintDataToStdoutComponent._available_attributes}). If starts with '!', it means all attributes except specified ones.)"""

    def setup(self, data: PipelineData):
        pass

    def run(self, data: PipelineData):
        print(f"PipelineData ({len(self._attributes)}/{len(self._available_attributes)}):"
              f" [{data.model_dump_json(include=self._attributes, indent=2)}]")


ComponentsRegister.register_component("print_pipeline_data", PrintDataToStdoutComponent)
