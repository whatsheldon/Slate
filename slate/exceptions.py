
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
