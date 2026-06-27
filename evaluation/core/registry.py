from typing import Dict, Type, Any

class EvaluationRegistry:
    _scenarios: Dict[str, Type[Any]] = {}
    _plugins: Dict[str, Any] = {}

    @classmethod
    def register_scenario(cls, name: str):
        def decorator(subclass: Type[Any]):
            cls._scenarios[name.lower()] = subclass
            return subclass
        return decorator

    @classmethod
    def get_scenario(cls, name: str) -> Type[Any]:
        scenario_cls = cls._scenarios.get(name.lower())
        if not scenario_cls:
            raise KeyError(f"Scenario '{name}' is not registered. Available: {list(cls._scenarios.keys())}")
        return scenario_cls

    @classmethod
    def list_scenarios(cls) -> Dict[str, Type[Any]]:
        return cls._scenarios

    @classmethod
    def register_plugin(cls, name: str, plugin_instance: Any):
        cls._plugins[name.lower()] = plugin_instance

    @classmethod
    def get_plugin(cls, name: str) -> Any:
        return cls._plugins.get(name.lower())
