from collections import UserDict
from collections.abc import ItemsView, KeysView, ValuesView


class BaseUserDict(UserDict):
    """
    Base UserDict that implements the
    keys(), values() and items() convenience functions.
    """
    def __init__(self):
        super(BaseUserDict, self).__init__()

    def keys(self) -> KeysView:
        return self.data.keys()

    def items(self) -> ItemsView:
        return self.data.items()

    def values(self) -> ValuesView:
        return self.data.values()
