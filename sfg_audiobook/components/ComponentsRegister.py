from structure import AbstractComponent


class ComponentsRegister:
    """
    Registers components for use in the application.
    """

    _components: dict[str, type[AbstractComponent]] = {}

    @staticmethod
    def register_component(component_name: str,
                           component: type[AbstractComponent]):
        """
        Register a component with a given name.
        :param component_name: The name of the component to register.
        :param component: The component class to register.
        """
        assert issubclass(component, AbstractComponent), f"Component {component} is not a subclass of {AbstractComponent}."
        assert component_name not in ComponentsRegister._components.keys(), f"Component with name {component_name} is already registered."

        # Register
        ComponentsRegister._components[component_name] = component

    @staticmethod
    def get_component(component_name: str) -> type[AbstractComponent] | None:
        """
        Retrieve a registered component by its name.
        :param component_name: The name of the component to retrieve.
        :return : The component if found, otherwise None.
        """
        return ComponentsRegister._components.get(component_name, None)

    @staticmethod
    def get_all_components() -> dict[str, type[AbstractComponent]]:
        """
        Retrieve all registered components of a given type.
        :return : A dictionary of all registered components. Mutable pointer, do not modify in place!
        """
        return ComponentsRegister._components
