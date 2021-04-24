from __future__ import annotations
from abc import ABC, abstractmethod, abstractproperty
from dataclasses import dataclass
from enum import Enum, auto
import functools
import json
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union

from bs4 import BeautifulSoup  # type: ignore
import requests


RunState = Dict[Any, Any]
RunError = NamedTuple("RunError", [("case", str), ("step", int), ("message", Any)])
RunResult = Union[RunError, RunState]


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
            return _lookup(p[1:], data[p[0]])

    return _lookup(path.split("."), dict_)


@dataclass
class Case:
    name: str
    tags: List[str]
    steps: List[Step]

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
                    "title": soup.title.get_text(),
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
        actual = lookup_path(self.actual, state)
        if actual == self.expected:
            return {**state, index: {"success": True}}
        else:
            return RunError(
                case=self.tag(),
                step=index,
                message={
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
            return {
                **state,
                index: {
                    "success": False,
                    "content": self.content,
                    "container": container,
                },
            }


if __name__ == "__main__":
    import doctest

    doctest.testmod()
