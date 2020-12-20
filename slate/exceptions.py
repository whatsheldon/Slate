
class SlateException(Exception):
    pass


class NodeException(SlateException):
    pass


class NodeCreationError(NodeException):
    pass


class NodeConnectionError(NodeException):
    pass


class NodeConnectionClosed(NodeException):
    pass


class NodeNotFound(NodeException):
    pass


class NoNodesFound(NodeException):
    pass


class PlayerAlreadyExists(SlateException):
    pass


class TrackLoadFailed(SlateException):

    def __init__(self, data: dict) -> None:

        self._data = data

        exception = data.get('exception')
        if exception:
            self._message = exception.get('message')
            self._severity = exception.get('severity')
        else:
            cause = data.get('cause')
            self._message = cause.get('message')
            self._severity = data.get('severity')

            self._class = cause.get('class')
            self._stack = cause.get('stack')
            self._cause = cause.get('cause')
            self._suppressed = cause.get('suppressed')

    @property
    def message(self) -> str:
        return self._message

    @property
    def severity(self) -> str:
        return self._severity


class TrackLoadError(SlateException):

    def __init__(self, message: str, data: dict) -> None:

        self._message = message
        self._data = data

        self._status_code = data.get('status_code')

    @property
    def message(self) -> str:
        return self._message

    @property
    def status_code(self) -> int:
        return self._status_code
