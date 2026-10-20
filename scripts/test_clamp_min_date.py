"""Check of clamp_min_date in NB_FMD_DQ_CLEANSING.

    python3 scripts/test_clamp_min_date.py

Part 1 (no dependencies): argument validation, with pyspark stubbed.
Part 2 (needs pyspark and Java): behaviour on real DataFrames; skipped with a notice when pyspark is missing.
"""

import re
import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent).resolve()
SRC = (REPO / "src/NB_FMD_DQ_CLEANSING.Notebook/notebook-content.py").read_text(encoding="utf-8")
CODE = re.search(r"(def clamp_min_date.*?)\n# METADATA", SRC, re.S).group(1)

failures = 0


def check(ok, text):
    global failures
    print(("  ok     " if ok else "  FOUT   ") + text)
    failures += 0 if ok else 1


def raises(fn, *a):
    try:
        fn(*a)
    except (ValueError, TypeError):
        return True
    return False


check('register_cleansing_function("clamp_min_date", clamp_min_date)' in SRC, "registered in the built-in cell")

print("validation (stubbed pyspark)")
class Col:
    def __call__(self, *a):
        return self

    def __getattr__(self, name):
        return self

    def __lt__(self, other):
        return self

    __le__ = __lt__


ns = {"DataFrame": None, "col": Col(), "lit": Col(), "when": Col()}
exec(CODE, ns)
f = ns["clamp_min_date"]


def df_with(**cols):
    df = MagicMock()
    fields = []
    for name, t in cols.items():
        fl = MagicMock()
        fl.name = name
        fl.dataType.simpleString.return_value = t
        fields.append(fl)
    df.schema.fields = fields
    return df


check(raises(f, df_with(a="date"), [], {}), "no columns -> error")
check(raises(f, df_with(a="date"), ["x"], {}), "unknown column -> error")
check(raises(f, df_with(a="string"), ["a"], {}), "string column -> error")
check(raises(f, df_with(a="date"), ["a"], {"min": "01-01-1900"}), "bad min -> error")
check(raises(f, df_with(a="date"), ["a"], {"replacement": "nonsense"}), "bad replacement -> error")
for t in ("date", "timestamp", "timestamp_ntz"):
    check(not raises(f, df_with(a=t), ["a"], {"min": "1900-01-01", "replacement": "1900-01-02", "inclusive": True}), f"{t} accepted")

print("behaviour (pyspark)")
try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql.functions import col, lit, when
    spark = SparkSession.builder.master("local[1]").getOrCreate()
except Exception as e:
    print(f"  SKIP   pyspark/Java not available ({type(e).__name__}); behaviour not tested")
    sys.exit(1 if failures else 0)

exec(CODE, globals())
rows = [(1, date(1, 1, 1)), (2, date(1900, 1, 1)), (3, date(2020, 5, 5)), (4, None)]
d = spark.createDataFrame(rows, "id int, d date")
t = d.selectExpr("id", "cast(d as timestamp) as d")


def run(df, args):
    return {r.id: r.d for r in clamp_min_date(df, ["d"], args).orderBy("id").collect()}


check(run(d, {}) == {1: date(1900, 1, 1), 2: date(1900, 1, 1), 3: date(2020, 5, 5), 4: None}, "date, exclusive: < min replaced, = min kept, NULL kept")
check(run(d, {"inclusive": True, "replacement": "1900-01-02"}) == {1: date(1900, 1, 2), 2: date(1900, 1, 2), 3: date(2020, 5, 5), 4: None}, "date, inclusive + replacement")
a = run(t, {})
check(a[1] == datetime(1900, 1, 1, 0, 0) and a[3] == datetime(2020, 5, 5, 0, 0) and a[4] is None, "timestamp, variant A")
check(run(t, {"min": "1900-01-01", "replacement": "1900-01-02 12:30:00", "inclusive": True})[2] == datetime(1900, 1, 2, 12, 30), "timestamp, variant B with time")
check(clamp_min_date(t, ["d"], {}).schema["d"].dataType.simpleString() == "timestamp", "column type unchanged")

sys.exit(1 if failures else 0)
