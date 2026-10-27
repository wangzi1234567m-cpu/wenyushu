from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate

ROOT = Path(__file__).parents[2]
CONTRACT = yaml.safe_load((ROOT / "contracts/openapi.yaml").read_text(encoding="utf-8"))


def normalize(value):
    if isinstance(value, dict):
        if "enum" in value and len(value["enum"]) == 1:
            value = {**value, "const": value["enum"][0]}
            value.pop("enum")
        return {
            k: normalize(v)
            for k, v in value.items()
            if k not in ("title", "description", "default")
        }
    if isinstance(value, list):
        return [normalize(v) for v in value]
    return value


def test_full_contract_and_implemented_runtime(foundation):
    validate(CONTRACT)
    actual = foundation[0].openapi()
    assert set(actual["paths"]) == {
        "/api/v1/auth/anonymous-session",
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/api/v1/topics",
        "/api/v1/conversations",
        "/api/v1/conversations/{conversation_id}",
        "/api/v1/conversations/{conversation_id}/messages",
        "/api/v1/questions/daily",
        "/api/v1/explorations",
        "/api/v1/explorations/{exploration_id}",
        "/api/v1/explorations/{exploration_id}/answers",
        "/api/v1/recommendations",
        "/api/v1/recommendations/{job_id}",
    }
    for path, methods in actual["paths"].items():
        for method, operation in methods.items():
            expected = CONTRACT["paths"][path.removeprefix("/api/v1")][method]
            assert operation["operationId"] == expected["operationId"]
            assert set(operation["responses"]) == set(expected["responses"])
            assert operation.get("security", []) == expected.get("security", [])
            assert sorted(
                normalize(operation.get("parameters", [])), key=lambda p: (p["in"], p["name"])
            ) == sorted(normalize(expected["parameters"]), key=lambda p: (p["in"], p["name"]))
            for status, response in operation["responses"].items():
                assert normalize(response["content"]) == normalize(
                    expected["responses"][status]["content"]
                )
    for name in (
        "ConversationCreate",
        "Conversation",
        "ConversationMessage",
        "ConversationMessagePage",
        "ConversationMessageCreate",
        "SessionCreated",
        "HealthStatus",
        "Ok",
        "Error",
        "ErrorEnvelope",
        "Topic",
        "Option",
        "QuestionStep",
        "DailyQuestion",
        "ExplorationCreate",
        "ExplorationAnswer",
        "ExplorationAnswerRecord",
        "ExplorationState",
        "RecommendationCreate",
        "VerifiedBook",
        "TaskError",
        "RecommendationJob",
    ):
        assert normalize(actual["components"]["schemas"][name]) == normalize(
            CONTRACT["components"]["schemas"][name]
        )


def test_response_payloads(client):
    for method, path, status, schema in [
        ("get", "/health/live", 200, "HealthStatus"),
        ("post", "/auth/anonymous-session", 201, "SessionCreated"),
        ("delete", "/auth/anonymous-session", 422, "ErrorEnvelope"),
    ]:
        response = getattr(client, method)("/api/v1" + path)
        assert response.status_code == status
        definition = {
            **CONTRACT["components"]["schemas"][schema],
            "components": CONTRACT["components"],
        }
        Draft202012Validator(definition, format_checker=FormatChecker()).validate(response.json())
