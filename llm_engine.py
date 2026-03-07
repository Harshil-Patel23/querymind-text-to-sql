import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Client setup — reads key from .env locally, or st.secrets on Streamlit Cloud
# ---------------------------------------------------------------------------
# In your .env file add:  GROQ_API_KEY=your_key_here
# On Streamlit Cloud add it under: Settings → Secrets

_api_key = os.environ.get("GROQ_API_KEY")
if not _api_key:
    raise EnvironmentError(
        "GROQ_API_KEY not found. "
        "Add it to your .env file locally, or to Streamlit Cloud secrets."
    )

_client = Groq(api_key=_api_key)

# Model to use — llama3-70b-8192 is free, fast, and excellent at SQL

# _MODEL = "llama-3.1-8b-instant"
_MODEL = "llama-3.3-70b-versatile"  

# ---------------------------------------------------------------------------
# Public function — same signature as before, drop-in replacement
# ---------------------------------------------------------------------------
def generate_sql(user_question: str, schema: str, dialect: str = "SQLite", max_retries: int = 2) -> str:
    """
    Convert a natural language question into a SQL query using Groq LLM.
    Retries up to max_retries times if the output fails validation.
    """
    prompt = f"""
You are an expert SQL assistant specialized in data accuracy.

TASK:
Generate a {dialect} SQL query to answer the user question based ONLY on the provided schema.

DATABASE SCHEMA:
{schema}

CRITICAL ACCURACY RULES:
1. FAN-OUT PREVENTION: If the query requires aggregating data (SUM, COUNT, etc.) from two or more independent child tables (e.g., Orders and Payments), you MUST aggregate each table in a separate CTE or Subquery BEFORE joining them to the parent table.
2. JOIN LOGIC: Ensure JOIN keys are correct. Use LEFT JOIN if the user implies including records that might not have matches in child tables.
3. ALIASING: Use clear table aliases (e.g., 'c' for customers).

OUTPUT RULES:
- Return ONLY the raw SQL code.
- No markdown code blocks (no ```sql).
- No explanations or prose.

USER QUESTION:
{user_question}

SQL QUERY:"""

    # Initial generation
    sql = _call_groq(prompt)
    sql = _clean_sql_output(sql)

    # Retry loop — same logic as before, now using Groq
    for attempt in range(max_retries):
        error = _validate_sql(sql)
        if error is None:
            break  # SQL passed validation, done

        fix_prompt = f"""
The following {dialect} SQL query has an error: {error}

Failed query:
{sql}

Schema:
{schema}

Fix the query and return ONLY the corrected SQL, no explanation, no markdown.
"""
        sql = _call_groq(fix_prompt)
        sql = _clean_sql_output(sql)

    return sql


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _call_groq(prompt: str) -> str:
    """Send a prompt to Groq and return the response text."""
    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are an expert SQL assistant. Return only valid SQL queries, no explanations."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,   # Low temperature = more deterministic SQL output
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


def _clean_sql_output(text: str) -> str:
    """
    Removes markdown fences, language tags, and surrounding junk.
    Returns the raw SQL string.
    """
    if not text:
        return text

    t = text.strip()

    # Remove ```sql ... ``` or ``` ... ```
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)

    # Remove leading/trailing backticks just in case
    t = t.strip("`").strip()

    return t


def _validate_sql(sql: str) -> str | None:
    """
    Lightweight client-side SQL check before hitting the database.
    Returns an error message string if invalid, or None if it looks fine.
    """
    if not sql:
        return "Query is empty."

    if any(sql.upper().startswith(kw) for kw in ["SELECT", "WITH", "EXPLAIN"]):
        return None  # looks like a valid read query

    # Catches cases where LLM returns explanation text instead of SQL
    if not any(kw in sql.upper() for kw in ["SELECT", "WITH", "SHOW", "DESCRIBE"]):
        return f"Response doesn't appear to be a SQL query: '{sql[:80]}'"

    fanout_error = _detect_fanout_aggregation(sql)
    if fanout_error:
        return fanout_error

    return None


def _detect_fanout_aggregation(sql: str) -> str | None:

    """
    Detects potential fan-out aggregation bugs where multiple fact tables
    are joined with COUNT/SUM without DISTINCT or subqueries.
    """
    s = sql.upper()

    has_orders = " ORDERS " in s
    has_payments = " PAYMENTS " in s
    has_orderdetails = " ORDERDETAILS " in s

    fact_tables = sum([has_orders, has_payments, has_orderdetails])

    has_count = "COUNT(" in s
    has_sum = "SUM(" in s
    has_distinct = "DISTINCT" in s

    if fact_tables >= 2 and (has_count or has_sum) and not has_distinct:
        return (
            "Potential fan-out aggregation detected: multiple fact tables joined "
            "with COUNT/SUM but no DISTINCT or subquery."
        )

    return None


def explain_error(sql: str, error: str) -> str:
    """
    Takes a failed SQL query and its database error message,
    and returns a plain English explanation of what went wrong.
    """
    prompt = f"""A SQL query failed with the following error.

SQL query:
{sql}

Error message:
{error}

In 1-2 sentences, explain in plain English what went wrong and how the user can fix it.
Do not repeat the SQL or the raw error. Be concise and helpful.
"""
    return _call_groq(prompt)