"""
Configuration settings for the RAG pipeline.

Loads environment variables and defines paths, model settings, and table metadata.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "database.db"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = "gpt-4o-mini"

TABLE_FILES = {
    "clients": DATA_DIR / "Clients.xlsx",
    "invoices": DATA_DIR / "Invoices.xlsx",
    "invoice_line_items": DATA_DIR / "InvoiceLineItems.xlsx",
}

TABLE_DESCRIPTIONS = {
    "clients": (
        "Contains client information including client_id (primary key), "
        "client_name, industry, and country."
    ),
    "invoices": (
        "Contains invoice records with invoice_id (primary key), client_id (foreign key), "
        "invoice_date, due_date, status (Paid/Overdue/Draft), currency, and fx_rate_to_usd."
    ),
    "invoice_line_items": (
        "Contains line items for invoices with line_id (primary key), invoice_id (foreign key), "
        "service_name, quantity, unit_price, and tax_rate. "
        "Line total with tax = quantity * unit_price * (1 + tax_rate)."
    ),
}
