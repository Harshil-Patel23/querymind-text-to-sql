# 🧠 Text to SQL

A powerful Streamlit-based web application that converts natural language questions into SQL queries using the **Groq LLM API** (Llama 3.1). Ask questions about your database in plain English, and the app generates, validates, and executes the appropriate SQL query — complete with auto-visualizations and an interactive schema explorer.

## 🎬 Live Demo

> **Demo Application**: [Text to SQL on Streamlit Cloud](https://querymindtexttosql.streamlit.app/)
>
> Try asking questions like:
>
> - "Show me all employees in the sales department"
> - "What is the average salary by department?"
> - "Which employee has the highest salary?"

## ✨ Features

- **Natural Language to SQL** — Convert plain English questions into SQL queries powered by Groq's Llama 3.1 model
- **Multi-Database Support** — Connect to **SQLite**, **PostgreSQL**, or **MySQL** databases
- **Database Discovery** — Auto-discover available databases on a server or SQLite files in a folder
- **Interactive Schema Explorer** — Browse tables, columns, primary keys, foreign keys, and data types
- **ER Diagram** — Visual entity-relationship diagram rendered with Plotly
- **Auto Visualization** — Automatically generates the best chart (bar, line, scatter, histogram) based on query results
- **Query History** — Re-run past queries from the sidebar with one click
- **Editable SQL** — Review and edit generated SQL before executing
- **Error Explanation** — AI-powered plain-English explanations when a query fails
- **Query Safety** — Blocks dangerous operations (DROP, DELETE, TRUNCATE, ALTER, INSERT, UPDATE, CREATE)
- **CSV Export** — Download query results as CSV

## 📋 Prerequisites

- Python 3.10+
- A [Groq API key](https://console.groq.com/) (free tier available)
- Database access credentials (SQLite file path, or PostgreSQL/MySQL connection details)

## 🚀 Installation

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd APP_TEXT_TO_SQL
   ```

2. **Create a virtual environment** (recommended):

   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:

   Create a `.env` file in the project root:

   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

## 💻 Usage

1. **Start the app**:

   ```bash
   streamlit run app.py
   ```

2. **Connect to a database** (sidebar):
   - Select your database type (SQLite, PostgreSQL, or MySQL)
   - For **SQLite**: point to a folder and click **Discover**, or enter a file path manually
   - For **PostgreSQL / MySQL**: enter host, port, username, password, then click **Discover** to list databases
   - Click **🔗 Connect**

3. **Ask questions**:
   - Switch to the **🔍 Query** tab
   - Type a question like *"Which department has the highest average salary?"*
   - Click **⚡ Generate SQL** → review/edit → **▶️ Run Query**
   - View results, auto-generated charts, and download as CSV

4. **Explore the schema**:
   - Switch to the **🗄️ Schema Explorer** tab
   - View the ER diagram and browse detailed table definitions

## 📁 Project Structure

```
APP_TEXT_TO_SQL/
├── app.py                # Main Streamlit application (UI, tabs, charts)
├── llm_engine.py         # Groq LLM integration and SQL generation
├── db_manager.py         # Connection string builder for all DB types
├── db_discovery.py       # Auto-discover databases and SQLite files
├── schema_extractor.py   # Schema extraction (text + structured) via SQLAlchemy
├── sql_executor.py       # Safe query execution with keyword blocking
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (GROQ_API_KEY)
├── .streamlit/
│   └── config.toml       # Streamlit theme configuration
├── sample_data/
│   ├── company.db        # Sample SQLite database
│   └── sakila.db         # Sakila sample database
├── LICENSE               # MIT License
└── README.md             # This file
```

## 🔧 Core Modules

| Module | Description |
|---|---|
| **`app.py`** | Main Streamlit app — sidebar connection panel, Query tab, Schema Explorer tab, auto-visualization, ER diagram, and query history |
| **`llm_engine.py`** | Sends prompts to the Groq API (Llama 3.1), cleans/validates output, retries on validation failures, and explains query errors |
| **`db_manager.py`** | Builds SQLAlchemy connection strings for SQLite, PostgreSQL, and MySQL |
| **`db_discovery.py`** | Lists databases on PostgreSQL/MySQL servers and scans folders for SQLite files |
| **`schema_extractor.py`** | Extracts schema as plain text (for the LLM) and as a structured dict (for the Schema Explorer UI) |
| **`sql_executor.py`** | Runs SQL via SQLAlchemy with blocked-keyword safety checks using `sqlparse` |

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | Web UI framework |
| `groq` | Groq cloud LLM API client |
| `sqlalchemy` | Database abstraction layer |
| `pandas` | Data manipulation and display |
| `plotly` | Interactive charts and ER diagrams |
| `sqlparse` | SQL statement parsing and validation |
| `python-dotenv` | Load environment variables from `.env` |
| `pymysql` | MySQL driver |
| `psycopg2-binary` | PostgreSQL driver |

## 🛡️ Security Features

- **Keyword Blocking** — Dangerous SQL keywords (`DROP`, `DELETE`, `TRUNCATE`, `ALTER`, `INSERT`, `UPDATE`, `CREATE`) are rejected before execution
- **SELECT-Only Enforcement** — Queries are parsed with `sqlparse` to verify they are SELECT statements
- **Fan-Out Detection** — LLM-level validation catches potential aggregation bugs when joining multiple fact tables
- **API Key Protection** — Credentials loaded from `.env` / Streamlit secrets, never hardcoded

## 🗄️ Sample Data

The project ships with two SQLite databases in `sample_data/`:

- **`company.db`** — A small database with `employees` and `sales` tables (great for quick testing)
- **`sakila.db`** — The classic Sakila sample database with a rich schema of films, actors, customers, rentals, etc.

## 🐛 Troubleshooting

| Issue | Solution |
|---|---|
| `GROQ_API_KEY not found` | Add your API key to the `.env` file or Streamlit Cloud secrets |
| "Connection failed" | Verify database credentials and ensure the database server is running |
| "Query contains blocked keyword" | Only SELECT queries are allowed; the query attempted a write operation |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` to install all dependencies |
| No databases discovered | Check that the server is reachable and credentials have sufficient permissions |

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
