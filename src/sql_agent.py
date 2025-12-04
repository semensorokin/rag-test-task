"""SQL generation and answer synthesis using LLM."""

import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.config import LLM_MODEL, OPENAI_API_KEY, TABLE_DESCRIPTIONS
from src.database import execute_query, get_schema_info
from src.logger import logger


def get_llm():
    """Return configured ChatOpenAI instance."""
    return ChatOpenAI(model=LLM_MODEL, api_key=OPENAI_API_KEY, temperature=0)


SQL_GENERATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a SQL expert. Generate a SQLite query to answer the user's question.

Database Schema:
{schema}

Table Descriptions:
{table_descriptions}

Rules:
1. Use only the tables and columns shown in the schema
2. For line totals with tax: quantity * unit_price * (1 + tax_rate)
3. Join clients and invoices on client_id
4. Join invoices and invoice_line_items on invoice_id
5. Return ONLY the SQL query, no explanations
6. Use strftime for date operations in SQLite""",
        ),
        ("human", "{question}"),
    ]
)


ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a helpful assistant answering questions about business data.
Based on the query results, provide a clear and accurate answer.

Rules:
1. Use ONLY the data provided in the results
2. Format numbers appropriately (currency with 2 decimals)
3. If results are empty, say no matching data was found
4. Be concise but complete""",
        ),
        (
            "human",
            """Question: {question}

SQL Query executed:
{sql_query}

Results:
{results}

Provide a natural language answer:""",
        ),
    ]
)


def analyze_sql(sql: str) -> dict:
    """
    Extract metadata from a SQL query.

    Parameters
    ----------
    sql : str
        SQL query to analyze.

    Returns
    -------
    dict
        Query metadata including tables used, join count, and flags for
        aggregation, filtering, ordering, and limits.
    """
    sql_upper = sql.upper()

    tables = []
    for table in ["clients", "invoices", "invoice_line_items"]:
        if table.upper() in sql_upper or table in sql.lower():
            tables.append(table)

    join_count = sql_upper.count("JOIN")
    has_aggregation = any(agg in sql_upper for agg in ["COUNT(", "SUM(", "AVG(", "MAX(", "MIN("])
    has_group_by = "GROUP BY" in sql_upper
    has_filter = "WHERE" in sql_upper
    has_order = "ORDER BY" in sql_upper
    has_limit = "LIMIT" in sql_upper

    query_type = "SELECT"
    if has_aggregation or has_group_by:
        query_type = "AGGREGATION"
    elif join_count > 0:
        query_type = "JOIN"

    return {
        "tables_used": tables,
        "table_count": len(tables),
        "join_count": join_count,
        "has_aggregation": has_aggregation,
        "has_group_by": has_group_by,
        "has_filter": has_filter,
        "has_order": has_order,
        "has_limit": has_limit,
        "query_type": query_type,
    }


def get_pre_aggregation_query(sql: str) -> str | None:
    """
    Generate a query to fetch raw data before aggregation.

    Parameters
    ----------
    sql : str
        Original aggregation query.

    Returns
    -------
    str or None
        Modified query without aggregation, or None if not applicable.
    """
    sql_upper = sql.upper()

    if "GROUP BY" not in sql_upper:
        return None

    try:
        from_match = re.search(
            r"FROM\s+(.+?)(?:\sGROUP BY|\sORDER BY|\sLIMIT|;|$)",
            sql,
            re.IGNORECASE | re.DOTALL,
        )

        if not from_match:
            return None

        from_clause = from_match.group(1).strip()
        pre_agg_sql = f"SELECT * FROM {from_clause} LIMIT 100"
        pre_agg_sql = re.sub(r"\s+", " ", pre_agg_sql).strip()

        return pre_agg_sql

    except Exception as e:
        logger.warning(f"Could not generate pre-aggregation query: {e}")
        return None


def generate_sql(question: str) -> str:
    """
    Generate SQL query from natural language question.

    Parameters
    ----------
    question : str
        User's question in natural language.

    Returns
    -------
    str
        Generated SQL query.
    """
    logger.info("Generating SQL query...")
    llm = get_llm()
    schema = get_schema_info()

    table_desc = "\n".join([f"- {name}: {desc}" for name, desc in TABLE_DESCRIPTIONS.items()])

    chain = SQL_GENERATION_PROMPT | llm | StrOutputParser()

    sql = chain.invoke(
        {
            "schema": schema,
            "table_descriptions": table_desc,
            "question": question,
        }
    )

    sql = sql.strip().replace("```sql", "").replace("```", "").strip()
    logger.info(f"Generated SQL: {sql[:100]}...")
    return sql


def execute_and_answer(question: str) -> dict:
    """
    Generate SQL, execute it, and produce a natural language answer.

    Parameters
    ----------
    question : str
        User's question.

    Returns
    -------
    dict
        Contains question, sql_query, results, row_count, col_count,
        answer, analysis, and intermediate data (if aggregation).
    """
    sql_query = generate_sql(question)
    sql_analysis = analyze_sql(sql_query)

    logger.info(
        f"Query analysis: {sql_analysis['table_count']} table(s), "
        f"{sql_analysis['join_count']} join(s), type: {sql_analysis['query_type']}"
    )

    intermediate_results = None

    if sql_analysis["query_type"] == "AGGREGATION":
        intermediate_query = get_pre_aggregation_query(sql_query)
        if intermediate_query:
            try:
                logger.info(f"Fetching intermediate results: {intermediate_query[:80]}...")
                intermediate_df = execute_query(intermediate_query)
                intermediate_results = {
                    "query": intermediate_query,
                    "data": intermediate_df.to_dict(orient="records"),
                    "row_count": len(intermediate_df),
                    "col_count": len(intermediate_df.columns),
                }
                logger.info(f"Intermediate results: {len(intermediate_df)} rows")
            except Exception as e:
                logger.warning(f"Could not fetch intermediate results: {e}")

    try:
        logger.info("Executing SQL query...")
        results_df = execute_query(sql_query)
        row_count = len(results_df)
        col_count = len(results_df.columns) if not results_df.empty else 0
        results_str = results_df.to_string(index=False) if not results_df.empty else "No results"
        logger.info(f"Query returned {row_count} row(s), {col_count} column(s)")
    except Exception as e:
        logger.error(f"SQL execution error: {e}")
        return {
            "question": question,
            "sql_query": sql_query,
            "error": str(e),
            "answer": f"Error executing query: {str(e)}",
            "analysis": sql_analysis,
        }

    logger.info("Generating natural language answer...")
    llm = get_llm()
    chain = ANSWER_PROMPT | llm | StrOutputParser()

    answer = chain.invoke(
        {
            "question": question,
            "sql_query": sql_query,
            "results": results_str,
        }
    )

    return {
        "question": question,
        "sql_query": sql_query,
        "results": results_df.to_dict(orient="records"),
        "row_count": row_count,
        "col_count": col_count,
        "answer": answer,
        "analysis": sql_analysis,
        "intermediate": intermediate_results,
    }
