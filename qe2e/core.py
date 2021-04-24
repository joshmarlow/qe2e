from __future__ import annotations
from abc import ABC, abstractmethod, abstractproperty
import argparse
from dataclasses import dataclass
from enum import Enum, auto
import glob
import functools
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union

from bs4 import BeautifulSoup  # type: ignore
import requests


@dataclass
class RunError:
    case: str
    step: int
    details: Optional[Any] = None


RunState = Dict[Any, Any]
RunResult = Union[RunError, RunState]


def display_results(result: RunResult) -> Tuple[bool, str]:
    if isinstance(result, RunError):
        return (
            False,
            f"FAILED - Error in step {result.step} ({result.case}) - {result.details}",
        )
    else:
        return (True, "PASSED")


class LookupError(Exception):
    path: str

    def __init__(self, path, *args, **kwargs):
        self.path = path
        super().__init__(*args, **kwargs)

    def __str__(self) -> str:
        return f"Could not find data at path '{self.path}'"


def lookup_path(path: str, dict_: Union[Any, Dict[str, Any]]) -> Any:
    """
    Recursively traverse a potentially nested dictionary
    using the '.' separated path.

    >>> lookup_path("k0.k1.k2", {"k0": {"k1": {"k2": 42}}})
    42
    """

    def _lookup(p: List[str], data: Union[Any, Dict[str, Any]]) -> Any:
        if not p:
            return data
        else:
            try:
                return _lookup(p[1:], data[p[0]])
            except KeyError:
                raise LookupError(p[0])

    return _lookup(path.split("."), dict_)


@dataclass
class Case:
    name: str
    tags: List[str]
    steps: List[Step]

    @staticmethod
    def from_file(path: str) -> Case:
        with open(path, "r") as fin:
            return Case.from_dict(json.loads(fin.read()))

    @staticmethod
    def from_dict(dict_: Dict[Any, Any]) -> Case:
        name = dict_["name"]
        tags = dict_.get("tags", [])
        steps = dict_.get("steps", [])

        return Case(
            name=name,
            tags=tags,
            steps=list(map(Step.from_dict, steps)),
        )

    def evaluate(self, state_opt: Optional[RunState] = None) -> RunResult:
        state: RunResult = state_opt or dict()

        def reduce_step(acc: RunResult, indexed_step: Tuple[int, Step]) -> RunResult:
            if isinstance(acc, RunError):
                return acc
            else:
                (index, step) = indexed_step
                return step.evaluate(index, acc)

        return functools.reduce(reduce_step, enumerate(self.steps), state)


class Step(ABC):
    @classmethod
    @abstractmethod
    def tag(cls) -> str:
        pass

    @abstractmethod
    def evaluate(self, index: int, state: RunState) -> RunResult:
        pass

    @staticmethod
    def subclass_dict() -> Dict[str, Any]:
        return {cls.tag(): cls for cls in Step.__subclasses__()}

    @classmethod
    @abstractmethod
    def from_dict(cls, dict_: Dict[Any, Any]) -> Step:
        type_ = dict_.pop("type", None)
        subclass_dict = Step.subclass_dict()
        if type_ in subclass_dict:
            return subclass_dict[type_].from_dict(dict_)
        else:
            raise Exception(f"Unknown step type - {type_}")


@dataclass
class Exec(Step):
    command: str

    @classmethod
    def tag(cls) -> str:
        return "exec"

    @classmethod
    def from_dict(cls, dict_: Dict[Any, Any]) -> Step:
        return cls(**dict_)

    def evaluate(self, index: int, state: RunState) -> RunResult:
        try:
            subprocess.call(self.command.split(), check=True)
        except subprocess.CalledProcessError as e:
            return RunError(
                case=self.tag(),
                step=index,
                details=e,
            )
        finally:
            return {
                **state,
                index: {"success": True},
            }


