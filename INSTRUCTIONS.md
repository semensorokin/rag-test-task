# RAG Chat for Tabular Data - Setup & Documentation

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key

### Setup

1. **Create conda environment:**
```bash
conda create -n rag-chat python=3.11 -y
conda activate rag-chat
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

4. **Run the app:**
```bash
streamlit run app.py
```

### Docker (Alternative)

```bash
cp .env.example .env
# Edit .env with your OPENAI_API_KEY
docker-compose up --build
```

Access at `http://localhost:8501`

## Architecture

```
User Question
      │
      ▼
┌─────────────────────────────────────┐
│  SQL Generation (LLM)               │
│  - Full table schemas               │
│  - Column types + sample data       │
│  - Table descriptions               │
│  - Question → SQL query             │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  SQLite Database                    │
│  (Excel data loaded at startup)     │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Answer Generation (LLM)            │
│  Query results → Natural language   │
└─────────────────────────────────────┘
```

### Components

| File | Purpose |
|------|---------|
| `src/config.py` | Configuration and environment |
| `src/database.py` | Excel → SQLite + query execution |
| `src/sql_agent.py` | SQL generation + answer synthesis |
| `src/chain.py` | Pipeline orchestration + stats |
| `src/logger.py` | Terminal logging |
| `app.py` | Streamlit UI (Chat + Statistics tabs) |

### How It Works

1. **Startup**: Excel files loaded into SQLite database
2. **Query**: User question sent to LLM with full schema context
3. **SQL Generation**: LLM generates SQL based on schema + question
4. **Execution**: SQL runs against SQLite
5. **Answer**: LLM converts query results to natural language

## Hallucination Mitigation

- **Text-to-SQL**: All numbers come directly from database queries
- **Full schema context**: LLM receives complete table schemas + sample data
- **Result grounding**: Answer LLM only uses actual query results
- **Transparent SQL**: Users can view executed queries

## Assumptions & Limitations

### Assumptions

- Data fits in memory (SQLite sufficient)
- Excel files follow expected schema
- Line total: `quantity * unit_price * (1 + tax_rate)`

### Limitations

- Single-turn conversations only
- No query validation before execution

## LangSmith Integration

Add to `.env`:
```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=rag-tabular-chat
```

## Project Structure

```
.
├── app.py                 # Streamlit (Chat + Statistics tabs)
├── src/
│   ├── config.py          # Configuration
│   ├── database.py        # Database operations  
│   ├── sql_agent.py       # SQL generation + answers
│   ├── chain.py           # Pipeline orchestration
│   └── logger.py          # Terminal logging
├── data/
│   ├── Clients.xlsx
│   ├── Invoices.xlsx
│   └── InvoiceLineItems.xlsx
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── TEST_RESULTS.md
├── INSTRUCTIONS.md        # This file
└── README.MD              # Original task description
```
