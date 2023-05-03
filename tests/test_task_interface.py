import time
from sqlite3 import Connection
from unittest.mock import Mock
import pytest
import os
import tempfile
import cloudpickle
from memento.task_interface import Context, FileSystemCheckpointing




def constant_key_provider(
    *args, **kwargs
):  # Necessary to ensure that mocks are not pickled
    return "key"


def arbitrary_expensive_thing(x):
    return x


def arbitrary_expensive_thing2(x):
    return x + 1


class TestContext:
    class TestRecord:
        def test_record_records_single_value(self):
            context = Context("key", FileSystemCheckpointing())
            context.record({"name": 1.0})
            context.record({"name": 2.0})

            metrics = context.collect_metrics()

            assert metrics.__contains__("name")

            expected_y_values = [1.0, 2.0]
            actual_y_values = list(metrics["name"]["y"])

            assert expected_y_values == actual_y_values

        def test_record_records_multiple_values_at_same_timestamp(self):
            context = Context("key", FileSystemCheckpointing())
            context.record(value_dict={"name1": 1.0, "name2": 2.0})

            metrics = context.collect_metrics()

            assert metrics.__contains__("name1")
            assert metrics.__contains__("name2")

            expected_y_values_1 = [1.0]
            actual_y_values_1 = list(metrics["name1"]["y"])
            expected_y_values_2 = [2.0]
            actual_y_values_2 = list(metrics["name2"]["y"])
            x_values_1 = list(metrics["name1"]["x"])
            x_values_2 = list(metrics["name2"]["x"])

            assert expected_y_values_1 == actual_y_values_1
            assert expected_y_values_2 == actual_y_values_2
            assert x_values_1 == x_values_2

        def test_record_records_multiple_values_at_different_timestamps(self):
            context = Context("key", FileSystemCheckpointing())
            context.record({"name1": 1.0})
            time.sleep(0.001)
            context.record({"name2": 2.0})

            metrics = context.collect_metrics()

            assert metrics.__contains__("name1")
            assert metrics.__contains__("name2")

            expected_y_values_1 = [1.0]
            actual_y_values_1 = list(metrics["name1"]["y"])
            expected_y_values_2 = [2.0]
            actual_y_values_2 = list(metrics["name2"]["y"])
            x_values_1 = list(metrics["name1"]["x"])
            x_values_2 = list(metrics["name2"]["x"])

            assert expected_y_values_1 == actual_y_values_1
            assert expected_y_values_2 == actual_y_values_2
            assert x_values_1 != x_values_2

        def test_record_records_x_and_y_when_given_a_tuple(self):
            context = Context("key", FileSystemCheckpointing())
            context.record({"name1": (1.0, 2.0)})

            metrics = context.collect_metrics()

            assert metrics.__contains__("name1")

            expected_y_values = [2.0]
            actual_y_values = list(metrics["name1"]["y"])
            expected_x_values = [1.0]
            actual_x_values = list(metrics["name1"]["x"])

            assert expected_y_values == actual_y_values
            assert expected_x_values == actual_x_values

    class TestCheckpoint:
        def setup_method(self, method):
            file = tempfile.NamedTemporaryFile(
                suffix="_memento.checkpoint", delete=False
            )
            self._filepath = os.path.abspath(file.name)
            file.close()

        def teardown_method(self, method):
            os.unlink(self._filepath)

        def test_file_system_checkpoint_provider_checkpoint_works(self):
            checkpoint_provider = FileSystemCheckpointing()
            intermediate = arbitrary_expensive_thing(1)
            context = Context("key", checkpoint_provider)

            context.checkpoint(intermediate)

            assert checkpoint_provider.contains("key")

        def test_file_system_checkpoint_provider_restore_works(self):
            checkpoint_provider = FileSystemCheckpointing()
            intermediate = arbitrary_expensive_thing(1)
            context = Context("key", checkpoint_provider)

            context.checkpoint(intermediate)
            value = context.restore()

            assert value == 1

        def test_file_system_checkpoint_provider_creates_correct_keys(self):
            def function(*args):
                return args

            context_key = "key"
            arguments = ("test1", "test2", 123, True)
            keyword_arguments = {
                "key1": "value1",
                "key2": "value2",
                "key3": 321,
                "key4": False,
                "context_key": context_key,
            }
            expected = cloudpickle.dumps(
                {
                    "function": function,
                    "args": arguments,
                    "kwargs": keyword_arguments,
                }
            )

            connection = Mock(spec_set=Connection)
            checkpoint_provider = FileSystemCheckpointing(connection=connection)
            actual = checkpoint_provider.make_key(
                function, *arguments, **keyword_arguments
            )

            assert expected == actual

        def test_file_system_checkpoint_provider_get_raises_key_error_when_key_not_in_database(
            self,
        ):
            connection = Mock(spec_set=Connection)
            connection.execute().fetchall.return_value = None
            checkpoint_provider = FileSystemCheckpointing(connection=connection)

            with pytest.raises(KeyError) as error_info:
                checkpoint_provider.get("not_in_checkpoint")
