from sfg_audiobook.common.errors import ComponentParserError
from sfg_audiobook.components.ComponentsRegister import ComponentsRegister
from sfg_audiobook.sfg_types import PipelineData
from sfg_audiobook.structure.AbstractComponent import AbstractComponent


class LoadTextFromFileComponent(AbstractComponent):
    """
    Components that loads the text input from file into pipeline data.
    """

    def __init__(self, params: dict[str, str], *args, **kwargs) -> None:
        super().__init__(params, *args, **kwargs)
        if "file" not in params:
            raise ComponentParserError("file parameter is required for LoadTextFromFileComponent.")

    @staticmethod
    def get_help() -> str:
        return """Loads source text from a file into the pipeline data.\n\tAttributes: file"""

    def setup(self, data: PipelineData):
        pass

    def run(self, data: PipelineData):
        with open(self._params["file"], "r", encoding="utf-8") as file:
            data.original_text = file.read()


ComponentsRegister.register_component("load_text_from_file", LoadTextFromFileComponent)
