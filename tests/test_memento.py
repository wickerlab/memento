import os
import tempfile

import pytest

from memento.memento import Memento
from memento.notifications import FileSystemNotificationProvider


def _create_file(suffix: str = None):
    file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    file.close()
    return os.path.abspath(file.name)


def expensive_thing(x):
    return x


def expensive_thing2(x):
    return x + 1


class TestMemento:
    def setup_method(self, method):
        # This is ugly, but sqlite3 doesn't seem to accept a file handle directly, so we need to
        # create a temporary file, close it (to not run afoul of locking on windows), then manually
        # remove it after we're done.
        self._cache_filepath = _create_file("_memento.cache")
        self._notification_filepath = _create_file("_memento.notifications")

    def teardown_method(self, method):
        try:
            os.unlink(self._cache_filepath)
            os.unlink(self._notification_filepath)
        except PermissionError:
            pass

    @pytest.mark.slow
    def test_memento(self):
        def func(context, config):
            return config.k1

        memento = Memento(func)
        matrix = {"parameters": {"k1": ["v1", "v2", "v3"]}}
        results = memento.run(matrix, cache_path=self._cache_filepath)
        assert [result.inner for result in results] == ["v1", "v2", "v3"]

    def test_dry_run(self):
        def func(context, config):
            raise Exception("should not be called")

        memento = Memento(func)
        matrix = {"parameters": {"k1": ["v1", "v2", "v3"]}}
        results = memento.run(matrix, cache_path=self._cache_filepath, dry_run=True)
        assert results is None

    @pytest.mark.slow
    def test_was_cached(self):
        def func(context, config):
            return config.k1

        memento = Memento(func)
        matrix = {"parameters": {"k1": ["v1", "v2"]}}
        _ = memento.run(matrix, cache_path=self._cache_filepath)
        matrix = {"parameters": {"k1": ["v1", "v2", "v3"]}}
        results = memento.run(matrix, cache_path=self._cache_filepath)
        assert [result.inner for result in results] == ["v1", "v2", "v3"]
        assert [result.was_cached for result in results] == [True, True, False]

    @pytest.mark.slow
    def test_checkpointing(self):
        def func(context, config):
            if context.checkpoint_exist():
                intermediate = context.restore()
            else:
                intermediate = expensive_thing(config.k1)
                context.checkpoint(intermediate)
                intermediate = expensive_thing2(config.k1)

            intermediate2 = context.restore() + intermediate

            return intermediate2

        memento = Memento(func)
        matrix = {"parameters": {"k1": [1, 2]}}
        results = memento.run(matrix, cache_path=self._cache_filepath)

        assert [result.inner for result in results] == [3, 5]

    @pytest.mark.slow
    def test_run_multiple(self):
        def func(context, config):
            return config.asdict()

        memento = Memento(func)

        memento.add_matrix({"id": 2, "dependencies": [1], "parameters": {"k1": ["a"]}})

        memento.add_matrix(
            {"id": 1, "dependencies": [], "parameters": {"k1": [1, 2, 3]}}
        )

        # Matrix with no dependencies or dependants
        memento.add_matrix(
            {"id": 3, "dependencies": [], "parameters": {"k1": [4, 5, 6]}}
        )

        results = memento.run_all(cache_path=self._cache_filepath)

        results_1 = results[1]
        assert [result.inner["k1"] for result in results_1] == [1, 2, 3]

        results_2 = results[2]
        assert all("1" in result.inner for result in results_2)
        assert [result.inner["1"]["k1"] for result in results_2] == [1, 2, 3]
        assert [result.inner["k1"] for result in results_2] == ["a", "a", "a"]

        results_3 = results[3]
        assert [result.inner["k1"] for result in results_3] == [4, 5, 6]

    def test_run_multiple_dry(self):
        def func(context, config):
            raise Exception("should not be called")

        memento = Memento(func)

        memento.add_matrix({"id": 2, "dependencies": [1], "parameters": {"k1": ["a"]}})

        memento.add_matrix(
            {"id": 1, "dependencies": [], "parameters": {"k1": [1, 2, 3]}}
        )

        results = memento.run_all(cache_path=self._cache_filepath, dry_run=True)
        assert results is None

    @pytest.mark.slow
    def test_run_with_notification_provider(self):
        def func(context, config):
            return config.k1

        notification_provider = FileSystemNotificationProvider(
            filepath=self._notification_filepath
        )
        memento = Memento(func, notification_provider=notification_provider)
        matrix = {"parameters": {"k1": ["v1"]}}
        _ = memento.run(matrix, cache_path=self._cache_filepath)

        with open(self._notification_filepath) as f:
            assert f.readlines() == ["Task completed\n", "All tasks completed\n"]

    @pytest.mark.slow
    def test_run_all_with_notification_provider(self):
        def func(context, config):
            return config.k1

        notification_provider = FileSystemNotificationProvider(
            filepath=self._notification_filepath
        )
        memento = Memento(func, notification_provider=notification_provider)

        memento.add_matrix({"id": 2, "dependencies": [1], "parameters": {"k1": ["a"]}})

        memento.add_matrix({"id": 1, "dependencies": [], "parameters": {"k1": [1]}})

        _ = memento.run_all(cache_path=self._cache_filepath)

        with open(self._notification_filepath) as f:
            assert f.readlines() == [
                "Task completed\n",
                "Task completed\n",
                "All tasks completed\n",
            ]
