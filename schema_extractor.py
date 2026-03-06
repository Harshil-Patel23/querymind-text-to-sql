from sqlalchemy import create_engine, inspect
from functools import lru_cache


@lru_cache(maxsize=10)
def extract_schema(connection_string: str) -> str:
    """Original function — returns plain text schema for the LLM. Unchanged."""
    engine = create_engine(connection_string)
    inspector = inspect(engine)
    schema_parts = []

    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        col_defs = ", ".join([f"{col['name']} ({col['type']})" for col in columns])
        schema_parts.append(f"Table: {table_name}\nColumns: {col_defs}")

    return "\n\n".join(schema_parts)


def extract_schema_structured(connection_string: str) -> dict:
    """
    Returns a structured dict used by the visual Schema Explorer tab.
    {
      "table_name": {
        "columns": [{"name": ..., "type": ..., "primary_key": ..., "nullable": ...}],
        "foreign_keys": [{"column": ..., "ref_table": ..., "ref_column": ...}]
      }
    }
    """
    engine = create_engine(connection_string)
    inspector = inspect(engine)
    schema = {}

    # Get primary keys per table first
    for table_name in inspector.get_table_names():
        pk_cols = set(inspector.get_pk_constraint(table_name).get("constrained_columns", []))
        columns = []
        for col in inspector.get_columns(table_name):
            columns.append({
                "name":        col["name"],
                "type":        str(col["type"]),
                "primary_key": col["name"] in pk_cols,
                "nullable":    col.get("nullable", True),
            })

        foreign_keys = []
        for fk in inspector.get_foreign_keys(table_name):
            for local_col, ref_col in zip(fk["constrained_columns"], fk["referred_columns"]):
                foreign_keys.append({
                    "column":     local_col,
                    "ref_table":  fk["referred_table"],
                    "ref_column": ref_col,
                })

        schema[table_name] = {
            "columns":      columns,
            "foreign_keys": foreign_keys,
        }

    return schema