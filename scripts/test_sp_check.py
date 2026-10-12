"""Check of the SP-secrets check in NB_SETUP_FMD (cell with the Key Vault secrets). No dependencies, no network.

    python3 scripts/test_sp_check.py

The setup creates the framework connections with key_vault.secrets.sql_sp_*, but gives workspace access only
to security.service_principal_id. Checked: a token for another principal, or a failed login, is a problem,
and only when the setup will create a framework connection itself.
"""

import ast
import base64
import json
import sys
from pathlib import Path

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent).resolve()
cells = {c.get("id"): "".join(c["source"]) for c in json.loads((REPO / "setup/NB_SETUP_FMD.ipynb").read_text(encoding="utf-8"))["cells"]}
tree = ast.parse(cells["f3c0961b"])
functions = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)], type_ignores=[])

SECRET, EXPECTED, OTHER = "s3cr3t-value", "e762ae59-6412-4f1a-84ec-ec964807d43a", "fdd7d4d8-2a7b-4c2e-9320-4e7dcdf096fa"
calls = []


class Response:
    def __init__(self, status, body):
        self.status_code, self.body = status, body

    def json(self):
        return self.body


def token_for(oid):
    claims = base64.urlsafe_b64encode(json.dumps({"oid": oid}).encode()).decode().rstrip("=")
    return Response(200, {"access_token": f"header.{claims}.signature"})


answer = token_for(EXPECTED)


def post(url, data, timeout):
    calls.append(data)
    return answer


manifest_sp = {"security.service_principal_id": EXPECTED}
scope = {
    "_requests": type("R", (), {"post": staticmethod(post)}),
    "principals": lambda *specs: [{"id": i, "type": t} for i, t in specs if i and str(i).replace("-", "").strip("0")],
    "optional": lambda path, default=None: manifest_sp.get(path, default),
    "connection_fabric_datapipelines_name": "CON_X_FABRIC_PIPELINES",
    "connection_fabric_notebooks_name": "CON_X_FABRIC_NOTEBOOKS",
    "connection_fabric_database_name": "CON_X_FABRIC_SQL",
    "fabric_sql_sp_tenant_id": "tenant", "fabric_sql_sp_client_id": "client", "fabric_sql_sp_secret": SECRET,
}
exec(compile(functions, "cell f3c0961b", "exec"), scope)
check = scope["framework_connections_problem"]
ALL = {"CON_X_FABRIC_PIPELINES", "CON_X_FABRIC_NOTEBOOKS", "CON_X_FABRIC_SQL"}

assert check(ALL - {"CON_X_FABRIC_SQL"}) is None, "same principal: no problem"

answer = token_for(OTHER)
problem = check(ALL - {"CON_X_FABRIC_SQL"})
assert problem and EXPECTED in problem and OTHER in problem, problem

answer = Response(401, {"error": "invalid_client", "error_description": "AADSTS7000215 " + SECRET})
problem = check(set())
assert problem and "invalid_client" in problem and SECRET not in problem, problem

calls.clear()
assert check(ALL) is None and not calls, "all connections exist: secrets are not used, no login"

manifest_sp["security.service_principal_id"] = "00000000-0000-0000-0000-000000000000"
assert check(set()) is None and not calls, "empty service_principal_id: reported by its own dry-run check"

print("OK: SP-secrets en service_principal_id worden vergeleken, alleen als de setup een connectie aanmaakt")
