"""
Contains classes for progress reporting.
"""
import email
from email.utils import formataddr
import smtplib
from abc import ABC, abstractmethod
from typing import Union, TextIO, Iterable, NamedTuple, Optional


class NotificationProvider(ABC):
    """
    Abstract base class for implementing a notification provider, allowing notifications to be
    raised to different locations. Generally, you should inherit from
    :class:`DefaultNotificationProvider` to avoid having to implement every method.
    """

    @abstractmethod
    def task_completed(self):
        """
        Executed when a task completes.
        """

    @abstractmethod
    def all_tasks_completed(self):
        """
        Executed when all tasks complete.
        """

    @abstractmethod
    def task_failure(self):
        """
        Executed when a task fails to execute.
        """


class DefaultNotificationProvider(NotificationProvider):
    """
    Default :class:`NotificationProvider` implementation that takes no actions when an event
    occurs. This is the class you should extend if you want to create your own custom
    notification provider.
    """

    def task_completed(self):
        pass

    def all_tasks_completed(self):
        pass

    def task_failure(self):
        pass


class ConsoleNotificationProvider(DefaultNotificationProvider):
    """
    Writes notification to the console (stdout).
    """

    def task_completed(self):
        print("Task completed")

    def all_tasks_completed(self):
        print("All tasks completed")

    def task_failure(self):
        print("Task failed")


class FileSystemNotificationProvider(DefaultNotificationProvider):
    """
    Writes notifications to a file.
    """

    def __init__(self, filepath: Union[TextIO, str] = None):
        """
        Creates a FileSystemNotificationProvider.

        :param filepath: the filepath to write notifications to, opened in append mode,
        or a file-like object. Defaults to 'logs.txt'.
        """
        self._filepath = filepath if isinstance(filepath, str) else "logs.txt"
        self._file = filepath if not isinstance(filepath, str) else None

    def _write(self, message: str):
        str_ = f"{message}\n"
        if self._file:
            self._file.write(str_)
        else:
            with open(self._filepath, "a") as file:
                file.write(str_)

    def task_completed(self):
        self._write("Task completed")

    def all_tasks_completed(self):
        self._write("All tasks completed")

    def task_failure(self):
        self._write("Task failed")


class SmtpConfiguration(NamedTuple):
    """SMTP server configuration options used by :class:`EmailNotificationProvider`."""

    host: str
    """ SMTP server host. """

    port: int
    """ SMTP server port. """

    username: Optional[str] = None
    """ Username to authenticate with. """

    password: Optional[str] = None
    """ Password to authenticate with. """

    require_tls: Optional[bool] = True
    """ Whether to require a TLS connection. Defaults to True. """


class EmailNotificationProvider(DefaultNotificationProvider):
    """
    Sends notifications via email. Requires an SMTP server to connect to.

    For example, to send notifications using a Gmail account::

        smtp_config = SmtpConfiguration(
            'smtp.gmail.com',
            587,
            username='sender@gmail.com',
            password='password'
        )

        provider = EmailNotificationProvider(
            smtp_config,
            "sender@gmail.com",
            ["recipient@gmail.com"]
        )
    """

    def __init__(
        self,
        smtp: Union[SmtpConfiguration, smtplib.SMTP],
        from_addr: str,
        to_addrs: Iterable[str],
    ):
        """
        Creates an EmailNotificationProvider.

        :param smtp: SMTP configuration or a smtplib.SMTP object
        :param from_addr: email address emails will be sent from
        :param to_addrs: email addresses emails will be sent to
        """
        self._smpt_config = (
            smtp
            if isinstance(smtp, SmtpConfiguration)
            else SmtpConfiguration("localhost", 0)
        )
        self._client = smtp if isinstance(smtp, smtplib.SMTP) else None
        self._from_addr = from_addr
        self._to_addrs = to_addrs

    @property
    def smpt(self):
        """This provider's SmtpConfiguration."""
        return self._smpt_config

    @property
    def from_addr(self):
        """Email address emails will be sent from."""
        return self._from_addr

    @property
    def to_addrs(self):
        """Email addresses emails will be sent to."""
        return self._to_addrs

    def _send_email(self, message: email.message.Message):
        if self._client:
            self._client.send_message(message)
        else:
            with smtplib.SMTP(self._smpt_config.host, self._smpt_config.port) as smtp:
                try:
                    smtp.starttls()
                except smtplib.SMTPNotSupportedError as error:
                    if self._smpt_config.require_tls:
                        raise error

                if (
                    self._smpt_config.username is not None
                    and self._smpt_config.password is not None
                ):
                    smtp.login(self._smpt_config.username, self._smpt_config.password)
                smtp.send_message(message)

    def create_message(self, subject: str, content: str) -> email.message.Message:
        """Creates an :class:`email.message.Message` with the given subject and content."""
        message = email.message.EmailMessage()
        message["From"] = formataddr(("Memento", self._from_addr))
        message["To"] = ",".join(self._to_addrs)
        message["Subject"] = subject
        message.set_content(
            content
        )  # TODO: Maybe support HTML messages with a plain text fallback
        return message

    def task_completed(self):
        message = self.create_message("[Memento] Task completed", "Task completed")
        self._send_email(message)

    def all_tasks_completed(self):
        message = self.create_message(
            "[Memento] All tasks completed", "All tasks completed"
        )
        self._send_email(message)

    def task_failure(self):
        message = self.create_message("[Memento] Task failed", "Task failed")
        self._send_email(message)