@dataclass
class GetUrl(Step):
    response_name: str
    url: str

    @classmethod
    def tag(cls) -> str:
        return "get_url"

    @classmethod
    def from_dict(cls, dict_: Dict[Any, Any]) -> Step:
        return cls(**dict_)

    def evaluate(self, index: int, state: RunState) -> RunResult:
        response = requests.get(self.url)
        soup = BeautifulSoup(response.content, "html.parser")
        return {
            **state,
            index: {"success": True},
            self.response_name: {
                "status_code": response.status_code,
                "html": {
                    "title": soup.title.get_text() if soup.title else None,
                    "content": soup.get_text(),
                },
            },
        }


@dataclass
class PostUrl(Step):
    body: Any
    response_name: str
    url: str

    @classmethod
    def tag(cls) -> str:
        return "post_url"

    @classmethod
    def from_dict(cls, dict_: Dict[Any, Any]) -> Step:
        return cls(**dict_)

    def evaluate(self, index: int, state: RunState) -> RunResult:
        response = requests.post(self.url, self.body)
        soup = BeautifulSoup(response.content, "html.parser")
        return {
            **state,
            index: {"success": True},
            self.response_name: {
                "status_code": response.status_code,
                "html": {
                    "title": soup.title,
                    "content": soup.get_text(),
                },
            },
        }


@dataclass
class PatchUrl(Step):
    body: Any
    response_name: str
    url: str

    @classmethod
    def tag(cls) -> str:
        return "patch_url"

    @classmethod
    def from_dict(cls, dict_: Dict[Any, Any]) -> Step:
        return cls(**dict_)

    def evaluate(self, index: int, state: RunState) -> RunResult:
        response = requests.patch(self.url, self.body)
        soup = BeautifulSoup(response.content, "html.parser")
        return {
            **state,
            index: {"success": True},
            self.response_name: {
                "status_code": response.status_code,
                "html": {
                    "title": soup.title,
                    "content": soup.get_text(),
                },
            },
        }


@dataclass
class AssertEq(Step):
    actual: str
    expected: Any

    @classmethod
    def tag(cls) -> str:
        return "assert_eq"

    @classmethod
    def from_dict(cls, dict_: Dict[Any, Any]) -> Step:
        return cls(**dict_)

    def evaluate(self, index: int, state: RunState) -> RunResult:
        try:
            actual = lookup_path(self.actual, state)
        except LookupError as e:
            return RunError(
                case=self.tag(),
                step=index,
                details=f"Could not find data at path '{self.actual}'",
            )
        if actual == self.expected:
            return {**state, index: {"success": True}}
        else:
            return RunError(
                case=self.tag(),
                step=index,
                details={
                    "expected": self.expected,
                    "actual": actual,
                },
            )


@dataclass
class AssertContains(Step):
    container: str
    content: str

    @classmethod
    def tag(cls) -> str:
        return "assert_contains"

    @classmethod
    def from_dict(cls, dict_: Dict[Any, Any]) -> Step:
        return cls(**dict_)

    def evaluate(self, index: int, state: RunState) -> RunResult:
        container = lookup_path(self.container, state)
        if self.content in container:
            return {**state, index: {"success": True}}
        else:
            return RunError(
                case=self.tag(),
                step=index,
                details={
                    "content": self.content,
                    "container": container,
                },
            )


def main():
    parser = argparse.ArgumentParser(description="Runner for Quick End 2 End Tests")
    parser.add_argument("test_path", type=str, help="Path to test file")
    args = parser.parse_args()

    if os.path.isdir(args.test_path):
        glob_pattern = f"{args.test_path}/*.e2e.json"
        files = glob.glob(glob_pattern, recursive=True)
        cases = list(map(lambda path: (path, Case.from_file), files))
    else:
        cases = [(args.test_path, Case.from_file(args.test_path))]

    for (path, case) in cases:
        (success, results) = display_results(case)
        print(f"{path} - {results}")


if __name__ == "__main__":
    main()
