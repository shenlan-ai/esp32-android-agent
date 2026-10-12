class AgentError(RuntimeError):
    """An actionable error safe to present to the user."""


class DeviceError(AgentError):
    pass


class ScreenError(AgentError):
    pass


class StaleFrameError(ScreenError):
    pass
