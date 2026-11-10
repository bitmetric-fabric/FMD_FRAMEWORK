"""Check of LoadGroup, SourceColumns and SourceFilter per table in the registration editor. No dependencies, no network.

    python3 scripts/test_registration_editor.py

Two parts:
  1. The pure functions of NB_FMD_REGISTRATION_FUNCTIONS (state, payload, validation, bulk, overview, export) and
     ColumnPicker, run with a minimal stand-in for ipywidgets (it also drops the value when the options are set,
     as ipywidgets does, which is what the picker's guard is for).
  2. A static check of the SQL side: the three views, the procedure and the table agree with the notebook.
The SQL itself is run by hand against SQL Server (see ADR-020); this script does not run SQL.
"""

import contextlib
import copy
import hashlib
import html
import io
import json
import re
import sys
import traceback
import types
from pathlib import Path

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent).resolve()
NOTEBOOK = (REPO / "src/NB_FMD_REGISTRATION_FUNCTIONS.Notebook/notebook-content.py").read_text(encoding="utf-8")
SQL = REPO / "src/Config_Database"

failures = 0


def check(ok, text):
    global failures
    print(("  ok     " if ok else "  FOUT   ") + text)
    failures += 0 if ok else 1


def cell_with(marker):
    cells = re.split(r"^# CELL \*+\n", NOTEBOOK, flags=re.M)[1:]
    found = [re.split(r"^# METADATA \*+", c, flags=re.M)[0] for c in cells if marker in c]
    assert len(found) == 1, f"{marker}: {len(found)} cells"
    return "\n".join(l for l in found[0].split("\n") if not l.startswith("%"))


# ---- a stand-in for the part of ipywidgets that ColumnPicker uses -----------------------------------
class Layout:
    def __init__(self, **kw):
        self.display = ""  # ipywidgets: the default
        self.__dict__.update(kw)


class FakeWidget:
    def __init__(self, *args, **kw):
        object.__setattr__(self, "_obs", [])
        object.__setattr__(self, "_click", None)
        object.__setattr__(self, "options", ())
        object.__setattr__(self, "value", args[0] if args and isinstance(args[0], str) else ("" if kw.get("placeholder") is not None else ()))
        for k, v in kw.items():
            object.__setattr__(self, k, v)

    def observe(self, fn, names=None):
        self._obs.append(fn)

    def on_click(self, fn):
        object.__setattr__(self, "_click", fn)

    def click(self):
        self._click(None)

    def __setattr__(self, name, new):
        old = self.__dict__.get(name)
        object.__setattr__(self, name, new)
        if name == "options":  # ipywidgets: new options reset the selection
            self.value = ()
        elif name == "value" and old != new:
            for fn in list(self._obs):
                fn({"new": new, "old": old, "name": "value"})


w = types.SimpleNamespace(HTML=FakeWidget, Text=FakeWidget, SelectMultiple=FakeWidget, Button=FakeWidget, Dropdown=FakeWidget, Checkbox=FakeWidget, Combobox=FakeWidget,
                          ToggleButtons=FakeWidget,
                          HBox=lambda children, layout=None, **kw: FakeWidget(children=children, layout=layout or Layout()),
                          VBox=lambda children, layout=None, **kw: FakeWidget(children=children, layout=layout or Layout()),
                          Layout=Layout)

scope = {"hashlib": hashlib, "json": json, "re": re, "html": html, "copy": copy, "io": io, "contextlib": contextlib, "traceback": traceback, "w": w}
exec(compile(cell_with("def build_state"), "registration logic", "exec"), scope)
exec(compile(cell_with("class ColumnPicker"), "registration ui", "exec"), scope)
exec(compile(cell_with("def plan_copy"), "registration copy", "exec"), scope)
exec(compile(cell_with("class RegistrationUI"), "registration screen", "exec"), scope)

# ---- state, payload, validation -----------------------------------------------------------------------
print("=== logica ===")
sources_rows = [{"ConnectionName": "CON_X", "DataSourceName": "ERPDB", "Namespace": "erp", "DataSourceType": "ASQL_01", "LoadGroup": "nacht"}]


def row(name, **kw):
    base = {"ConnectionName": "CON_X", "DataSourceName": "ERPDB", "DataSourceType": "ASQL_01", "SourceSchema": "dbo", "SourceName": name,
            "FileName": f"dbo_{name}", "FileType": "parquet", "IsIncremental": 0, "IsIncrementalColumn": None, "IsActive": 1,
            "CustomNotebookName": None, "TargetSchema": "dbo", "TargetName": name, "PrimaryKeys": "ID", "BronzeRules": None, "SilverRules": None,
            "IsHistorized": 0, "EntityLoadGroup": None, "SourceColumns": None, "SourceFilter": None, "Watermark": None}
    return {**base, **kw}


state = scope["build_state"]("TEST", "D", "WS", sources_rows, [row("Orders", EntityLoadGroup="dag", SourceColumns="ID,Amount", SourceFilter="Amount > 0", Watermark="2024-06-01"), row("Customers")])
original = copy.deepcopy(state)
orders, customers = state["entities"]
check(orders["LoadGroup"] == "dag" and orders["SourceColumns"] == "ID,Amount" and orders["SourceFilter"] == "Amount > 0", "build_state: leest de drie velden")
check(customers["LoadGroup"] == "" and customers["SourceColumns"] == "" and customers["SourceFilter"] == "", "build_state: leeg veld wordt een lege tekst, geen None")
check(orders["Watermark"] == "2024-06-01" and "Watermark" not in scope["ENTITY_FIELDS"], "build_state: watermark erbij, maar geen veld dat een wijziging oplevert")
check(scope["entities_to_register"](state, original) == [], "ongewijzigde tabellen: niets te registreren")

