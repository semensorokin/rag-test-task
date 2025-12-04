import pandas as pd
from sqlalchemy import create_engine, text
from src.config import TABLE_FILES, DB_PATH


def get_engine():
    return create_engine(f"sqlite:///{DB_PATH}")


def init_database():
    engine = get_engine()
    
    for table_name, file_path in TABLE_FILES.items():
        df = pd.read_excel(file_path)
        df.to_sql(table_name, engine, if_exists="replace", index=False)
    
    return engine


def execute_query(query: str) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(query))
        columns = result.keys()
        rows = result.fetchall()
    return pd.DataFrame(rows, columns=columns)


def get_schema_info() -> str:
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

