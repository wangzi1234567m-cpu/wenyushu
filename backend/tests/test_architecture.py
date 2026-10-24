import ast
from pathlib import Path

ROOT = Path(__file__).parents[1] / "app"


def imports(path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, f"Use explicit imports for dependency checks: {path}"
            yield node.module or ""


def test_layer_boundaries():
    for path in ROOT.rglob("*.py"):
        relative = path.relative_to(ROOT)
        parts = relative.parts
        for module in imports(path):
            if "domain" in parts or "application" in parts:
                assert not module.startswith(("fastapi", "starlette", "sqlalchemy", "httpx")), path
                assert ".infrastructure" not in module and ".api" not in module, path
            if "api" in parts:
                assert not module.startswith(("sqlalchemy", "app.infrastructure")), path
                assert ".infrastructure" not in module and ".mock" not in module, path
            if parts[:1] == ("modules",):
                owner = parts[1]
                if module.startswith("app.modules."):
                    target = module.split(".")[2]
                    if target != owner:
                        assert ".application." in module, (path, module)
                    if owner in ("conversation", "discussion"):
                        assert target not in ("reading", "catalog", "handoff"), path
                assert module != "app.infrastructure.db.metadata", path


def test_only_api_client_uses_fetch():
    web = ROOT.parents[1] / "web" / "src"
    for path in web.rglob("*.tsx"):
        assert "fetch(" not in path.read_text(encoding="utf-8"), path