customers.update(LoadGroup="wekelijks", SourceColumns="ID, Name", SourceFilter="Name <> ''")
check(sorted(scope["changed_fields"](customers, original["entities"][1])) == ["LoadGroup", "SourceColumns", "SourceFilter"], "changed_fields noemt de drie velden")
sources, entities = scope["build_payload"](state, original)
check([e["SourceName"] for e in entities] == ["Customers"], "alleen de gewijzigde tabel gaat mee")
check(entities[0]["LoadGroup"] == "wekelijks" and entities[0]["SourceColumns"] == "ID, Name" and entities[0]["SourceFilter"] == "Name <> ''", "payload: de drie velden")
state["entities"][0].update(LoadGroup="", SourceColumns="", SourceFilter="", IsActive=0)
_, entities = scope["build_payload"](state, original)
orders_item = next(e for e in entities if e["SourceName"] == "Orders")
check(not any(k in orders_item for k in ("LoadGroup", "SourceColumns", "SourceFilter")), "payload: een leeg veld blijft weg (de procedure maakt het leeg)")


def problems(e_updates, source_type="ASQL_01", discovered=None, columns=None, types=None):
    s = scope["build_state"]("TEST", "D", "WS", [{**sources_rows[0], "DataSourceType": source_type}], [row("Orders", DataSourceType=source_type)])
    o = copy.deepcopy(s)
    s["entities"][0].update(e_updates)
    found = {"ERP": {("dbo", "Orders"): {"Columns": [{"Name": c, "Type": (types or {}).get(c, "int")} for c in columns], "PrimaryKeys": "ID"}}} if columns else {}
    return [(p["field"], p["level"]) for p in scope["validate_state"](s, o, found)]


check(("PrimaryKeys", "error") in problems({"SourceColumns": "Amount"}), "validate: PrimaryKeys moet in SourceColumns staan")
check(("PrimaryKeys", "error") not in problems({"SourceColumns": "id, Amount"}), "validate: spaties en hoofdletters (niet-Snowflake) tellen niet")
check(("IsIncrementalColumn", "error") in problems({"SourceColumns": "ID", "IsIncremental": 1, "IsIncrementalColumn": "ModifiedAt"}), "validate: watermarkkolom moet in SourceColumns staan")
check(("SourceFilter", "error") in problems({"SourceFilter": "1=1; DROP TABLE x"}), "validate: geen puntkomma in het filter")
check(("SourceFilter", "warning") in problems({"SourceFilter": "Amount > 0"}), "validate: een filter geeft een waarschuwing (de dry run test het niet)")
check(("SourceColumns", "error") in problems({"SourceColumns": "ID"}, source_type="ORACLE_01"), "validate: kolommen niet voor Oracle")
check(("SourceFilter", "error") in problems({"SourceFilter": "ID > 1"}, source_type="SQLMI_01"), "validate: filter niet voor SQLMI")
check(("LoadGroup", "error") in problems({"LoadGroup": "x" * 51}), "validate: LoadGroup langer dan 50")
check(("SourceColumns", "error") in problems({"SourceColumns": "ID,Nope"}, columns=["ID", "Amount"]), "validate: kolom die de ontdekking niet kent")
check(not [p for p in problems({"SourceColumns": "ID,Amount", "LoadGroup": "dag"}, columns=["ID", "Amount"]) if p[1] == "error"], "validate: een geldige combinatie geeft geen fout")
check(("PrimaryKeys", "error") in problems({"SourceColumns": "id", "PrimaryKeys": "ID"}, source_type="SNOWFLAKE_01"), "validate: Snowflake is hoofdlettergevoelig")
check(("SourceColumns", "error") not in problems({"SourceColumns": "ID"}, source_type="ODATA_01"), "validate: kolommen wel voor OData")
check(("SourceFilter", "error") not in problems({"SourceFilter": "Amount gt 0"}, source_type="ODATA_01"), "validate: filter wel voor OData")
check(("SourceColumns", "warning") in problems({"SourceColumns": "ID,Amount"}), "validate: kolommen wijzigen bij een geregistreerde tabel waarschuwt (Bronze-merge)")

# ---- a cast per column (Snowflake, TIME) --------------------------------------------------------------
SF, TIME = "SNOWFLAKE_01", {"TIJD": "TIME", "GEWIJZIGD": "TIMESTAMP_NTZ"}
cols = ["ID", "TIJD", "GEWIJZIGD"]
errors = lambda *a, **kw: [p for p in problems(*a, **kw) if p[1] == "error"]
check(scope["split_column"]("TIJD::VARCHAR") == ("TIJD", "VARCHAR") and scope["split_column"](" TIJD :: VARCHAR ") == ("TIJD", "VARCHAR"), "split_column: naam en type, spaties eraf")
check(scope["split_column"]("TIJD") == ("TIJD", None) and scope["split_column"]("TIJD::") == ("TIJD", "") and scope["split_column"]("::X") == ("", "X"), "split_column: zonder cast, lege cast, lege naam")
check(not errors({"SourceColumns": "ID,TIJD::VARCHAR", "PrimaryKeys": "ID,TIJD", "FileType": "delta"}, SF, columns=cols, types=TIME), "cast: TIJD::VARCHAR met TIJD in de key geeft geen fout")
check(("PrimaryKeys", "error") in problems({"SourceColumns": "ID,TIJD::VARCHAR", "PrimaryKeys": "ID,NOPE"}, SF, columns=cols, types=TIME), "cast: een key die niet in de lijst staat blijft een fout (de cast telt niet als naam)")
check(("SourceColumns", "error") in problems({"SourceColumns": "ID,Nope::VARCHAR"}, SF, columns=cols), "cast: een onbekende kolom met cast is een fout")
check(("SourceColumns", "error") in problems({"SourceColumns": "ID::VARCHAR"}), "cast: niet voor ASQL_01")
for bad in ("TIJD::VARCHAR(10)", "TIJD::", "::VARCHAR", 'TIJD::X" FROM y--', "TIJD::NUMBER(12,2)"):
    check(("SourceColumns", "error") in problems({"SourceColumns": f"ID,{bad}"}, SF), f"cast: {bad!r} wordt geweigerd")
