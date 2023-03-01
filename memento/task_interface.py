"""
Contains MEMENTO's task interface, once the configurations are
generated and dispatched to tasks, we need some way to interact
with the user code
"""
import datetime
import os
import sqlite3
import tempfile
import time
from collections import namedtuple
from typing import Any, Optional, Union, Tuple, Dict, List, cast
from typing import Callable

import cloudpickle
import pandas as pd
from pandas import DataFrame

from memento.configurations import Config
from memento.caching import default_key_provider

Metric = namedtuple("Metric", "x y")


class FileSystemCheckpointing:
    """
    A filesystem checkpoint. Uses SQLITE3 to write to a database file on disk.
    """

    def __init__(
        self,
        filepath: str = None,
        key: Callable = None,
        connection: sqlite3.Connection = None,
    ):
        """
        Creates a FileSystemCheckpointing, optionally using a DB connection or filepath.
        :param filepath: A filepath to use for the database file.
        :param connection: A sqlite3 DB connection to use. Supplying this breaks parallelization.
        """
        self._filepath = os.path.abspath(
            filepath or tempfile.NamedTemporaryFile(suffix="_memento.checkpoint").name
        )
        self._table_name = "checkpoint_table"
        self.key = key or default_key_provider
        self._connection = connection

        self._setup_database()

    def _setup_database(self) -> None:
        """
        :return: Nothing.
        """
        with self as databases:
            databases.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._table_name} (
                    key BINARY PRIMARY KEY,
                    ts REAL NOT NULL DEFAULT ((julianday('now') - 2440587.5)*86400.0),
                    value BLOB NOT NULL
                ) WITHOUT ROWID
            """
            )

    def __enter__(self) -> sqlite3.Connection:
        """
        Used to connect to the underlying database safely, handling setup and teardown.

        Runs at the beginning of a `with _ as _` block
        ...
            with File_System_Checkpointing_Object as database:
                database.execute("some SQL")

        :return: A sqlite3 Connection object, representing a database connection.
        """
        return self._connection or sqlite3.Connection(
            self._filepath, isolation_level="DEFERRED"
        )

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Run at the end of the `with _ as _` block
        ...
            with File_System_Checkpointing_Object as database:
                database.execute("some SQL")

        :return: Nothing.
        """

    def __str__(self) -> str:
        """
        Creates a human-readable string of the checkpoint.
        :return: A string representing the checkpoint.
        """
        return f"Filesystem checkpoint, using {self._connection or self._filepath}"

    def get(self, key: str):
        """
        Gets the item in the checkpoint specified by the key.
        :param key: Used to get the item from the cache.
        :returns: The item in the checkpoint, if it exists.
        :raise KeyError: When the key has not been checkpoint.
        """
        with self as database:
            rows = database.execute(
                f"SELECT value FROM {self._table_name} WHERE key = ?", (key,)
            ).fetchall()
            if rows:
                return cloudpickle.loads(rows[0][0])[0]

            raise KeyError(f"Key '{key}' not in checkpoint")

    def set(self, key: str, item) -> None:
        """
        Checkpoint the item with a specified key.
        :param key: The location for the item in checkpoint.
        :param item: The item to be checkpoint.
        :returns: Nothing.
        """
        with self as database:
            database.execute(
                f"INSERT OR REPLACE INTO {self._table_name}(key,value) VALUES(?,?)",
                (key, cloudpickle.dumps(item)),
            )
            database.commit()

    def remove(self, key: str):
        """
        Remove checkpoint by using key
        :param key: Key of the checkpoint
        :returns: None
        """
        with self as database:
            database.execute(f"DELETE FROM {self._table_name} WHERE key = ?", (key,))
            database.commit()

    def contains(self, key: str) -> bool:
        """
        Checks whether a key has been checkpoint.
        :param key: The key to check.
        :returns: True if it exists, False otherwise.
        """
        try:
            self.get(key)
            return True
        except KeyError:
            return False

    def make_key(self, *args, **kwargs) -> str:
        """
        Generates a key to be used in checkpointing.
        :param args: Arguments to the function to be checkpoint.
        :param kwargs: Keyword arguments to the function to be checkpoint.
        :returns: True if it exists, False otherwise.
        """
        return self.key(*args, **kwargs)


