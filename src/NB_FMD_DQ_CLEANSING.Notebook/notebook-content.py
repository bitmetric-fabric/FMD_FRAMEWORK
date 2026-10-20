# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse_name": "",
# META       "default_lakehouse_workspace_id": ""
# META     }
# META   }
# META }

# MARKDOWN ********************

# ## Data cleansing functions
# 
# It is possible to perform cleansing functions on incoming data. For example, converting all text in a column to uppercase. This can be achieved by defining cleansing rules for a table. The cleansing_rules contains a piece of JSON as shown below. This is an array of one or more functions that need to be called.
# 
# - function: name of the function
# - columns: semi-colon separated list of columns to which the function should be applied
# - parameters: JSON string with the different parameters and their values
# 
# Example:
# 
# ```
# [
#    {"function": "to_upper",
#     "columns": "TransactionTypeName"}, 
#    {"function": "custom_function_with_params",
#     "columns": "TransactionTypeName;LastEditedBy",
#     "parameters": {"param1" : "abc", "param2" : "123"}}
# ]
# ```
# More info https://github.com/edkreuk/FMD_FRAMEWORK/wiki/Data-Cleansing
# 
# 
# ## Custom functions
# Custom functions can be added in a separate notebook NB_FMD_CUSTOM_DQ_CLEANSING.
# Each function must be registered to be callable from cleansing rules:
# ```
# def my_custom_function(df, columns, args):
#     print(args['<custom parameter name>']) # use of custom parameters
#     for column in columns: # apply function foreach column
#         df = df.<custom logic>
#     return df # always return dataframe
# register_cleansing_function("my_custom_function", my_custom_function)
# ```
# 


# CELL ********************

# Registry of allowed cleansing functions.
# Built-in functions are registered below; custom functions from
# NB_FMD_CUSTOM_DQ_CLEANSING can register themselves via register_cleansing_function().
_CLEANSING_FUNCTION_REGISTRY = {}

def register_cleansing_function(name, func, overwrite=False):
    """Register a cleansing function by name so it can be invoked from metadata rules."""
    if not isinstance(name, str):
        raise TypeError("Cleansing function name must be a string.")

    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Cleansing function name must be a non-empty string.")

    if not callable(func):
        raise TypeError(
            f"Cleansing function '{normalized_name}' must be callable."
        )

    if not overwrite and normalized_name in _CLEANSING_FUNCTION_REGISTRY:
        raise ValueError(
            f"Cleansing function '{normalized_name}' is already registered. "
            "Pass overwrite=True to replace the existing registration."
        )

    _CLEANSING_FUNCTION_REGISTRY[normalized_name] = func

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