check(("SourceColumns", "error") in problems({"SourceColumns": "ID,GEWIJZIGD::VARCHAR", "IsIncremental": 1, "IsIncrementalColumn": "GEWIJZIGD"}, SF, columns=cols, types=TIME), "cast: niet op de watermarkkolom")
check(("SourceColumns", "error") in problems({"FileType": "delta"}, SF, columns=cols, types=TIME), "TIME zonder cast, alle kolommen, delta: fout")
check(("SourceColumns", "error") in problems({"SourceColumns": "ID,TIJD", "FileType": "delta"}, SF, columns=cols, types=TIME), "TIME zonder cast, in de lijst, delta: fout")
check(("SourceColumns", "warning") in problems({"SourceColumns": "ID,TIJD", "FileType": "parquet"}, SF, columns=cols, types=TIME)
      and ("SourceColumns", "error") not in problems({"SourceColumns": "ID,TIJD", "FileType": "parquet"}, SF, columns=cols, types=TIME), "TIME zonder cast bij parquet: waarschuwing (niet getest), geen fout")
check(not [p for p in problems({"SourceColumns": "ID,GEWIJZIGD", "FileType": "delta"}, SF, columns=cols, types=TIME) if p[0] == "SourceColumns" and p[1] == "error"], "TIME-kolom buiten de lijst: geen melding")
check(("SourceColumns", "error") not in problems({"SourceColumns": "ID,TIJD::VARCHAR", "FileType": "delta"}, SF, columns=cols, types=TIME), "TIME met cast: geen TIME-melding")
check(("SourceColumns", "error") not in problems({"FileType": "delta"}, "ASQL_01", columns=cols, types=TIME), "TIME-controle geldt alleen voor Snowflake")
warnings = lambda updates: [p for p in problems(updates, SF, columns=cols, types=TIME) if p == ("SourceColumns", "warning")]
check(len(warnings({"SourceColumns": "ID,GEWIJZIGD"})) == 1 and len(warnings({"SourceColumns": "ID,GEWIJZIGD::VARCHAR"})) == 2, "cast toevoegen aan een geregistreerde tabel geeft een extra waarschuwing (kolomtype verandert)")
check(scope["join_columns"](["ID", "TIJD"], "ID,TIJD::VARCHAR") == "ID,TIJD::VARCHAR", "join_columns: de cast blijft bij het opslaan van de kolomkeuze")
check(scope["join_columns"](["ID"], "ID,TIJD::VARCHAR") == "ID" and scope["join_columns"](["ID", "TIJD"], "ID") == "ID,TIJD", "join_columns: een kolom die uit de keuze gaat verliest zijn cast; een nieuwe kolom krijgt er geen")
check(scope["join_columns"]([], "") == "" and scope["join_columns"](("A", "B"), "B::DATE , A") == "A,B::DATE", "join_columns: leeg, tuple, spaties in de vorige tekst")

# ---- bulk ---------------------------------------------------------------------------------------------
keys = [scope["entity_key"](e) for e in state["entities"]]
check(scope["BULK_FIELDS"] == ("IsActive", "IsHistorized", "LoadGroup"), "BULK_FIELDS bevat LoadGroup")
before = scope["bulk_set"](state, keys, "LoadGroup", "  nieuw ")
check(len(before) == 2 and all(e["LoadGroup"] != "nieuw" for e in state["entities"]), "bulk_set zonder apply wijzigt niets")
scope["bulk_set"](state, keys, "LoadGroup", " nieuw ", apply=True)
check(all(e["LoadGroup"] == "nieuw" for e in state["entities"]), "bulk_set: LoadGroup als getrimde tekst")
check(scope["bulk_set"](state, keys, "LoadGroup", "nieuw") == [], "bulk_set: tabellen die de waarde al hebben tellen niet mee")
scope["bulk_set"](state, keys, "IsActive", 1, apply=True)
check(all(e["IsActive"] == 1 and isinstance(e["IsActive"], int) for e in state["entities"]), "bulk_set: IsActive blijft 0 of 1")
scope["bulk_set"](state, keys, "LoadGroup", "", apply=True)
check(all(e["LoadGroup"] == "" for e in state["entities"]), "bulk_set: leeg = terug naar de groep van de bron")

# ---- overview and export ---------------------------------------------------------------------------
state = scope["build_state"]("TEST", "D", "WS", sources_rows, [row("Orders", EntityLoadGroup="dag", SourceColumns="ID,Amount", SourceFilter="Amount < 5 AND Name = 'a'"), row("Customers")])
original = copy.deepcopy(state)
for e in state["entities"]:
    e["IsHistorized"] = 1  # touch both, so both are in the overview
page = scope["overview_html"](state, original)
check("<td>dag</td>" in page, "overview: de eigen groep van een tabel")
check("van bron: nacht" in page, "overview: tabel zonder eigen groep toont die van de bron")
check("2: ID, Amount" in page and "alle" in page, "overview: kolommen als aantal en namen, of 'alle'")
check("Amount &lt; 5 AND Name = &#x27;a&#x27;" in page, "overview: het filter is HTML-veilig")
text = scope["export_tables"](
    [{"Environment": "*", "Source": "ERP", "ConnectionName": "C", "DataSourceName": "D", "Namespace": "n", "DataSourceType": "ASQL_01", "LoadGroup": "g"}],
    [{"Source": "ERP", "SourceSchema": "dbo", "SourceName": "T", "LoadGroup": "dag", "SourceColumns": "A,B", "SourceFilter": "A > 1"}])
check(all(c in text.split("entities")[1].split("\n")[1] for c in ("LoadGroup", "SourceColumns", "SourceFilter")), "export_tables: de nieuwe kolommen")
new = scope["new_entity"]({"Source": "ERP", "DataSourceType": "ASQL_01"}, "dbo", "T")
check(new["LoadGroup"] == "" and new["SourceColumns"] == "" and new["SourceFilter"] == "" and new["Watermark"] is None, "new_entity: lege standaard")

