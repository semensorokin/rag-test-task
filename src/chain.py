"""RAG pipeline orchestration and statistics tracking."""

import os
import time

from src.database import DB_PATH, init_database
from src.logger import logger
from src.sql_agent import execute_and_answer


class RAGPipeline:
    """
    Main pipeline for processing natural language queries over tabular data.

    Handles initialization, query execution, and statistics collection.
    """

    def __init__(self):
        self._initialized = False
        self.last_query_info = None
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "total_response_time": 0,
            "query_history": [],
        }

    def initialize(self):
        """Initialize database if needed. Idempotent."""
        if self._initialized:
            return

        logger.info("Initializing RAG pipeline...")

        if not os.path.exists(DB_PATH):
            logger.info("Creating SQLite database from Excel files...")
            init_database()
            logger.info("Database initialized successfully")
        else:
            logger.info("Using existing database")

        self._initialized = True
        logger.info("Pipeline ready")

    def query(self, question: str) -> dict:
        """
        Process a natural language question.

        Parameters
        ----------
        question : str
            User's question about the data.

        Returns
        -------
        dict
            Result containing answer, SQL query, raw results, and metadata.
        """
        if not self._initialized:
            self.initialize()

        start_time = time.time()
        self.stats["total_queries"] += 1

        logger.info(f"Processing query: {question[:100]}...")

        try:
            result = execute_and_answer(question)
            self.stats["successful_queries"] += 1
            logger.info("Query executed successfully")
        except Exception as e:
            self.stats["failed_queries"] += 1
            logger.error(f"Query failed: {e}")
            raise

        elapsed = time.time() - start_time
        self.stats["total_response_time"] += elapsed

        result["response_time"] = elapsed

        query_record = {
            "question": question,
            "response_time": elapsed,
            "success": "error" not in result,
            "row_count": result.get("row_count", 0),
            "col_count": result.get("col_count", 0),
            "analysis": result.get("analysis", {}),
            "intermediate": result.get("intermediate"),
            "sql_query": result.get("sql_query", ""),
        }

        self.stats["query_history"].append(query_record)
        self.last_query_info = query_record

        logger.info(f"Response generated in {elapsed:.2f}s")

        return result

    def get_stats(self) -> dict:
        """
        Get pipeline statistics.

        Returns
        -------
        dict
            Statistics including query counts, timing, and history.
        """
        avg_time = (
            self.stats["total_response_time"] / self.stats["total_queries"]
            if self.stats["total_queries"] > 0
            else 0
        )
        return {
            **self.stats,
            "avg_response_time": avg_time,
            "last_query": self.last_query_info,
        }


pipeline = RAGPipeline()


def ask(question: str) -> dict:
    """
    Query the pipeline with a natural language question.

    Parameters
    ----------
    question : str
        User's question.

    Returns
    -------
    dict
        Query result with answer and metadata.
    """
    return pipeline.query(question)


def get_pipeline_stats() -> dict:
    """Return current pipeline statistics."""
    return pipeline.get_stats()