class Context:
    """
    The ``Context`` makes MEMENTO's utilities like checkpointing, metrics,
    progress reporting, and more available to tasks.
    """

    _metrics: Dict[str, List[Metric]]

    def __init__(self, key: str, checkpoint_provider: FileSystemCheckpointing):
        """
        Each context is associated with exactly one task.

        :param key: This is the key provided by memento for each task.
        :param checkpoint_provider: The checkpoint provider, defaults to FileSystemCheckpointing
        """
        self.key = key
        self._metrics = {}
        self._checkpoint_provider = checkpoint_provider
        self.checkpoint_key = None

    def collect_metrics(self) -> Dict[str, pd.DataFrame]:
        """
        Collects all of the metrics as dataframes.
        :return: A dictionary of metric names that map to Pandas Dataframes.
        """
        metrics: Dict[str, DataFrame] = {}
        for name in self._metrics:
            metrics[name] = pd.DataFrame(self._metrics[name])

        return metrics

    def record(self, value_dict: Dict[str, Union[float, Tuple[float, float]]]) -> None:
        """
        Records a floating point metric in one of the following formats.
        Default x value is a timestamp.
        Metrics are available as part of the results object.

        ..
            context.record({"metric_name": value})
            context.record({"metric_name": (x,y)})

            # Record with the same timestamp
            context.record({"metric_1": value1, "metric_2": value2})

        :return: None.
        :param value_dict:
        """
        x_value = time.time()

        for name in value_dict:
            y_value = value_dict[name]

            # Handles the case of a tuple
            if isinstance(y_value, tuple):
                y_value = cast(Tuple[float, float], y_value)
                x_value = y_value[0]
                y_value = y_value[1]

            # Type guards that shouldn't be triggered.
            assert isinstance(x_value, float)
            assert isinstance(y_value, float)

            metric = Metric(x_value, y_value)
            if self._metrics.get(name, False):
                self._metrics[name].append(metric)
            else:
                self._metrics[name] = [metric]

    def progress(self, delta, total=None):  # pylint: disable=no-self-use
        """
        Update the progress estimate, changing the current progress by ``delta``.
        The first call to this should (if possible) estimate the total amount of work.
        This can later be refined by passing a different value of ``total``.
        """
        raise NotADirectoryError("feature: progress")

    def checkpoint(self, *func) -> None:
        """
        Save the current state of the task.
        :param func: The function to be checkpoint.
        """
        # self.checkpoint_key = self._checkpoint_provider.make_key(self.key, func)
        self._checkpoint_provider.set(self.key, func)

    def restore(self):
        """
        Save the current state of the task.
        :return: The function saved to the key
        """
        return self._checkpoint_provider.get(self.key)

    def checkpoint_exist(self):
        """
        Checks if checkpoint already exists
        """
        return self._checkpoint_provider.contains(self.key)


class MemoryUsage:
    """
    Memory usage statistics recorded from a task.
    """

    virtual_peak: int
    hardware_peak: int

    def __init__(self, virtual_peak: int, hardware_peak: int):
        self.virtual_peak = virtual_peak
        self.hardware_peak = hardware_peak


class Result:
    """
    The result from a single task. This contains the value returned from the experiment, ``inner``,
    and metadata about the task run.
    """

    config: Config

    inner: Any

    metrics: Dict[str, pd.DataFrame]

    "The start time of the task."
    start_time: datetime.datetime

    "The task's runtime, measured on the wall clock."
    runtime: datetime.timedelta
    "The task's runtime, measured by the CPU"
    cpu_time: Optional[datetime.timedelta]
    "Memory usage statistics"
    memory: Optional[MemoryUsage]

    "Whether or not this result was retrieved from cache."
    was_cached: bool

    def __init__(  # pylint: disable=too-many-arguments
        self,
        config,
        inner,
        metrics: Dict[str, pd.DataFrame],
        start_time: datetime.datetime,
        runtime: datetime.timedelta,
        cpu_time: Optional[datetime.timedelta],
        memory: Optional[MemoryUsage],
        was_cached: bool,
    ):
        self.config = config
        self.inner = inner
        self.metrics = metrics
        self.start_time = start_time
        self.runtime = runtime
        self.cpu_time = cpu_time
        self.memory = memory
        self.was_cached = was_cached
