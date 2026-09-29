"""Zet de bindingen tussen workspaces in deze repo op de Dev-waarden uit .github/fabric-bindings.dev.json.

Een developer-workspace koppelt model, rapport, shortcuts en de defaults van Variable Libraries aan zijn eigen
workspaces (setup/NB_SETUP_DEVELOPER_WORKSPACES, mode bind). Die koppeling hoort niet op `dev`: git op `dev` bevat altijd de Dev-toestand
(ADR-011).

  --report meldt afwijkingen en faalt alleen bij problemen (de PR-check: de feature-branch blijft ongewijzigd, zodat
           de developer-workspace geïsoleerd blijft)
  --fix    bindingen omzetten naar Dev (de workflow draait dit na de merge op `dev` en commit het resultaat)
  --check  exit 1 als een binding afwijkt, of als een model/rapport/lakehouse met shortcuts niet in het bestand staat
  --root   map met de te controleren inhoud (standaard deze repo). De workflow draait het script en de bindingen uit
           `dev` en controleert daarmee de PR-branch, zodat een PR het script of de Dev-waarden niet zelf kan aanpassen.
"""
import glob, json, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = sys.argv[sys.argv.index("--root") + 1] if "--root" in sys.argv else HERE
SQL_DB = re.compile(r'Sql\.Database\("([^"]+)",\s*"([^"]+)"\)')
VAR_VALUE = r'("name":\s*"{}"[^}}]*?"value":\s*")([^"]*)(")'  # waarde van één variabele in variables.json


def items(kind):
    for d in glob.glob(os.path.join(ROOT, "**", f"*.{kind}"), recursive=True):
        if os.path.isfile(os.path.join(d, ".platform")):
            yield os.path.basename(d)[: -len(kind) - 1], d


def read(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def main():
    fix, report = "--fix" in sys.argv, "--report" in sys.argv
    b = json.load(open(os.path.join(HERE, ".github", "fabric-bindings.dev.json"), encoding="utf-8"))
    problems, changed = [], []

    for name, d in items("SemanticModel"):
        want = b.get("semanticModels", {}).get(name)
        for p in glob.glob(os.path.join(d, "**", "*.tmdl"), recursive=True):
            src = read(p)
            if not SQL_DB.search(src):
                continue
            if not want:
                problems.append(f"{name}: niet in fabric-bindings.dev.json (nieuw model? voeg de Dev-binding toe)")
                continue
            new = SQL_DB.sub(f'Sql.Database("{want["server"]}", "{want["database"]}")', src)
            if new != src:
                changed.append(os.path.relpath(p, ROOT))
                if fix: write(p, new)

    for name, d in items("Report"):
        p = os.path.join(d, "definition.pbir")
        pbir = json.loads(read(p))
        conn = pbir.get("datasetReference", {}).get("byConnection")
        if not conn:
            continue  # byPath: binding in dezelfde workspace, gaat vanzelf goed
        want = b.get("reports", {}).get(name)
        if not want:
            problems.append(f"{name}: niet in fabric-bindings.dev.json (nieuw rapport? voeg de Dev-binding toe)")
        elif conn.get("connectionString") != want["connectionString"]:
            changed.append(os.path.relpath(p, ROOT))
            if fix:  # alleen de waarde vervangen, zodat de opmaak van Fabric blijft staan
                old, new = (json.dumps(v, ensure_ascii=False)[1:-1] for v in (conn["connectionString"], want["connectionString"]))
                write(p, read(p).replace(old, new))

    for name, d in items("Lakehouse"):
        p = os.path.join(d, "shortcuts.metadata.json")
        if not os.path.isfile(p):
            continue
        sc = json.loads(read(p))
        onelake = [s["target"]["oneLake"] for s in sc if s.get("target", {}).get("type") == "OneLake"]
        if not onelake:
            continue
        want = b.get("lakehouseShortcuts", {}).get(name)
        if not want:
            problems.append(f"{name}: shortcuts, maar niet in fabric-bindings.dev.json")
        elif any((t["workspaceId"], t["itemId"]) != (want["workspaceId"], want["itemId"]) for t in onelake):
            changed.append(os.path.relpath(p, ROOT))
            if fix:  # alleen de ID's vervangen, zodat de opmaak van Fabric blijft staan
                src = read(p)
                for t in onelake:
                    src = src.replace(t["workspaceId"], want["workspaceId"]).replace(t["itemId"], want["itemId"])
                write(p, src)

    for name, d in items("VariableLibrary"):
        want = b.get("variableLibraries", {}).get(name)
        if not want:
            continue  # een library zonder bindingen tussen workspaces
        p = os.path.join(d, "variables.json")
        src = new = read(p)
        for var, value in want.items():
            pat = re.compile(VAR_VALUE.format(re.escape(var)))
            if not pat.search(new):
                problems.append(f"{name}: variabele {var} staat niet in variables.json")
                continue
            new = pat.sub(lambda m: m.group(1) + value + m.group(3), new, count=1)
        if new != src:
            changed.append(os.path.relpath(p, ROOT))
            if fix: write(p, new)

    for c in changed:
        print(("omgezet naar Dev: " if fix else "wijkt af van Dev (wordt na de merge teruggezet): " if report else "wijkt af van Dev: ") + c)
    for pr in problems:
        print("FOUT: " + pr)
    if problems or (changed and not fix and not report):
        sys.exit(1)
    if not changed:
        print("Alle bindingen staan op Dev.")


if __name__ == "__main__":
    main()
