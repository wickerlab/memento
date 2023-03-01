import email
import smtplib
from email.utils import parseaddr
from io import StringIO
from typing import List
from unittest.mock import Mock

import pytest
from aiosmtpd import controller, handlers

from memento.notifications import (
    FileSystemNotificationProvider,
    EmailNotificationProvider,
    SmtpConfiguration,
)
from memento.parallel import TaskManager, delayed


class TestFileSystemNotificationProvider:
    def setup_method(self):
        self.file = StringIO()
        self.provider = FileSystemNotificationProvider(filepath=self.file)

    def test_writes_to_file_on_job_completed(self):
        self.provider.task_completed()
        assert self.file.getvalue() == "Task completed\n"

    def test_writes_to_file_on_all_tasks_completed(self):
        self.provider.all_tasks_completed()
        assert self.file.getvalue() == "All tasks completed\n"

    def test_writes_to_file_on_task_failure(self):
        self.provider.task_failure()
        assert self.file.getvalue() == "Task failed\n"


class Handler(handlers.Message):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._messages: List[email.message.Message] = []

    def handle_message(self, message):
        self._messages.append(message)
        print("<<< START MESSAGE >>>")
        print(message)
        print("<<< END MESSAGE >>>")

    @property
    def messages(self):
        """Returns the messages processed by this handler."""
        return self._messages


class DummySmtpServer:
    """Dummy SMTP server that saves emails to a list. Primarily for testing/debugging."""

    def __init__(self):
        self._messages = []
        self._handler = Handler()
        self._controller = controller.Controller(self._handler)

    def __enter__(self):
        self._controller.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._controller.stop()

    @property
    def messages(self):
        """List of messages in the order they were received by this server."""
        return self._handler.messages

    @property
    def host(self):
        """
        This server's hostname.
        """
        return self._controller.hostname

    @property
    def port(self):
        """
        Port this server is accessible from.
        """
        return self._controller.port

    def start(self):
        """Starts this server."""
        self._controller.start()

    def stop(self):
        """Stops this server."""
        self._controller.stop()


@pytest.mark.parametrize(
    "to_addrs",
    [
        ["receiver@test.com"],
        ["receiver1@test.com", "receiver2@test.com"],
    ],
)
class TestEmailNotificationProvider:
    def setup_provider(self, to_addrs: List[str]):
        self.messages: List[email.message.Message] = []
        self.client = Mock(spec_set=smtplib.SMTP)
        self.client.send_message.side_effect = self.messages.append
        self.from_addr = "sender@text.com"
        self.to_addrs = to_addrs
        self.provider = EmailNotificationProvider(
            self.client, self.from_addr, self.to_addrs
        )

    def _check_message(
        self, message: email.message.Message, subject: str, payload: str
    ):
        """
        Checks a message is being sent from and delivered to the right person as well as that it
        contains the correct information.
        """
        assert parseaddr(message["from"])[1] == self.from_addr
        assert message["to"] == ", ".join(self.to_addrs)
        assert message["subject"] == subject
        assert message.get_payload().strip() == payload

    def _check_messages(self, subject, payload):
        messages = self.messages
        assert len(messages) == 1
        self._check_message(messages[0], subject, payload)

    def test_sends_email_on_task_completed(self, to_addrs):
        self.setup_provider(to_addrs)
        self.provider.task_completed()
        subject = "[Memento] Task completed"
        payload = "Task completed"
        self._check_messages(subject, payload)

    def test_sends_email_on_all_tasks_completed(self, to_addrs):
        self.setup_provider(to_addrs)
        self.provider.all_tasks_completed()
        subject = "[Memento] All tasks completed"
        payload = "All tasks completed"
        self._check_messages(subject, payload)

    def test_sends_email_on_task_failure(self, to_addrs):
        self.setup_provider(to_addrs)
        self.provider.task_failure()
        subject = "[Memento] Task failed"
        payload = "Task failed"
        self._check_messages(subject, payload)


@pytest.mark.slow
class TestEmailNotificationProviderWithServer:
    """Tests to verify that emails are delivered to the SMTP server."""

    def setup_method(self):
        self.server = DummySmtpServer()
        self.server.start()

        self.from_addr = "sender@text.com"
        self.to_addrs = ["receiver@test.com"]

        smtp_config = SmtpConfiguration(
            self.server.host, self.server.port, require_tls=False
        )

        self.provider = EmailNotificationProvider(
            smtp_config, self.from_addr, self.to_addrs
        )

    def teardown_method(self):
        self.server.stop()

    def test_sends_email_to_server_on_task_completed(self):
        self.provider.task_completed()
        assert len(self.server.messages) == 1

    def test_sends_email_to_server_on_all_tasks_completed(self):
        self.provider.all_tasks_completed()
        assert len(self.server.messages) == 1

    def test_sends_email_to_server_on_task_failure(self):
        self.provider.task_failure()
        assert len(self.server.messages) == 1

    def test_sends_emails_in_parallel(self):
        manager = TaskManager(
            notification_provider=self.provider, notify_on_complete=True
        )
        manager.add_task(delayed(lambda x: print(x))("Hello World!"))
        manager.run()
        assert len(self.server.messages) == 2
