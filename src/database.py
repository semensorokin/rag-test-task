"""Database operations for loading Excel data into SQLite and executing queries."""

import pandas as pd
from sqlalchemy import create_engine, text

from src.config import DB_PATH, TABLE_FILES


def get_engine():
    """
    Create SQLAlchemy engine for the SQLite database.

    Returns
    -------
    sqlalchemy.Engine
        Database engine instance.
    """
    return create_engine(f"sqlite:///{DB_PATH}")


def init_database():
    """
    Load all Excel files into SQLite tables.

    Reads each Excel file defined in TABLE_FILES and creates
    corresponding tables in the SQLite database.
    """
    engine = get_engine()

    for table_name, file_path in TABLE_FILES.items():
        df = pd.read_excel(file_path)
        df.to_sql(table_name, engine, if_exists="replace", index=False)


def execute_query(query: str) -> pd.DataFrame:
    """
    Execute a SQL query and return results as DataFrame.

    Parameters
    ----------
    query : str
        SQL query string to execute.

    Returns
    -------
    pd.DataFrame
        Query results.
    """
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(query))
        columns = result.keys()
        rows = result.fetchall()
    return pd.DataFrame(rows, columns=columns)


def get_schema_info() -> str:
    """
    Generate schema information string for all tables.

    Returns
    -------
    str
        Formatted string with table names, column types, and sample data.
    """
    engine = get_engine()
    schema_parts = []

    for table_name in TABLE_FILES.keys():
        df = pd.read_sql(f"SELECT * FROM {table_name} LIMIT 3", engine)
        columns = df.dtypes.to_dict()

        col_info = ", ".join([f"{col} ({dtype})" for col, dtype in columns.items()])
        sample_data = df.to_string(index=False)

        schema_parts.append(
            f"Table: {table_name}\nColumns: {col_info}\nSample rows:\n{sample_data}"
        )

    return "\n\n".join(schema_parts)
