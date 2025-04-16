from sfg_types import PipelineData
from structure import AbstractComponent


class Pipeline:
    def __init__(self, components: list[AbstractComponent]):
        self.components = components
        self._data = None

    def setup_and_run(self, input_data: PipelineData | None) -> PipelineData:
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