# ---- copy D -> T/P -------------------------------------------------------------------------------------
print("=== kopie van D naar T en P ===")
plan_copy = scope["plan_copy"]
rules = '[{"function": "exclude_rows", "columns": "OP", "parameters": {"values": ["delete"]}}]'
d_state = scope["build_state"]("TEST", "D", "WS D", sources_rows, [
    row("Orders", IsIncremental=1, IsIncrementalColumn="ModifiedAt", SilverRules=rules, SourceFilter="Amount > 0", Watermark="2024-06-01"),
    row("Customers", EntityLoadGroup="dag"), row("Old", IsActive=0), row("Wide", SourceColumns="ID,Amount")])
d_state["environment"] = "D"


def target(*rows):
    return scope["build_state"]("TEST", "T", "WS T", sources_rows, list(rows))


def names(plan):
    return sorted(e["SourceName"] for e in plan["entities"])


plan = plan_copy(d_state, target(), "T")
check(names(plan) == ["Customers", "Orders", "Wide"], "kopie naar een lege omgeving: alleen de actieve tabellen")
check(not [p for p in plan["problems"] if p["level"] == "error"], "kopie: een geldige set geeft geen fout")
orders_t = next(e for e in plan["entities"] if e["SourceName"] == "Orders")
check(orders_t["SourceFilter"] == "Amount > 0" and orders_t["IsIncremental"] == 1 and orders_t["PrimaryKeys"] == "ID", "kopie: de instellingen van D gaan mee")
check(not any("discovered" in p["message"] for p in plan["problems"]), "kopie: geen waarschuwing over ontbrekende ontdekking")
check(orders_t["SilverCleansingRules"] and "BronzeCleansingRules" not in orders_t, "kopie: Silver-regels gaan mee, een lege Bronze-lijst laat het veld weg")
check(not any("Watermark" in e for e in plan["entities"]), "kopie: een watermark gaat nooit mee")
check(plan["sources"] and plan["sources"][0]["Environment"] == "*" and "HistoryDays" not in plan["sources"][0], "kopie: bron met Environment '*', geen HistoryDays zonder history_days")
check(names(plan_copy(d_state, target(), "T", only_active=False)) == ["Customers", "Old", "Orders", "Wide"], "only_active=False: ook uitgezette tabellen")
check(names(plan_copy(d_state, target(), "T", sources=["NOPE"])) == [] and plan_copy(d_state, target(), "T", sources=["NOPE"])["problems"], "sources met een onbekende alias: fout, niets geregistreerd")
check(plan_copy(d_state, target(), "T", history_days=30)["sources"][0]["HistoryDays"] == 30, "history_days komt op de bron")

existing = target(row("Orders", SourceFilter="Amount > 100", EntityLoadGroup="nacht", PrimaryKeys="ID,Line"))
plan = plan_copy(d_state, existing, "T")
check(names(plan) == ["Customers", "Wide"] and plan["skipped"] == ["dbo.Orders"], "zonder update: een bestaande tabel blijft ongemoeid")
plan = plan_copy(d_state, existing, "T", update=True)
orders_u = next(e for e in plan["entities"] if e["SourceName"] == "Orders")
check(orders_u["PrimaryKeys"] == "ID" and orders_u["SourceFilter"] == "Amount > 100" and orders_u["LoadGroup"] == "nacht",
      "update: D volgt voor de rest, maar filter en LoadGroup van het doel blijven staan")
check(any(e["SourceName"] == "Customers" for e in plan["entities"]), "update: nieuwe tabellen gaan ook mee")

# overrides: selection per environment
ov = {"*": {"IsActive": 0}, "dbo.Orders": {"IsActive": 1, "SourceFilter": "ModifiedAt >= '2025-01-01'"}}
plan = plan_copy(d_state, target(), "T", overrides=ov)
by = {e["SourceName"]: e for e in plan["entities"]}
check(by["Orders"]["IsActive"] == 1 and by["Orders"]["SourceFilter"] == "ModifiedAt >= '2025-01-01'", "override: een tabelregel gaat voor '*'")
check(by["Customers"]["IsActive"] == 0 and by["Wide"]["IsActive"] == 0, "override '*': standaard voor alle andere tabellen")
check(by["Wide"]["SourceColumns"] == "ID,Amount", "override: wat niet genoemd is blijft zoals in D")
check(d_state["entities"][0]["SourceFilter"] == "Amount > 0", "override: D zelf verandert niet")
plan = plan_copy(d_state, existing, "T", overrides={"dbo.Orders": {"SourceFilter": "Amount > 5"}})
check(names(plan) == ["Customers", "Orders", "Wide"], "override op een bestaande tabel: gaat ook zonder update mee")
orders_o = next(e for e in plan["entities"] if e["SourceName"] == "Orders")
check(orders_o["SourceFilter"] == "Amount > 5" and orders_o["PrimaryKeys"] == "ID,Line" and orders_o["LoadGroup"] == "nacht", "override op een bestaande tabel: alleen dat veld verandert")
check("BronzeCleansingRules" not in orders_o and "SilverCleansingRules" not in orders_o, "override op een bestaande tabel: regels blijven zoals ze zijn")
plan = plan_copy(d_state, existing, "T", overrides={"dbo.Orders": {"SourceFilter": "Amount > 100"}})
check("Orders" not in names(plan) and "dbo.Orders" in plan["skipped"], "override met dezelfde waarde als het doel: niets te doen (herhalen is veilig)")
for bad, text in (({"dbo.Nope": {"IsActive": 1}}, "onbekende tabel"), ({"*": {"PrimaryKeys": "X"}}, "veld buiten de dataselectie"),
                  ({"dbo.Orders": {"SourceFilter": "1=1; DROP TABLE x"}}, "puntkomma in het filter"),
                  ({"dbo.Orders": {"SourceColumns": "Amount"}}, "PK buiten SourceColumns"), ({"*": {"IsActive": 2}}, "IsActive 2")):
    check(any(p["level"] == "error" for p in plan_copy(d_state, target(), "T", overrides=bad)["problems"]), f"override: {text} is een fout")
