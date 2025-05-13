from sfg_audiobook.common.errors import ComponentParserError, ComponentError
from sfg_audiobook.components.ComponentsRegister import ComponentsRegister
from sfg_audiobook.sfg_types import PipelineData
from sfg_audiobook.structure.AbstractComponent import AbstractComponent


class LoadPipelineDataComponentFromJson(AbstractComponent):
    """
    Saves whole pipeline data to a file.
    """

    def __init__(self, params: dict[str, str], *args, **kwargs) -> None:
        super().__init__(params, *args, **kwargs)
        if "file" not in params:
            raise ComponentParserError("file parameter is required for LoadPipelineDataComponentFromJson.")

    @staticmethod
    def get_help() -> str:
        return """Saves whole pipeline data to a file.\n\tAttributes: file"""

    def setup(self, data: PipelineData):
        pass

    def run(self, data: PipelineData):
        filepath = self._params["file"]
        print(f"{self._name}: Loading pipeline data from (overwrites any previous PipelineData!): {filepath}")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                json_text = f.read()
                loaded_data = PipelineData.model_validate_json(json_text)
                data.__dict__.update(loaded_data.__dict__)
        except Exception as e:
            raise ComponentError(self, f"Error: {e}\nFailed to load pipeline data from {filepath}. Error above.")



ComponentsRegister.register_component("load_pipeline_data_json", LoadPipelineDataComponentFromJson)