%run NB_FMD_CUSTOM_DQ_CLEANSING

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def dynamic_call_cleansing_function(df: DataFrame,
        func_name: str, 
        columns: str, 
        *args, 
        **kwargs):

    func = _CLEANSING_FUNCTION_REGISTRY.get(func_name)

    if func:
        try:
            return func(df, columns, *args, **kwargs)
        except Exception as e:
            raise ValueError(f"Function '{func_name}' failed with Error: {e}") from e
    else:
        available_functions = sorted(_CLEANSING_FUNCTION_REGISTRY.keys())
        available_message = (
            f"Available functions: {', '.join(available_functions)}"
            if available_functions
            else "No functions registered."
        )
        raise ValueError(
            f"Function '{func_name}' is not a registered cleansing function. "
            f"{available_message}"
        )

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def normalize_cleansing_rules(cleansing_rules):
    if cleansing_rules is None:
        return []

    # JSON string → Python object
    if isinstance(cleansing_rules, str):
        cleansing_rules = cleansing_rules.strip()
        if not cleansing_rules:
            return []
        cleansing_rules = json.loads(cleansing_rules)

    # Single dict → wrap in list
    if isinstance(cleansing_rules, dict):
        cleansing_rules = [cleansing_rules]

    if not isinstance(cleansing_rules, list):
        raise TypeError(
            f"cleansing_rules must be a list of dicts, got {type(cleansing_rules).__name__}"
        )

    for i, rule in enumerate(cleansing_rules):
        if not isinstance(rule, dict):
            raise TypeError(
                f"Rule at index {i} is not a dict (got {type(rule).__name__})"
            )

    return cleansing_rules

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def handle_cleansing_functions(df: DataFrame, cleansing_rules):
    cleansing_rules = normalize_cleansing_rules(cleansing_rules)

    for rule in cleansing_rules:
        function = rule.get("function")
        if not function:
            print(f"'function' missing in: {rule}")
            continue

        parameters = rule.get("parameters")
        if parameters is None:
            parameters = {}
        elif not isinstance(parameters, dict):
            raise TypeError(
                f"'parameters' must be a dict for function '{function}' (got {type(parameters).__name__})"
            )
        columns_raw = rule.get("columns")

        columns = (
            [c.strip() for c in columns_raw.split(";") if c.strip()]
            if columns_raw else []
        )

        print(
            f"\nFunction: {function}"
            f"\nParameters: {parameters}"
            f"\nColumns: {columns}"
        )

        df = dynamic_call_cleansing_function(
            df,
            function,
            columns,
            parameters
        )

    return df

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# # Cleansing functions
# 


# CELL ********************

