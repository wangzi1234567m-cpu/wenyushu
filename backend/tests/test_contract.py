from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate

ROOT = Path(__file__).parents[2]
CONTRACT = yaml.safe_load((ROOT / "contracts/openapi.yaml").read_text(encoding="utf-8"))


def normalize(value):
    if isinstance(value, dict):
        return {
            k: normalize(v)
            for k, v in value.items()
            if k not in ("title", "description", "default")
        }
    if isinstance(value, list):
        return [normalize(v) for v in value]
    return value


def test_full_contract_and_p0_runtime(foundation):
    validate(CONTRACT)
    actual = foundation[0].openapi()
    assert set(actual["paths"]) == {
        "/api/v1/auth/anonymous-session",
        "/api/v1/health/live",
        "/api/v1/health/ready",
    }
    for path, methods in actual["paths"].items():
        for method, operation in methods.items():
            expected = CONTRACT["paths"][path.removeprefix("/api/v1")][method]
            assert operation["operationId"] == expected["operationId"]
            assert set(operation["responses"]) == set(expected["responses"])
            assert operation.get("security", []) == expected.get("security", [])
            assert normalize(operation.get("parameters", [])) == normalize(expected["parameters"])
            for status, response in operation["responses"].items():
                assert (
                    response["content"]["application/json"]["schema"]
                    == expected["responses"][status]["content"]["application/json"]["schema"]
                )
    for name in ("SessionCreated", "HealthStatus", "Ok", "Error", "ErrorEnvelope"):
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
