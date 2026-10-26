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


w = types.SimpleNamespace(HTML=FakeWidget, Text=FakeWidget, SelectMultiple=FakeWidget, Button=FakeWidget,
                          HBox=lambda children, **kw: FakeWidget(children=children), VBox=lambda children, **kw: FakeWidget(children=children),
                          Layout=Layout)

scope = {"json": json, "re": re, "html": html, "copy": copy, "io": io, "contextlib": contextlib, "traceback": traceback, "w": w}
exec(compile(cell_with("def build_state"), "registration logic", "exec"), scope)
exec(compile(cell_with("class ColumnPicker"), "registration ui", "exec"), scope)
exec(compile(cell_with("def plan_copy"), "registration copy", "exec"), scope)

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