other = scope["build_state"]("TEST", "D", "WS", [{**sources_rows[0], "DataSourceType": "ORACLE_01"}], [row("Orders", DataSourceType="ORACLE_01")])
other["environment"] = "D"
check(any(p["level"] == "error" for p in plan_copy(other, target(), "T", overrides={"*": {"SourceFilter": "ID > 1"}})["problems"]), "override: filter voor een brontype dat het niet kent is een fout")

# a source with another connection in the target (P-019), and an alias that differs per environment
print("=== connectie en alias per omgeving ===")
p_sources = [{**sources_rows[0], "ConnectionName": "CON_P"}]
plan = plan_copy(d_state, scope["build_state"]("TEST", "P", "WS P", p_sources, [row("Orders", ConnectionName="CON_P")]), "P")
check(plan["sources"][0]["ConnectionName"] == "CON_P", "kopie: de bron behoudt de connectie van het doel (P-019), niet die van D")
check(plan_copy(d_state, target(), "T")["sources"][0]["ConnectionName"] == "CON_X", "kopie: een bron die het doel nog niet heeft, krijgt de connectie van D")
check(d_state["sources"][0]["ConnectionName"] == "CON_X", "kopie: D zelf verandert niet")
# in the target a second source shares the namespace, so the same source gets another alias there
two = [{**sources_rows[0], "DataSourceName": "OTHERDB"}, sources_rows[0]]
shifted = scope["build_state"]("TEST", "T", "WS T", two, [row("Orders", SourceFilter="Amount > 100")])
check(shifted["sources"][1]["Source"] != d_state["sources"][0]["Source"], "voorwaarde: de alias van dezelfde bron verschilt per omgeving")
plan = plan_copy(d_state, shifted, "T")
check("Orders" not in names(plan) and "dbo.Orders" in plan["skipped"], "alias verschilt: een bestaande tabel wordt toch herkend")
plan = plan_copy(d_state, shifted, "T", overrides={"dbo.Orders": {"SourceFilter": "Amount > 5"}})
orders_s = next(e for e in plan["entities"] if e["SourceName"] == "Orders")
check(orders_s["Source"] in {s["Source"] for s in plan["sources"]}, "override op een bestaande tabel: de bron staat in de payload (alias van D)")

# ---- compare D, T and P ----------------------------------------------------------------------------------
print("=== omgevingen vergelijken ===")
compare = scope["compare_environments"]
ds = scope["build_state"]("TEST", "D", "WS D", sources_rows, [row("Orders", SourceFilter="Amount > 0", Watermark="1"), row("Customers"), row("Wide", PrimaryKeys="ID")])
ts = scope["build_state"]("TEST", "T", "WS T", sources_rows, [row("Orders", SourceFilter="Amount > 5"), row("Wide", PrimaryKeys="ID")])
ps = scope["build_state"]("TEST", "P", "WS P", p_sources, [row("Orders", ConnectionName="CON_P", SourceFilter="Amount > 5", PrimaryKeys="ID,Line"), row("Wide", ConnectionName="CON_P", PrimaryKeys="ID")])
rows_ = {r["Table"]: r for r in compare({"D": ds, "T": ts, "P": ps})}
check(list(rows_) == ["dbo.Orders", "dbo.Customers", "dbo.Wide"], "vergelijken: een rij per tabel, in de volgorde van D")
o, c, wd = rows_["dbo.Orders"], rows_["dbo.Customers"], rows_["dbo.Wide"]
check(o["Selection"] == {"SourceFilter": {"D": "Amount > 0", "T": "Amount > 5", "P": "Amount > 5"}}, "vergelijken: een ander filter staat onder dataselectie")
check(o["Other"] == {"PrimaryKeys": {"D": "ID", "T": "ID", "P": "ID,Line"}} and o["Status"] == "differs", "vergelijken: een andere primary key is een afwijking")
check(o["Connection"] == {"D": "CON_X", "T": "CON_X", "P": "CON_P"} and "Watermark" not in o["Selection"] | o["Other"], "vergelijken: de connectie staat apart, het watermark telt niet mee")
check(c["Present"] == {"D": True, "T": False, "P": False} and c["Status"] == "missing", "vergelijken: een tabel die ontbreekt")
check(wd["Status"] == "same" and wd["Selection"] == {} and wd["Other"] == {} and wd["Connection"] == {"D": "CON_X", "T": "CON_X", "P": "CON_P"},
      "vergelijken: alleen een andere connectie telt niet als verschil")
only_sel = compare({"D": ds, "T": scope["build_state"]("TEST", "T", "WS T", sources_rows, [row("Orders", SourceFilter="Amount > 5"), row("Customers"), row("Wide", PrimaryKeys="ID")])})
check({r["Table"]: r["Status"] for r in only_sel} == {"dbo.Orders": "selection", "dbo.Customers": "same", "dbo.Wide": "same"}, "vergelijken: alleen de dataselectie anders")
rules2 = scope["build_state"]("TEST", "T", "WS T", sources_rows, [row("Orders", SourceFilter="Amount > 0", SilverRules=rules)])
check(compare({"D": ds, "T": rules2})[0]["Other"].keys() == {"SilverRules"}, "vergelijken: andere Silver-regels zijn een afwijking")
shifted_cmp = compare({"D": ds, "T": scope["build_state"]("TEST", "T", "WS T", two, [row("Orders", SourceFilter="Amount > 0")])})
check(shifted_cmp[0]["Present"] == {"D": True, "T": True}, "vergelijken: herkent een tabel ook als de alias verschilt")
check(compare({"D": ds}) and compare({"D": ds})[0]["Status"] == "same", "vergelijken: één omgeving geeft geen verschillen")

