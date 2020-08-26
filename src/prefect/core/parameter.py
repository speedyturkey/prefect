from typing import TYPE_CHECKING, Any, Dict, Iterable

import prefect
import prefect.engine.signals
import prefect.triggers
from prefect.core.task import Task
from prefect.engine.results import PrefectResult

if TYPE_CHECKING:
    from prefect.core.flow import Flow  # pylint: disable=W0611


# A sentinel value indicating no default was provided
no_default = type(
    "no_default",
    (object,),
    dict.fromkeys(["__repr__", "__reduce__"], lambda s: "no_default"),
)()


class Parameter(Task):
    """
    A Parameter is a special task that defines a required flow input.

    A parameter's "slug" is automatically -- and immutably -- set to the parameter name.
    Flows enforce slug uniqueness across all tasks, so this ensures that the flow has
    no other parameters by the same name.

    Args:
        - name (str): the Parameter name.
        - default (any, optional): A default value for the parameter.
        - required (bool, optional): If True, the Parameter is required and the
            default value is ignored. Defaults to `False` if a `default` is
            provided, otherwise `True`.
        - tags ([str], optional): A list of tags for this parameter

    """

    def __init__(
        self,
        name: str,
        default: Any = no_default,
        required: bool = None,
        tags: Iterable[str] = None,
    ):
        if required is None:
            required = default is no_default
        if default is no_default:
            default = None
        self.required = required
        self.default = default

        super().__init__(
            name=name,
            slug=name,
            tags=tags,
            result=PrefectResult(),
            checkpoint=True,
        )

    def __repr__(self) -> str:
        return "<Parameter: {self.name}>".format(self=self)

    def __call__(self, flow: "Flow" = None) -> "Parameter":  # type: ignore
        """
        Calling a Parameter adds it to a flow.

        Args:
            - flow (Flow, optional): The flow to set dependencies on, defaults to the current
                flow in context if no flow is specified

        Returns:
            - Task: a new Task instance

        """
        result = super().bind(flow=flow)
        assert isinstance(result, Parameter)  # mypy assert
        return result

    def copy(self, name: str, **task_args: Any) -> "Task":  # type: ignore
        """
        Creates a copy of the Parameter with a new name.

        Args:
            - name (str): the new Parameter name
            - **task_args (dict, optional): a dictionary of task attribute keyword arguments,
                these attributes will be set on the new copy

        Raises:
            - AttributeError: if any passed `task_args` are not attributes of the original

        Returns:
            - Parameter: a copy of the current Parameter, with a new name and any attributes
                updated from `task_args`
        """
        return super().copy(name=name, slug=name, **task_args)

    def run(self) -> Any:
        params = prefect.context.get("parameters") or {}
        if self.required and self.name not in params:
            self.logger.debug(
                'Parameter "{}" was required but not provided.'.format(self.name)
            )
            raise prefect.engine.signals.FAIL(
                'Parameter "{}" was required but not provided.'.format(self.name)
            )
        return params.get(self.name, self.default)

    # Serialization ------------------------------------------------------------

    def serialize(self) -> Dict[str, Any]:
        """
        Creates a serialized representation of this parameter

        Returns:
            - dict representing this parameter
        """
        return prefect.serialization.task.ParameterSchema().dump(self)
