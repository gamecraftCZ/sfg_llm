from sfg_audiobook.structure import AbstractComponent


class ComponentParserError(ValueError):
    """Exception raised when a component parsing fails. Contains message."""
    def __init__(self, message: str):
        super().__init__(f"{message}")


class ComponentError(ValueError):
    """Exception raised when a component parsing fails. Contains message."""
    def __init__(self, component: AbstractComponent, message: str):
        super().__init__(f"{component.get_name()}: {message}")