# ---- the comparison as a table, and tab 4 -------------------------------------------------------------------
print("=== tab Omgevingen ===")
compared = compare({"D": ds, "T": ts, "P": ps})
shown = scope["comparison_html"](compared, ["D", "T", "P"], "diff")
check("dbo.Orders" in shown and "dbo.Customers" in shown and "dbo.Wide" not in shown, "tabel: 'alleen verschillen' laat gelijke tabellen weg (een andere connectie telt niet)")
check("dbo.Wide" in scope["comparison_html"](compared, ["D", "T", "P"], "all"), "tabel: 'alles' toont ook gelijke tabellen")
check("dbo.Customers" not in scope["comparison_html"](compared, ["D", "T", "P"], "differs") and "dbo.Orders" in scope["comparison_html"](compared, ["D", "T", "P"], "differs"), "tabel: filter op een status")
check("SourceFilter" in shown and "Amount &gt; 5" in shown and "Amount > 5" not in shown, "tabel: waarden staan er, en HTML-tekens zijn ontsnapt")
evil = compare({"D": scope["build_state"]("TEST", "D", "W", sources_rows, [row("<b>x</b>")]), "T": scope["build_state"]("TEST", "T", "W", sources_rows, [])})
check("<b>x</b>" not in scope["comparison_html"](evil, ["D", "T"], "all"), "tabel: een tabelnaam met HTML wordt ontsnapt")

calls = []
scope["compare"] = lambda domain, envs: (calls.append(("compare", domain, envs)), compare({"D": ds, "T": ts, "P": ps}))[1]
scope["copy_registration"] = lambda domain, to_environments, **kw: calls.append(("copy", domain, to_environments, kw))
ui = types.SimpleNamespace(domain=w.Text("INTEGRATION"), _guard=lambda b, f: b.on_click(lambda _: f()))
page = scope["EnvironmentsPage"](ui)
check("icon=" not in NOTEBOOK, "geen iconen: Fabric laadt FontAwesome niet, ze zijn onzichtbaar")
check(page.ov_value.continuous_update is False,
      "tab: tekstvelden leggen hun waarde vast bij verlaten (Fabric loopt achter bij elke toetsaanslag; in de trial werd 'Amount > 1' als 'A' toegevoegd)")
check(page.view == 0 and page.compare_view.layout.display == "" and page.copy_view.layout.display == "none", "tab: opent op Vergelijken")
check(page.view_bar.buttons[0].button_style == "info" and page.view_bar.buttons[1].button_style == "", "tab: de gekozen weergave heeft een eigen stijl, anders dan de hoofdtabs")
page.view_bar.buttons[1].click()
check(page.view == 1 and page.compare_view.layout.display == "none" and page.copy_view.layout.display == "" and page.view_bar.buttons[1].button_style == "info" and page.view_bar.buttons[0].button_style == "",
      "tab: omschakelen naar Overzetten")
page.show_view(0)
page.compare_btn.click()
check(calls[-1] == ("compare", "INTEGRATION", ["D", "T", "P"]) and "dbo.Orders" in page.table.value, "tab: Vergelijken leest de aangevinkte omgevingen en toont de tabel")
check("niet in T, P" in page.table.value, "tab: bij 'ontbreekt' staat in welke omgevingen de tabel niet staat")
check(page.to_copy_btn.layout.display == "", "tab: na het vergelijken is 'Naar Overzetten' beschikbaar")
n = len(calls)
page.to_copy_btn.click()
check(page.view == 1 and page.from_dd.value == "D" and [e for e, c in page.to_checks.items() if c.value] == ["T", "P"] and len(calls) == n,
      "tab: 'Naar Overzetten' vult de omgevingen in en start niets")
page.show_view(0)
page.cmp_checks["D"].value = False
page.compare_btn.click()
page.to_copy_btn.click()
check(page.from_dd.value == "T" and [e for e, c in page.to_checks.items() if c.value] == ["P"], "tab: zonder D in de vergelijking is de eerste omgeving de bron")
page.from_dd.value = "D"
page.to_checks["T"].value = page.to_checks["P"].value = True
page.show_view(0)
page.cmp_checks["D"].value = True
page.cmp_checks["P"].value = False
page.compare_btn.click()
check(calls[-1] == ("compare", "INTEGRATION", ["D", "T"]), "tab: een niet aangevinkte omgeving gaat niet mee")
page.cmp_checks["T"].value = False
n = len(calls)
page.compare_btn.click()
check(len(calls) == n and "minstens twee" in page.cmp_res.widget.value and page.pane() is page.cmp_res, "tab: minder dan twee omgevingen: melding in het zichtbare vak, niets gelezen")
page.show_view(1)
check(page.pane() is page.res, "tab: op Overzetten gaan meldingen naar het vak van die weergave")
check(page.from_dd.value == "D" and [e for e, c in page.to_checks.items() if c.value] == ["T", "P"], "tab: standaard van D naar T en P")
check(page.to_checks["D"].disabled and not page.to_checks["T"].disabled, "tab: de bronomgeving is uitgeschakeld als doel")
page.from_dd.value = "T"
check(page.to_checks["T"].disabled and page.to_checks["T"].value is False and not page.to_checks["D"].disabled, "tab: een andere bron schakelt het vinkje van die omgeving uit en zet het uit")
page.from_dd.value = "D"
page.to_checks["T"].value = page.to_checks["P"].value = True
check(page.ov_box.layout.display == "none", "tab: het override-formulier is verborgen tot je het aanzet")
page.ov_enable.value = True
check(page.ov_box.layout.display == "", "tab: het vinkje toont het override-formulier")
page.ov_field.value = "LoadGroup"
check("laadgroep" in page.ov_field_label.value and "laadgroep" in page.ov_help.value, "tab: de uitleg bij de gekozen instelling staat in een tooltip en zichtbaar eronder")
page.ov_field.value = "SourceFilter"
page.ov_env.value, page.ov_table.value, page.ov_value.value = "T", "dbo.Orders", "Amount > 9"
page.ov_add.click()
check(page.overrides == {"T": {"dbo.Orders": {"SourceFilter": "Amount > 9"}}} and len(page.ov_rows.children) == 1, "tab: een override per omgeving en tabel toevoegen")
check("Amount &gt; 9" in page.ov_rows.children[0].children[1].value, "tab: de regel toont de waarde, ontsnapt")
page.ov_field.value = "IsActive"
check(page.ov_active.layout.display == "" and page.ov_value.layout.display == "none", "tab: bij Actief een Aan/Uit-keuze in plaats van een tekstveld")
page.ov_table.value, page.ov_active.value = "*", 0
page.ov_add.click()
check(page.overrides["T"]["*"] == {"IsActive": 0} and len(page.ov_rows.children) == 2, "tab: Aan/Uit wordt 1 of 0, '*' geldt voor alle tabellen")
page.ov_rows.children[1].children[0].click()
check(page.overrides == {"T": {"dbo.Orders": {"SourceFilter": "Amount > 9"}}} and len(page.ov_rows.children) == 1, "tab: een override verwijderen met het kruisje van die regel")
page.ov_table.value, page.ov_active.value = "*", 0
page.ov_add.click()
check(page.copy_btn.disabled and "proefdraaien" in page.copy_hint.value.lower(), "tab: overzetten kan niet voor een proefdraai, en de zichtbare regel zegt waarom")
page.confirm.value = True
check(page.copy_btn.disabled, "tab: een vinkje alleen is niet genoeg")
page.dry_btn.click()
kind, domain, to, kw = calls[-1]
check(kind == "copy" and domain == "INTEGRATION" and to == ["T", "P"] and kw["dry_run"] is True and kw["from_environment"] == "D" and kw["update"] is False and kw["only_active"] is True,
      "tab: proefdraai roept copy_registration aan met dry_run=True")
