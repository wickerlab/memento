"""
Exceptions raised by Memento.
"""
from typing import List

from memento.configurations import Config


class AggregateException(Exception):
    """
    Raised when one or more exceptions are raised when running tasks.
    """

    def __init__(self, exceptions: List[Exception]) -> None:
        message = ",\n\t".join(
            f"{type(exception).__name__}: {str(exception)}" for exception in exceptions
        )
        super().__init__(f"One or more exceptions were encountered:\n\t{message}")
        self.exceptions = exceptions


class CacheMiss(Exception):
    """
    Raised when ``force_cache=True`` is passed to ``Memento.run`` and an experiment was not found
    in the cache.
    """

    def __init__(self, config: Config) -> None:
        super().__init__(f"Config {config} was not found in the cache")


class CyclicDependency(Exception):
    """
    Raised when ``run_all`` is called with a cyclic dependency in one or more of the matrices.
    """

    def __init__(self) -> None:
        super().__init__("Cyclic dependency detected")
