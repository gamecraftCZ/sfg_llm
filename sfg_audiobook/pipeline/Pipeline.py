from sfg_audiobook.components import ComponentParser
from sfg_audiobook.sfg_types import PipelineData
from sfg_audiobook.structure import AbstractComponent


class Pipeline:
    def __init__(self, components: list[AbstractComponent]):
        self.components = components
        self._data = None

    def setup_and_run(self, input_data: PipelineData | None = None) -> PipelineData:
        if input_data:
            self._data = input_data
        elif self._data is None:
            self._data = PipelineData()

        # Setup components
        for component in self.components:
            print(f"Setting up component {component.get_name()} of type {component.__class__.__name__}")
            component.setup(self._data)

        # Run pipeline
        for component in self.components:
            print(f"Running component {component.get_name()} of type {component.__class__.__name__}")
            component.run(self._data)

        print("PIPELINE finished.")
        # Return result
        return self._data

    @staticmethod
    def from_component_strings(component_strings: list[str]) -> 'Pipeline':
        """
        Create a pipeline from a list of component strings.
        """
        # Parse components
        components = []
        for component_string in component_strings:
            components.append(ComponentParser.parse_component_string(component_string))

        # Name components
        for i, component in enumerate(components):
            component.set_name(f"{component.__class__.__name__}_{i}")

        return Pipeline(components)
