import os
import re
import sys
import time
import unittest
from typing import Any, List, TypedDict

from typing_extensions import NotRequired


class JsonTestResult(TypedDict):
    name: str
    time: NotRequired[int]


JsonTestResults = List[JsonTestResult]


class HealthcheckJsonTestResult(TypedDict):
    tests_passed: bool
    successes: JsonTestResults
    failures: JsonTestResults
    errors: JsonTestResults


class HealthcheckResult(unittest.TextTestResult):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__path_re = re.compile(r"^[\.\/\w]+\.(\w+\.\w+)$")
        self.__successes_json: JsonTestResults = []
        self.__failures_json: JsonTestResults = []
        self.__errors_json: JsonTestResults = []

    def _get_name(self, path: str) -> str:
        match = self.__path_re.match(path)
        return match.group(1) if match else "Unknown"

    def startTest(self, test: unittest.TestCase) -> None:
        self._start_time = time.time()
        super().startTest(test)

    def addSuccess(self, test: unittest.TestCase) -> None:
        elapsed = time.time() - self._start_time
        self.__successes_json.append(
            JsonTestResult(name=self._get_name(test.id()), time=round(1e6 * elapsed))
        )
        super().addSuccess(test)

    def addFailure(self, test: unittest.TestCase, err: Any) -> None:
        self.__failures_json.append(JsonTestResult(name=self._get_name(test.id())))
        super().addFailure(test, err)

    def addError(self, test: unittest.TestCase, err: Any) -> None:
        self.__errors_json.append(JsonTestResult(name=self._get_name(test.id())))
        super().addError(test, err)

    def get_successes_json(self) -> JsonTestResults:
        return self.__successes_json

    def get_failures_json(self) -> JsonTestResults:
        return self.__failures_json

    def get_errors_json(self) -> JsonTestResults:
        return self.__errors_json


class HealthcheckRunner(unittest.TextTestRunner):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(resultclass=HealthcheckResult, *args, **kwargs)

    def run(self, test) -> HealthcheckJsonTestResult:
        result: HealthcheckResult = super().run(test)  # type: ignore
        return HealthcheckJsonTestResult(
            tests_passed=result.wasSuccessful(),
            successes=result.get_successes_json(),
            failures=result.get_failures_json(),
            errors=result.get_errors_json(),
        )


def run_healthcheck() -> HealthcheckJsonTestResult:
    no_stream = open(os.devnull, "w")
    sys.stderr = no_stream

    try:
        loader = unittest.TestLoader()
        suite = loader.discover(start_dir=".", pattern="*test*.py")
        runner = HealthcheckRunner(verbosity=0)
        result = runner.run(suite)
    finally:
        sys.stderr = sys.__stderr__
        no_stream.close()

    return result