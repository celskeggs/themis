import typing


class ActionState:
    pass


AutonomousType = typing.Callable[[ActionState], None]
