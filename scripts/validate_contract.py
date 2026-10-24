"""Validate WenyuShu OpenAPI 3.1 structure without requiring a running server.

Install with: pip install pyyaml jsonschema
Then: python scripts/validate_contract.py
CI additionally compares routes and payloads to FastAPI's generated /openapi.json.
"""
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

root=Path(__file__).resolve().parents[1]
file=root/'contracts/openapi.yaml'
api=yaml.safe_load(file.read_text(encoding='utf-8'))
assert api['openapi']=='3.1.0'
schemas=api['components']['schemas']
for schema in schemas.values():
    Draft202012Validator.check_schema(schema)
refs=[]
def collect(value):
    if isinstance(value,dict):
        if '$ref' in value: refs.append(value['$ref'])
        for nested in value.values(): collect(nested)
    elif isinstance(value,list):
        for nested in value:collect(nested)
collect(api)
assert all(ref.startswith('#/components/schemas/') and ref.removeprefix('#/components/schemas/') in schemas for ref in refs)
ops=set()
for path, methods in api['paths'].items():
    assert path.startswith('/')
    for method, spec in methods.items():
        assert method in {'get','post','put','patch','delete'}
        assert spec['operationId'] not in ops
        assert spec['responses']
        ops.add(spec['operationId'])
assert len(ops)>=20
print(f'PASS: OpenAPI {len(ops)} operations; {len(schemas)} schemas; {len(refs)} resolved references')
