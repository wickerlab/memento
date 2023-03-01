"""
Contains classes for implementing caching of functions.
"""
import os
import sqlite3
import tempfile
from abc import ABC, abstractmethod
from typing import Callable
import cloudpickle


class CacheProvider(ABC):
    """
    Abstract base class for implementing a cache provider, allowing different forms of caching.

    Provides the interface that all cache providers must adhere to.

    Must be used as the parent class of a cache provider class.

    ..
        class CustomCacheProvider(CacheProvider):
    """

    def __getitem__(self, key: str):
        return self.get(key)

    def __setitem__(self, key: str, item):
        return self.set(key, item)

    def __contains__(self, key: str):
        return self.contains(key)

    @abstractmethod
    def __str__(self) -> str:
        """
        Creates a human-readable string of the cache.

        :return: A string representing the cache.
        """

    @abstractmethod
    def get(self, key: str):
        """
        Gets the item in the cache specified by the key.

        :param key: Used to get the item from the cache.
        :returns: The item in the cache, if it exists.
        :raise KeyError: When the key is not in the cache.
        """

    @abstractmethod
    def set(self, key: str, item) -> None:
        """
        Puts the item in the cache, at the specified key.

        :param key: The location for the item in the cache.
        :param item: The item to be cached.
        :returns: Nothing.
        """

    @abstractmethod
    def contains(self, key: str) -> bool:
        """
        Checks whether a key is already in the cache.

        :param key: The key to check.
        :returns: True if it exists, False otherwise.
        """

    @abstractmethod
    def make_key(self, func: Callable, *args, **kwargs) -> str:
        """
        Generates a key to be used in caching.

        :param func: The function to be cached.
        :param args: Arguments to the function to be cached.
        :param kwargs: Keyword arguments to the function to be cached.
        :returns: True if it exists, False otherwise.
        """


class MemoryCacheProvider(CacheProvider):
    """
    An in-memory cache provider. Uses a dictionary for underlying storage.
    """

    def __init__(self, initial_cache: dict = None, key_provider: Callable = None):
        """
        Creates a cache provider that uses memory for caching.

        :param initial_cache: Optional initial cache, defaults to an empty dictionary.
        """
        self._cache = initial_cache or {}

        self._key_provider = key_provider or default_key_provider

    def __str__(self):
        return str(self._cache)

    def get(self, key: str):
        return self._cache[key]

    def set(self, key: str, item) -> None:
        self._cache[key] = item

    def contains(self, key: str) -> bool:
        return self._cache.get(key, False) is not False

    def make_key(self, func: Callable, *args, **kwargs) -> str:
        return self._key_provider(func, *args, **kwargs)


class FileSystemCacheProvider(CacheProvider):
    """
    A filesystem caching provider. Uses SQLITE3 to write to a database file on disk.
    """

    def __init__(
        self,
        connection: sqlite3.Connection = None,
        filepath: str = None,
        key_provider: Callable = None,
        table_name: str = None,
    ):
        """
        Creates a FileSystemCacheProvider, optionally using a DB connection or filepath.
        :param connection: A sqlite3 DB connection to use. Supplying this breaks parallelization.
        :param filepath: A filepath to use for the database file (relative or absolute).
        """
        self._connection = connection  # if none is handled elsewhere
        # use a temporary file (in appropriate tmp dir) if no file provided
        self._filepath = os.path.abspath(
            filepath or tempfile.NamedTemporaryFile(suffix="_memento.cache").name
        )
        self._table_name = table_name or "cache"

        self._sqlite_timestamp = "(julianday('now') - 2440587.5)*86400.0"
        self._sql_select = f"SELECT value FROM {self._table_name} WHERE key = ?"
        self._sql_insert = (
            f"INSERT OR REPLACE INTO {self._table_name}(key,value) VALUES(?,?)"
        )

        self._key_provider = key_provider or default_key_provider

        self._setup_database()

    def _setup_database(self) -> None:
        """
        Sets up the database, creating a "cache" table, with a key, value, and timestamp column.
        :return: Nothing.
        """
        with self as database:
            database.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._table_name} (
                    key BINARY PRIMARY KEY,
                    ts REAL NOT NULL DEFAULT ({self._sqlite_timestamp}),
                    value BLOB NOT NULL
                ) WITHOUT ROWID
            """
            )

    def __enter__(self) -> sqlite3.Connection:
        """
        Used to connect to the underlying database safely, handling setup and teardown.

        Runs at the beginning of a `with _ as _` block
        ...
            with file_system_caching_object as database:
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
            with file_system_caching_object as database:
                database.execute("some SQL")

        :return: Nothing.
        """

    def __str__(self) -> str:
        return f"Filesystem cache, using {self._connection or self._filepath}"

    def get(self, key: str):
        with self as database:
            rows = database.execute(self._sql_select, (key,)).fetchall()
            if rows:
                return cloudpickle.loads(rows[0][0])

            raise KeyError(f"Key '{key}' not in cache")

    def set(self, key: str, item) -> None:
        with self as database:
            database.execute(self._sql_insert, (key, cloudpickle.dumps(item)))
            database.commit()

    def contains(self, key: str) -> bool:
        try:
            self.get(key)
            return True
        except KeyError:
            return False

    def make_key(self, func: Callable, *args, **kwargs) -> str:
        return self._key_provider(func, *args, **kwargs)


class Cache:
    """
    A higher order function that caches another, underlying function.
    """

    def __init__(self, func: Callable, cache_provider: CacheProvider = None):
        """
        Create the Cache object.

        Usage can be one of the following:

        ..
            @Cache
            def underlying_function():
                pass

            cached_function = Cache(underlying_function)

        :param func: The function to be cached.
        :param cache_provider: The cache provider, defaults to FileSystemCacheProvider
        """
        self._func = func
        if cache_provider is None:
            cache_provider = FileSystemCacheProvider()
        self._cache_provider = cache_provider

    def __call__(
        self, *args, force_cache: bool = False, force_run: bool = False, **kwargs
    ):
        """
        Method called when the cached function is called.

        ..
            @Cache
            def underlying_func():
                pass
            cached_func = Cache(underlying_func)

            underlying_func()
            cached_func()

        :param args: Arguments to the underlying function.
        :param force_cache: Attempt to retrieve cached results, raising
        ``KeyError`` if they do not exist
        :param force_run: Run the function, ignoring any cached values
        :param kwargs: Keyword arguments to the underlying function.
        :return: The (cached) result of the underlying function.
        """
        key = self._cache_provider.make_key(self._func, *args, **kwargs)

        try:
            if force_run:
                raise KeyError("cache ignored due to force_run")
            return self._cache_provider.get(key)
        except KeyError as ex:
            if force_cache:
                raise ex
            value = self._func(*args, **kwargs)  # execute the function, with arguments
            self._cache_provider.set(key, value)
            return value

    def __str__(self):
        """
        Creates a human-readable string of the cache and cached function.

        :return: A string representing the cached function.
        """
        return f"Cached function object: func: {self._func}, cache: {str(self._cache_provider)}"


def default_key_provider(func: Callable, *args, **kwargs) -> str:
    """
    Default cache key function. This uses cloudpickle to hash the function and all arguments.
    """
    return cloudpickle.dumps({"function": func, "args": args, "kwargs": kwargs})
