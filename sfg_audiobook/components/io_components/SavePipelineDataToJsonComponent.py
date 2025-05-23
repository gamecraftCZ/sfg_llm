from datetime import datetime

from sfg_audiobook.common.errors import ComponentParserError
from sfg_audiobook.components.ComponentsRegister import ComponentsRegister
from sfg_audiobook.sfg_types import PipelineData
from sfg_audiobook.structure.AbstractComponent import AbstractComponent


class SavePipelineDataComponentToJson(AbstractComponent):
    """
    Saves whole pipeline data to a file.
    """

    def __init__(self, params: dict[str, str], *args, **kwargs) -> None:
        super().__init__(params, *args, **kwargs)
        if "file" not in params:
            raise ComponentParserError("file parameter is required for SavePipelineDataComponent.")

    @staticmethod
    def get_help() -> str:
        return """Saves whole pipeline data to a file.\n\tAttributes: file (will be formated using datetime.strftime)"""

    def setup(self, data: PipelineData):
        pass

    def run(self, data: PipelineData):
        filepath = self._params["file"]
        filepath = datetime.now().strftime(filepath)
        print(f"{self._name}: Saving pipeline data to: {filepath}")
        data.additional_attributes["last_save_path"] = filepath
        with open(filepath, "w+", encoding="utf-8") as f:
            json_text = data.model_dump_json(indent=4)
            f.write(json_text)


ComponentsRegister.register_component("save_pipeline_data_json", SavePipelineDataComponentToJson)