check(kw["overrides"] == {"T": {"dbo.Orders": {"SourceFilter": "Amount > 9"}, "*": {"IsActive": 0}}}, "tab: de overrides gaan mee")
check(page.confirm.value is False and "gecontroleerd" in page.copy_hint.value, "tab: een vinkje van vóór de proefdraai telt niet mee, en de regel vraagt erom")
page.confirm.value = True
check(not page.copy_btn.disabled and "Klaar" in page.copy_hint.value, "tab: na proefdraai en vinkje kan overzetten")
page.copy_btn.click()
check(calls[-1][3]["dry_run"] is False and page.copy_btn.disabled and "Al overgezet" in page.copy_hint.value, "tab: overzetten draait echt, en daarna niet nog een keer")
n = len(calls)
page.copy_btn.click()
check(len(calls) == n, "tab: een tweede klik doet niets")
page.dry_btn.click()
page.confirm.value = True
page.update_cb.value = True
check(page.copy_btn.disabled and page.confirm.value is False and "proefdraaien" in page.copy_hint.value.lower(), "tab: een wijziging na de proefdraai maakt hem ongeldig")
page.update_cb.value = False
page.ov_enable.value = False
page.dry_btn.click()
check(calls[-1][3]["overrides"] is None, "tab: met het override-vinkje uit gaan de overrides niet mee")
page.to_checks["P"].value = False
page.dry_btn.click()
check(calls[-1][2] == ["T"], "tab: een niet aangevinkte doelomgeving valt weg")
page.to_checks["T"].value = False
check("omgeving" in page.copy_hint.value and page.copy_btn.disabled, "tab: zonder doelomgeving zegt de regel dat je er een aanvinkt")
page.ov_enable.value = True
page.ov_clear.click()
check(page.overrides == {} and page.ov_rows.children == [], "tab: overrides wissen")
check(all(getattr(page, n).tooltip for n in ("compare_btn", "dry_btn", "copy_btn", "to_copy_btn")) and "Schrijft" in page.copy_btn.tooltip, "tab: de knoppen hebben een tooltip")
# Fabric shows a tooltip on a button and on HTML (a title), but not on a checkbox or dropdown: their labels are HTML
labels = {"Toon": page.show_label, "Van": page.from_label, "bijwerken": page.update_label, "uit staan": page.inactive_label}
check(all("title=" in w_.value for w_ in labels.values()) and all(text in w_.value for text, w_ in labels.items()), "tab: de labels van vinkjes en dropdowns zijn HTML met een tooltip")
check("Ontbreekt" in page.show_label.value and "Filter, kolommen, LoadGroup en actief blijven" in page.update_label.value, "tab: de tooltips hebben de afgesproken tekst")
check(all("title=" in row.children[1].value for row in (*page.cmp_rows, *page.to_rows)) and all(not hasattr(c, "description_tooltip") for c in page.to_checks.values()),
      "tab: ook de omgevingsvinkjes hebben een tooltip, zonder het verouderde description_tooltip (dat geeft een waarschuwing)")
page.ov_field.value = "LoadGroup"
check("laadgroep" in page.ov_field_label.value, "tab: het label bij Instelling volgt de gekozen instelling")
shown_all = scope["comparison_html"](compared, ["D", "T", "P"], "all")
check("title=" in shown_all and "geregistreerd in deze omgeving" in shown_all, "tabel: tooltip op de kolomkoppen")
header = types.SimpleNamespace(env=w.Dropdown(value="T"), env_other=w.Text("DEV_X"), OTHER_ENV="Andere…")
check(scope["RegistrationUI"]._environment(header) == "T", "kop: D, T en P komen uit de dropdown")
header.env.value = "Andere…"
check(scope["RegistrationUI"]._environment(header) == "DEV_X", "kop: 'Andere…' gebruikt het tekstveld (A en DEV_<NAAM>)")

# the tab bar: the chosen tab is blue and the others are plain (a ToggleButtons selection is barely visible in Fabric)
seen = []
bar = scope["TabBar"](["een", "twee", "drie"], seen.append)
check(bar.value == 0 and [b.button_style for b in bar.buttons] == ["primary", "", ""], "tabbalk: de eerste tab is gekozen en blauw")
bar.buttons[2].click()
check(bar.value == 2 and [b.button_style for b in bar.buttons] == ["", "", "primary"] and seen == [2], "tabbalk: klikken kiest die tab en meldt het")
bar.value = 1
check([b.button_style for b in bar.buttons] == ["", "primary", ""] and seen == [2, 1], "tabbalk: in code kiezen werkt ook (Terug naar begin)")

