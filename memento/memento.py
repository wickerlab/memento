"""
Contains `Memento`, the main entry point of MEMENTO.
"""

import functools
import logging
import os
from datetime import datetime
from typing import Callable, List, Optional, Dict, Any, cast
from networkx import DiGraph, is_directed_acyclic_graph, topological_sort  # type: ignore

import cloudpickle

from memento.notifications import NotificationProvider, DefaultNotificationProvider
from memento.parallel import TaskManager, delayed
from memento.caching import FileSystemCacheProvider, CacheProvider
from memento.configurations import generate_configurations, Config
from memento.task_interface import Context, Result, FileSystemCheckpointing
from memento.exceptions import CacheMiss, CyclicDependency

logger = logging.getLogger(__name__)


class Memento:
    """
    The main class of MEMENTO. This is the 'front end' of MEMENTO with which you can run a
    configuration matrix and retrieve results from your experiments.
    """

    def __init__(
        self, func: Callable, notification_provider: NotificationProvider = None, num_workers: int = None
    ):
        """
        :param func: Your experiment code. This will be called with an experiment configuration.
        :param notification_provider: Notification provider to use. If not specified, no
            notifications will be emitted.
        """
        self.func = func
        self._notification_provider = (
            notification_provider or DefaultNotificationProvider()
        )
        self._matrices: List[dict] = []
        self._workers = num_workers

    def add_matrix(self, matrix: dict):
        """
        Adds a configuration matrix.

        :param matrix: A configuration matrix
        """
        self._matrices.append(matrix)

    def _get_execution_order(self):
        # Construct graph representation of matrices

        graph_edges = []

        for matrix in self._matrices:
            for dependency in matrix["dependencies"]:
                graph_edges.append(tuple([matrix["id"], dependency]))

        graph = DiGraph()
        graph.add_edges_from(graph_edges)
        graph.add_nodes_from(matrix["id"] for matrix in self._matrices)

        # Validate graph

        if not is_directed_acyclic_graph(graph):
            raise CyclicDependency()

        # Get execution order via a topological sort
        id_matrix_map = {matrix["id"]: matrix for matrix in self._matrices}
        matrices = [id_matrix_map[id_] for id_ in list(topological_sort(graph))[::-1]]
        return matrices

    def run_all(self, **kwargs) -> Optional[Dict[Any, Optional[List[Result]]]]:
        """
        Runs this object's configuration matrices and returns their results.

        :param kwargs: keyword arguments to Memento.run
        """
        matrices = self._get_execution_order()

        n_matrices = len(matrices)

        results: Dict[Any, Optional[List[Result]]] = {
            matrix["id"]: None for matrix in matrices
        }

        # Run each matrix
        for i in range(n_matrices):
            matrix = matrices[i]

            if kwargs.get("dry_run"):
                configs = generate_configurations(matrix)

                logger.info("Running configurations for matrix '%s':", matrix["id"])
                for config in configs:
                    logger.info("  %s", config)

                if i == n_matrices - 1:
                    logger.info("Exiting due to dry run")
                    return None

                inners = list(configs)
            else:
                results[matrix["id"]] = self.run(
                    matrix, **kwargs, notify_on_complete=False
                )

                if i == n_matrices - 1:
                    break

                inners = [result.inner for result in cast(List, results[matrix["id"]])]

            # Update all matrices that depend on the matrix that was just run
            for mat in matrices[i + 1 :]:
                if matrix["id"] in mat["dependencies"]:
                    mat["parameters"][str(matrix["id"])] = inners

        self._notification_provider.all_tasks_completed()

        return results

    def run(  # pylint: disable=too-many-arguments, too-many-locals
        self,
        matrix: dict,
        dry_run: bool = False,
        force_run: bool = False,
        force_cache: bool = False,
        cache_path: str = None,
        notify_on_complete: bool = True,
    ) -> Optional[List[Result]]:
        """
        Run a configuration matrix and return it's results.

        :param matrix: A configuration matrix
        :param dry_run: Do not actually run experiments, just log what would be run
        :param force_run: Ignore the cache and re-run all experiments
        :param force_cache: Raise ``exceptions.CacheMiss`` if an experiment is not found in the
            cache
        :param cache_path: Path to save results. This defaults to the current working directory and
            can also be specified using ``MEMENTO_CACHE_PATH``.
        :param notify_on_complete: If true, a notification will be triggered when all tasks have
            been run.
        :returns: A list of results from your experiments.
        """

        configs = generate_configurations(matrix)

        logger.info("Running configurations:")
        for config in configs:
            logger.info("  %s", config)

        if dry_run:
            logger.info("Exiting due to dry run")
            return None

        cache_provider = FileSystemCacheProvider(
            filepath=(
                cache_path
                or os.environ.get("MEMENTO_CACHE_PATH", None)
                or "memento.sqlite"
            ),
            key_provider=_key_provider,
        )

        checkpoint_provider = FileSystemCheckpointing(
            filepath=(cache_path or "memento.sqlite"),
            key=_key_provider,
        )
        manager = TaskManager(
            workers=self._workers,
            notification_provider=self._notification_provider,
            notify_on_complete=notify_on_complete
        )

        # Run tasks for which we have no cached result
        ran = []
        for config in configs:
            key = _key_provider(self.func, config)
            if not cache_provider.contains(key) or force_run:
                if force_cache:
                    raise CacheMiss(config)
                context = Context(key, checkpoint_provider)
                manager.add_task(
                    delayed(_wrapper(self.func))(context, config, cache_provider)
                )
                ran.append(config)

        manager.run()

        results = [
            cache_provider.get(_key_provider(self.func, config)) for config in configs
        ]

        for config in configs:
            checkpoint_provider.remove(_key_provider(self.func, config))

        for result in results:
            if result.config in ran:
                result.was_cached = False

        logger.info(
            "%s/%s results retrieved from cache",
            len(configs) - len(ran),
            len(configs),
        )

        return results


def _wrapper(func: Callable) -> Callable:
    """
    Wrapper which runs in the task thread. This is responsible for collecting performance metrics
    and writing to the cache.
    """

    @functools.wraps(func)
    def inner(
        context: Context, config: Config, cache_provider: CacheProvider
    ) -> Result:
        start_time = datetime.now()

        inner = func(context, config)

        runtime = datetime.now() - start_time

        result = Result(
            config,
            inner,
            metrics=context.collect_metrics(),
            start_time=start_time,
            runtime=runtime,
            cpu_time=None,
            memory=None,
            was_cached=True,
        )
        cache_provider.set(context.key, result)
        context.checkpoint(result)
        return result

    return inner


def _key_provider(func: Callable, config: Config):
    # The default behaviour caches on all arguments, including the config object.
    return cloudpickle.dumps({"function": func.__name__, "args": [config]})
