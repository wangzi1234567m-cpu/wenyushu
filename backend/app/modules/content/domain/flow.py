from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FlowOption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=96)
    label: str = Field(min_length=1, max_length=100)
    description: str | None = None
    next_step_id: str | None = None
    topics: list[str] = Field(default_factory=list, max_length=3)
    focus: str = Field(default="", max_length=70)
    genre: str | None = None
    style: list[str] = Field(default_factory=list)


class FlowStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    prompt: str
    optional: bool = False
    multiple: bool = False
    source_url: str | None = None
    options: list[FlowOption] = Field(min_length=2, max_length=8)


class QuestionFlow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    first_step_id: str
    fallback: bool = False
    steps: dict[str, FlowStep]

    @model_validator(mode="after")
    def valid_graph(self):
        def walk(key, visited):
            if key in visited or key not in self.steps:
                raise ValueError("Invalid step graph")
            step = self.steps[key]
            if step.id != key or len({o.id for o in step.options}) != len(step.options):
                raise ValueError("Step/option identities must be unique")
            if step.optional and not any(o.id == "skip" for o in step.options):
                raise ValueError("Optional steps require a server-defined skip option")
            if step.multiple and len({o.next_step_id for o in step.options}) != 1:
                raise ValueError("Multiple selections must share a successor")
            path = visited | {key}
            if len(path) > 3:
                raise ValueError("Daily exploration must fit within three steps")
            for option in step.options:
                if option.next_step_id:
                    walk(option.next_step_id, path)
                elif len(path) < 2:
                    raise ValueError("Daily exploration needs at least two steps")

        walk(self.first_step_id, set())
        return self

    def public_step(self, key: str) -> dict:
        step = self.steps[key]
        return {
            "id": step.id,
            "prompt": step.prompt,
            "optional": step.optional,
            "multiple": step.multiple,
            **({"source_url": step.source_url} if step.source_url else {}),
            "options": [
                {
                    "id": o.id,
                    "label": o.label,
                    **({"description": o.description} if o.description else {}),
                }
                for o in step.options
            ],
        }
