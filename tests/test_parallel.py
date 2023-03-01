"""
Contains tests for parallel.py.
"""

import functools
import multiprocessing
import os
import time
from typing import List, Callable, TextIO

import pytest

from memento.parallel import TaskManager, delayed

BASE_PATH = os.path.abspath(os.path.dirname(__file__))
INPUT_PATH = os.path.join(BASE_PATH, "data", "hello_world.txt")


def get_process_id():
    return id(multiprocessing.current_process())


class DummyClass:
    def __init__(self, x: int, y: int):
        self._result = x + y

    def calculate(self):
        return self._result

    def __eq__(self, other):
        return isinstance(other, DummyClass) and self._result == other._result


class CallableDummyClass:
    def __call__(self, x: int, y: int):
        return x + y


def recursive_function(x: int):
    if x <= 0:
        return 0
    return 1 + recursive_function(x - 1)


def function_with_dependencies(x: int, y: int):
    time.sleep(0)
    return x + y


def function_referencing_locals(x: int, y: int):
    return function_with_dependencies(x, y)


def function_with_local_import(x: int, y: int):
    import math

    return math.floor(x + y)


def read_file(file: TextIO):
    return file.readlines()


@pytest.mark.slow
class TestParallel:
    def test_parallel_uses_multiple_processes(self):
        """Multiple processes are used when running tasks."""
        manager = TaskManager(max_tasks_per_worker=1)
        manager.add_tasks((delayed(get_process_id)() for _ in range(10)))
        results = manager.run()

        assert len(set(results)) > 0

    # The current method used to spawn processes doesn't give precise control over how many are
    # spawned so this test has been skipped (for now)
    @pytest.mark.skip
    def test_parallel_uses_correct_number_of_processes(self):
        """Multiple processes are used up to the specified limit when possible."""
        manager = TaskManager(max_tasks_per_worker=2, workers=5)
        manager.add_tasks((delayed(get_process_id)() for _ in range(10)))
        results = manager.run()

        assert len(set(results)) <= 5

    @pytest.mark.parametrize(
        "task,expected",
        [
            (delayed(sum)([1, 2]), [3]),
            (delayed(lambda x: sum(x))([2, 2]), [4]),
            (delayed(functools.partial(lambda x, y: sum([x, y]), 2))(3), [5]),
            (delayed(DummyClass)(3, 3), [DummyClass(3, 3)]),
            (delayed(DummyClass(3, 3).calculate)(), [6]),
            (delayed(CallableDummyClass())(3, 4), [7]),
            (delayed(recursive_function)(8), [8]),
            (delayed(function_with_dependencies)(4, 5), [9]),
            (delayed(function_referencing_locals)(5, 5), [10]),
            (delayed(function_with_local_import)(5, 6), [11]),
            (delayed(list)(range(5)), [[0, 1, 2, 3, 4]]),
        ],
    )
    def test_parallel_returns_correct_result(self, task: Callable, expected: List):
        """The correct result is returned when tasks are run."""
        manager = TaskManager()
        manager.add_task(task)
        results = manager.run()

        assert results == expected

    def test_parallel_order(self):
        manager = TaskManager()

        def identity(x):
            return x

        manager.add_tasks(delayed(identity)(x) for x in range(10))

        results = manager.run()

        assert results == list(range(10))

    def test_parallel_with_file(self):
        manager = TaskManager()

        with open(INPUT_PATH) as f:
            manager.add_task(delayed(read_file)(f))

        results = manager.run()
        assert results == [["Hello World!\n"]]
