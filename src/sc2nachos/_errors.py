"""The root of the exceptions the library raises for failures of its own."""


class NachOSError(Exception):
    """Something the library was asked to do failed. Misuse, such as a bad argument, raises a built-in instead."""
