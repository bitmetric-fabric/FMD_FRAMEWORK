"""Check of deduplicate_keys in NB_FMD_DQ_CLEANSING (ADR-022).

    python3 scripts/test_deduplicate_keys.py

Part 1 (no dependencies): argument validation.
Part 2 (needs pyspark and Java): behaviour on real DataFrames; skipped with a notice when pyspark is missing.
"""

import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent).resolve()
SRC = (REPO / "src/NB_FMD_DQ_CLEANSING.Notebook/notebook-content.py").read_text(encoding="utf-8")
CODE = re.search(r"(cleansing_dedup_stats = .*?def deduplicate_keys.*?)\n# METADATA", SRC, re.S).group(1)
BRONZE = (REPO / "src/NB_FMD_LOAD_LANDING_BRONZE.Notebook/notebook-content.py").read_text(encoding="utf-8")

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


check('register_cleansing_function("deduplicate_keys", deduplicate_keys)' in SRC, "registered in the built-in cell")
check(BRONZE.index("## Check for Duplicates") > BRONZE.index("handle_cleansing_functions(dfDataChanged"),
      "Bronze checks for duplicates after the cleansing")
check(BRONZE.count("**cleansing_dedup_stats,") == 2, "Bronze logs the counts on the first load and after the merge")

print("validation")
ns = {"DataFrame": None, "col": MagicMock(), "lit": MagicMock()}
exec(CODE, ns)
f = ns["deduplicate_keys"]


def df_with(*cols):
    df = MagicMock()
    df.columns = list(cols)
    return df


check(raises(f, df_with("HashedPKColumn", "TS"), [], {}), "no columns -> error")
check(raises(f, df_with("HashedPKColumn", "TS"), ["X"], {}), "unknown column -> error")
check(raises(f, df_with("TS"), ["TS"], {}), "no HashedPKColumn (not Bronze) -> error")
check(raises(f, df_with("HashedPKColumn", "TS"), ["TS"], {"keep": "newest"}), "bad keep -> error")

print("behaviour (pyspark)")
try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql.functions import col, lit
    spark = SparkSession.builder.master("local[1]").getOrCreate()
except Exception as e:
    print(f"  SKIP   pyspark/Java not available ({type(e).__name__}); behaviour not tested")
    sys.exit(1 if failures else 0)

exec(CODE, globals())
schema = "HashedPKColumn string, id int, TS string, FILLER string, REDEN string"
rows = [
    ("a", 1, "2026-11-01", "", "X"),          # unique key: untouched
    ("b", 2, "2026-11-01", "   ", "X"),       # dump pair, differs only in a filler (spaces vs empty)
    ("b", 3, "2026-11-01", "", "X"),
    ("c", 4, "2026-11-01", "", "VM001"),      # dump pair, differs in a business column
    ("c", 5, "2026-11-01", "", "RD004"),
    ("d", 6, "2026-11-02", "", "old"),        # two events for one key
    ("d", 7, "2026-11-03", "", "new"),
    ("e", 8, None, "", "null ts"),            # NULL in the order column
    ("e", 9, "2026-11-01", "", "ts"),
]
df = spark.createDataFrame(rows, schema)


def run(data, keep):
    cleansing_dedup_stats.update({'RowsDeduplicated': 0, 'KeysDeduplicated': 0})
    out = deduplicate_keys(data, ["TS"], {"keep": keep})
    return {r.HashedPKColumn: r.id for r in out.collect()}, out.count(), dict(cleansing_dedup_stats)


last, n, stats = run(df, "last")
check(n == 5 and sorted(last) == ["a", "b", "c", "d", "e"], "one row per key, 5 of 9 rows")
check(stats == {'RowsDeduplicated': 4, 'KeysDeduplicated': 4}, f"stats count dropped rows and keys: {stats}")
check(last["a"] == 1, "unique key untouched")
check(last["d"] == 7, "keep=last: latest event wins")
check(last["e"] == 9, "keep=last: NULL order value loses")
first, _, _ = run(df, "first")
check(first["d"] == 6, "keep=first: earliest event wins")
check(first["e"] == 8, "keep=first: NULL order value counts as lowest")
again, _, _ = run(df.orderBy(col("id").desc()).repartition(3), "last")
check(again == last, "same order value: the same row wins regardless of input order")
check(set(run(df, "last")[0]) == set(last) and deduplicate_keys(df, ["TS"], {}).columns == df.columns,
      "default keep is last, columns unchanged")
clean = df.where(col("HashedPKColumn") == "a")
cleansing_dedup_stats.update({'RowsDeduplicated': 0, 'KeysDeduplicated': 0})
check(deduplicate_keys(clean, ["TS"], {}) is clean and cleansing_dedup_stats['RowsDeduplicated'] == 0,
      "no duplicates: DataFrame returned as is, nothing logged")

sys.exit(1 if failures else 0)
