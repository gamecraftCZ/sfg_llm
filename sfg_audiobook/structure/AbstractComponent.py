from abc import ABC, abstractmethod

from sfg_audiobook.sfg_types import PipelineData


class AbstractComponent(ABC):
    """
    Abstract component class for all components in the pipeline.
    """

    def __init__(self, params: dict[str, str], name: str = None, *args, **kwargs) -> None:
        """
        :param params: list of parameters for the component in {name: value} format.
                        Defined in the CLI as Component[name=val,name2=val2,...]
        :param name: Optional name of the component
        :param args: Ignored
        :param kwargs: Ignored
        """
        self._params = params
        self._name = name if name else self.__class__.__name__

    def set_name(self, new_name: str):
        self._name = new_name

    def get_name(self) -> str:
        return self._name

    @staticmethod
    @abstractmethod
    def get_help() -> str:
        """
        Returns help text that will be displayed to the user.
        :return: Help string
        """
        raise NotImplementedError()

    @abstractmethod
    def setup(self, data: PipelineData) -> None:
        """
        Set up the component and pipeline data. E.g. set data.available_speakers if TTS component.
        :param data: PipelineData edited in place
        """
        raise NotImplementedError()

    @abstractmethod
    def run(self, data: PipelineData):
        """
        Run the component as a part of the pipeline.
        :param data: PipelineData edited in place
        """
        raise NotImplementedError()
