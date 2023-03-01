"""
MEMENTO is a Python library for running computationally expensive experiments.
"""

from memento.configurations import Config, Configurations, generate_configurations
from memento.memento import Memento
from memento.task_interface import FileSystemCheckpointing, Context, MemoryUsage, Result
from memento.notifications import (
    NotificationProvider,
    DefaultNotificationProvider,
    ConsoleNotificationProvider,
    FileSystemNotificationProvider,
    EmailNotificationProvider,
    SmtpConfiguration,
)
from memento.caching import (
    CacheProvider,
    MemoryCacheProvider,
    FileSystemCacheProvider,
    Cache,
    default_key_provider,
)
from memento.parallel import (
    TaskManager,
    delayed,
    TASK_PRIORITY_LOW,
    TASK_PRIORITY_MEDIUM,
    TASK_PRIORITY_HIGH,
)
from memento.exceptions import AggregateException, CacheMiss, CyclicDependency

__all__ = [
    "Memento",
    "Config",
    "Configurations",
    "generate_configurations",
    "FileSystemCheckpointing",
    "Context",
    "MemoryUsage",
    "Result",
    "default_key_provider",
    "NotificationProvider",
    "DefaultNotificationProvider",
    "ConsoleNotificationProvider",
    "FileSystemNotificationProvider",
    "EmailNotificationProvider",
    "SmtpConfiguration",
    "CacheProvider",
    "MemoryCacheProvider",
    "FileSystemCacheProvider",
    "Cache",
    "default_key_provider",
    "TaskManager",
    "delayed",
    "TASK_PRIORITY_LOW",
    "TASK_PRIORITY_MEDIUM",
    "TASK_PRIORITY_HIGH",
    "AggregateException",
    "CacheMiss",
    "CyclicDependency",
]

__version__ = "1.0.0"