# tab 3: the confirmation counts only after the dry run (the checkbox ticked beforehand must not carry over)
registered = []
scope["register"] = lambda *a, **kw: registered.append(kw.get("dry_run"))
tab3 = types.SimpleNamespace(confirm=w.Checkbox(value=True), res=scope["Pane"](), dry_run_of=None, check=lambda: True,
                             _payload=lambda: ([{"Source": "S"}], [{"Source": "S"}]), state={"domain": "TEST", "environment": "D"},
                             _fingerprint=lambda: "fp", _say=lambda *a, **kw: None)
scope["RegistrationUI"].dry_run(tab3)
check(registered == [True] and tab3.dry_run_of == "fp", "tab 3: de proefdraai draait met dry_run=True")
check(tab3.confirm.value is False, "tab 3: een vinkje van vóór de proefdraai telt niet mee")

# ---- ColumnPicker -------------------------------------------------------------------------------------
print("=== ColumnPicker ===")
calls = []
picker = scope["ColumnPicker"]("Kolommen", on_change=lambda: calls.append(picker.value))
picker.load(["ID", "Amount", "OrderDate", "CustomerName"], ["Amount"])
check(picker.value == ("Amount",) and calls == [], "load: selectie gezet, on_change niet aangeroepen")
check(list(picker.select.options) == ["ID", "Amount", "OrderDate", "CustomerName"] and picker.select.value == ("Amount",), "load: alle kolommen, keuze behouden")
picker.search.value = "date"
check(list(picker.select.options) == ["Amount", "OrderDate"], "zoeken: treffers plus wat al gekozen is")
check(picker.value == ("Amount",) and picker.select.value == ("Amount",) and calls == [], "zoeken: de keuze blijft, zonder on_change")
picker.select.value = ("Amount", "OrderDate")
check(picker.value == ("Amount", "OrderDate") and calls[-1] == ("Amount", "OrderDate"), "kiezen binnen de treffers: on_change met de nieuwe keuze")
picker.search.value = "name"
check(picker.value == ("Amount", "OrderDate"), "ander zoekwoord: eerdere keuzes blijven gekozen buiten beeld")
picker.all_btn.click()
check(picker.value == ("Amount", "OrderDate", "CustomerName"), "alle zichtbare: voegt toe, vervangt niet; volgorde van de tabel")
picker.search.value = ""
picker.none_btn.click()
check(picker.value == () and calls[-1] == (), "wissen")
picker.load(["ID"], ["Oud"])
check(picker.value == ("Oud",) and "Oud" in picker.select.options, "load: een gekozen naam die geen kolom is blijft staan (en wordt gerapporteerd door Controleren)")

# ---- SQL, static ------------------------------------------------------------------------------------------
print("=== SQL ===")
for view in ("vw_LoadSourceToLandingzone", "vw_LoadToBronzeLayer", "vw_LoadToSilverLayer"):
    text = (SQL / f"execution/Views/{view}.sql").read_text(encoding="utf-8")
    check("COALESCE(NULLIF(LZE.[LoadGroup], ''), DS.[LoadGroup]) AS [LoadGroup]" in text and "DS.[LoadGroup] AS" not in text, f"{view}: LoadGroup van de tabel, anders van de bron")
table = (SQL / "integration/Tables/LandingzoneEntity.sql").read_text(encoding="utf-8")
check(all(re.search(r"\[%s\]\s+\S+(\s+\(\S+\))?\s+NULL" % c, table) for c in ("LoadGroup", "SourceColumns", "SourceFilter")), "LandingzoneEntity: drie kolommen, NULL toegestaan")
proc = (SQL / "integration/StoredProcedures/sp_RegisterEntities.sql").read_text(encoding="utf-8")
check(all(f"'{c}'" in proc for c in ("LoadGroup", "SourceColumns", "SourceFilter")), "sp_RegisterEntities: de velden staan in de lijst van bekende velden")
in_proc = set(re.findall(r"'(\w+_\d+)'", re.search(r"\[DataSourceType\] NOT IN \(([^)]*)\)", proc).group(1)))
check(in_proc == set(scope["SOURCE_FILTER_TYPES"]), f"brontypes met kolommen en filter: procedure en notebook gelijk ({sorted(in_proc)})")
check("[SourceColumns] = @SC" in proc and "[SourceFilter] = @SF" in proc and "[LoadGroup] = @LGE" in proc, "sp_RegisterEntities: schrijft de drie velden")
landing = (SQL / "execution/Views/vw_LoadSourceToLandingzone.sql").read_text(encoding="utf-8")
check(landing.count("QF.[Filter]") >= 5 and "QF.[Columns]" in landing, "vw_LoadSourceToLandingzone: filter in de kopie- en de watermarkquery, kolommen in de kopie")
# CONCAT_WS of only NULLs is '', not NULL: without the NULLIF the first load of an incremental table (no watermark, no filter)
# gets a WHERE without a condition.
check(landing.count("NULLIF(CONCAT_WS(' AND ',") == 2, "vw_LoadSourceToLandingzone: geen WHERE zonder voorwaarde (eerste load van een incrementele tabel)")

# A cast per column: the view builds "name"::TYPE AS "name" for Snowflake only, with TYPE restricted to a bare word; the procedure
# and the notebook refuse the rest. The SQL itself ran against SQL Server 2022 (ADR-020, aanvulling 2026-10-26).
check("::' + p.[CastType] + ' AS \"'" in landing and "NOT LIKE '%[^A-Za-z0-9_]%'" in landing and "CHARINDEX('::'" in landing, "vw_LoadSourceToLandingzone: cast per kolom, type beperkt tot een kaal woord")
check("a cast (name::TYPE) is only supported for SNOWFLAKE_01" in proc and "LIKE '%[^A-Za-z0-9_]%'" in proc, "sp_RegisterEntities: weigert een cast buiten Snowflake en een ander type dan een kaal woord")
check(proc.count("CHARINDEX('::', sc.[value])") >= 8, "sp_RegisterEntities: key-, watermark- en ontdekkingscontrole vergelijken de naam voor '::'")

print("\nALLES OK" if not failures else f"\n{failures} FOUT(EN)")
sys.exit(1 if failures else 0)