from pyspark.sql.functions import col, trim, regexp_replace, lower, upper, initcap, when, length, lit, coalesce,to_date, to_timestamp, when
from pyspark.sql import DataFrame
from pyspark.sql.types import NumericType

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def normalize_text(df: DataFrame, columns, args):
    """
    Args (all optional in args dict):
      - case: one of {'lower','upper','title', None}  (default: None)
      - collapse_spaces: bool (default: True)
      - empty_as_null: bool (default: True)
    """
    case = args.get('case', None)
    collapse_spaces = args.get('collapse_spaces', True)
    empty_as_null = args.get('empty_as_null', True)

    for c in columns:
        expr = trim(col(c))
        if collapse_spaces:
            # Replace 2+ spaces with a single space
            expr = regexp_replace(expr, r"\s{2,}", " ")
        if case == 'lower':
            expr = lower(expr)
        elif case == 'upper':
            expr = upper(expr)
        elif case == 'title':
            expr = initcap(expr)

        if empty_as_null:
            expr = when(length(expr) == 0, lit(None)).otherwise(expr)

        df = df.withColumn(c, expr)
    return df

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def fill_nulls(df: DataFrame, columns, args):
    """
    Args:
      - defaults: dict[str, any]   -> per-column default values
      - default_string: str or None
      - default_numeric: int/float or None
      - default_date: date string in 'yyyy-MM-dd' or None
    """
    defaults = args.get('defaults', {}) or {}
    default_string = args.get('default_string', None)
    default_numeric = args.get('default_numeric', None)
    default_date = args.get('default_date', None)

    for c in columns:
        if c in defaults:
            df = df.withColumn(c, coalesce(col(c), lit(defaults[c])))
        else:
            dtype = [f.dataType for f in df.schema.fields if f.name == c]
            dtype = dtype[0] if dtype else None
            if dtype is None:
                continue

            if default_string is not None and dtype.simpleString().startswith('string'):
                df = df.withColumn(c, coalesce(col(c), lit(default_string)))
            elif default_numeric is not None and isinstance(dtype, NumericType):
                df = df.withColumn(c, coalesce(col(c), lit(default_numeric)))
            elif default_date is not None and dtype.simpleString() in ('date',):
                df = df.withColumn(c, coalesce(col(c), lit(default_date)))
    return df

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def parse_datetime(df: DataFrame, columns, args):
    """
    Args:
      - target_type: 'date'|'timestamp' (default: 'date')
      - formats: list[str] of formats, e.g. ['yyyy-MM-dd','dd/MM/yyyy','MM-dd-yyyy']
      - into: str or None  -> if provided and len(columns)==1, write into this column name
      - keep_original: bool (default: True)
    """
    target_type = args.get('target_type', 'date')
    formats = args.get('formats', ['yyyy-MM-dd'])
    into = args.get('into', None)
    keep_original = args.get('keep_original', True)

    for c in columns:
        parsed = None
        for fmt in formats:
            candidate = to_timestamp(col(c), fmt) if target_type == 'timestamp' else to_date(col(c), fmt)
            parsed = candidate if parsed is None else coalesce(parsed, candidate)

        out_col = into if (into and len(columns) == 1) else c
        df = df.withColumn(out_col, parsed)
        if into and not keep_original and out_col != c:
            df = df.drop(c)
    return df

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def exclude_rows(df: DataFrame, columns, args):
    """
    Drops the rows whose value in any of the columns is one of the given values.
    Meant as a Silver rule for a source flag such as EVENT_CRUD = 'delete': Silver then sees the key as
    absent and soft-deletes it (IsDeleted = 1, IsCurrent = 0). Do not use it as a Bronze rule: an incremental
    Bronze merge would then leave the existing row in place instead of marking it.
    Args:
      - values: non-empty list of values to drop (compared trimmed and case-insensitive)
    A NULL in a column keeps the row.
    """
    values = args.get('values')
    if isinstance(values, str):
        values = [values]
    if not values:
        raise ValueError("exclude_rows needs a non-empty 'values' list in parameters.")
    if not columns:
        raise ValueError("exclude_rows needs at least one column in 'columns'.")

    values = [str(v).strip().lower() for v in values]
    for c in columns:
        hit = coalesce(lower(trim(col(c).cast('string'))).isin(values), lit(False))
        df = df.filter(~hit)
    return df

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def clamp_min_date(df: DataFrame, columns, args):
    """
    Replaces date/timestamp values that lie below a minimum (e.g. the 0001-01-01 placeholder of a source system)
    with a replacement value. NULL stays NULL. Runs after the read, so a Spark datetime rebase of dates before
    1582 has already happened by then.
    Args:
      - min: 'yyyy-MM-dd' (default '1900-01-01')
      - replacement: 'yyyy-MM-dd' or timestamp string (default: min), cast to the column type
      - inclusive: bool (default False: value < min is replaced; True: value <= min)
    """
    from datetime import datetime

    min_value = args.get('min', '1900-01-01') or '1900-01-01'
    replacement = args.get('replacement') or min_value
    inclusive = args.get('inclusive', False)
    if isinstance(inclusive, str):
        inclusive = inclusive.strip().lower() in ('true', '1')

    # Spark casts an unparsable string to NULL, which would wipe the data: validate up front.
    datetime.strptime(str(min_value), '%Y-%m-%d')
    datetime.fromisoformat(str(replacement))
    if not columns:
        raise ValueError("clamp_min_date needs at least one column in 'columns'.")

    types = {f.name: f.dataType for f in df.schema.fields}
    for c in columns:
        if c not in types:
            raise ValueError(f"clamp_min_date: column '{c}' does not exist.")
        t = types[c].simpleString()
        if t != 'date' and not t.startswith('timestamp'):
            raise ValueError(f"clamp_min_date: column '{c}' is {t}, expected date or timestamp.")
        low = col(c) <= lit(min_value).cast(t) if inclusive else col(c) < lit(min_value).cast(t)
        df = df.withColumn(c, when(low, lit(replacement).cast(t)).otherwise(col(c)))
    return df

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Register built-in cleansing functions
register_cleansing_function("normalize_text", normalize_text)
register_cleansing_function("fill_nulls", fill_nulls)
register_cleansing_function("parse_datetime", parse_datetime)
register_cleansing_function("exclude_rows", exclude_rows)
register_cleansing_function("clamp_min_date", clamp_min_date)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
