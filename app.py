import streamlit as st
from datetime import datetime
from io import BytesIO
import os
import plotly.express as px
import plotly.graph_objects as go
from db_manager import build_connection_string
from schema_extractor import extract_schema, extract_schema_structured
from llm_engine import generate_sql, explain_error
from sql_executor import run_query
from db_discovery import list_databases, list_sqlite_databases
# At the top of the file, add this import alongside the existing ones:
from datetime import datetime
import pytz



# ---------------------------------------------------------------------------
# Auto-visualization: picks the best chart based on the DataFrame shape
# ---------------------------------------------------------------------------
def auto_visualize(df):
    if df.empty or len(df.columns) < 2:
        return  # Nothing useful to chart

    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include="object").columns.tolist()
    date_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()

    # Also treat string columns that look like dates
    for col in cat_cols:
        try:
            import pandas as pd
            df[col] = pd.to_datetime(df[col])
            date_cols.append(col)
            cat_cols.remove(col)
        except Exception:
            pass

    st.subheader("📊 Auto Visualization")

    # Time series: date + at least one numeric
    if date_cols and num_cols:
        fig = px.line(df, x=date_cols[0], y=num_cols[0],
                      title=f"{num_cols[0]} over time")
        st.plotly_chart(fig, use_container_width=True)

    # 1 category + 1 numeric → bar chart (best for comparisons)
    elif len(cat_cols) >= 1 and len(num_cols) >= 1:
        # Only show top 20 to keep chart readable
        plot_df = df.nlargest(20, num_cols[0]) if len(df) > 20 else df
        fig = px.bar(plot_df, x=cat_cols[0], y=num_cols[0],
                     title=f"{num_cols[0]} by {cat_cols[0]}",
                     text_auto=True)
        fig.update_layout(xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

    # 2+ numerics → scatter plot
    elif len(num_cols) >= 2:
        fig = px.scatter(df, x=num_cols[0], y=num_cols[1],
                         title=f"{num_cols[0]} vs {num_cols[1]}")
        st.plotly_chart(fig, use_container_width=True)

    # Single numeric column → histogram
    elif len(num_cols) == 1:
        fig = px.histogram(df, x=num_cols[0],
                           title=f"Distribution of {num_cols[0]}")
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No suitable columns found for visualization.")


# ---------------------------------------------------------------------------
# ER Diagram: renders tables as nodes, foreign keys as edges using Plotly
# ---------------------------------------------------------------------------
def build_er_diagram(schema: dict):
    import math

    tables = list(schema.keys())
    n = len(tables)
    if n == 0:
        st.info("No tables found.")
        return

    # Place tables in a circle so they don't overlap
    radius = max(2, n * 0.6)
    positions = {}
    for i, table in enumerate(tables):
        angle = 2 * math.pi * i / n
        positions[table] = (radius * math.cos(angle), radius * math.sin(angle))

    # Build edge traces (foreign key relationships)
    edge_traces = []
    edge_label_traces = []
    for table, info in schema.items():
        for fk in info["foreign_keys"]:
            ref = fk["ref_table"]
            if ref not in positions:
                continue
            x0, y0 = positions[table]
            x1, y1 = positions[ref]
            edge_traces.append(go.Scatter(
                x=[x0, x1, None], y=[y0, y1, None],
                mode="lines",
                line=dict(width=1.5, color="#888"),
                hoverinfo="none",
                showlegend=False,
            ))
            # Label in the middle of the edge
            edge_label_traces.append(go.Scatter(
                x=[(x0 + x1) / 2], y=[(y0 + y1) / 2],
                mode="text",
                text=[f"{fk['column']} → {fk['ref_column']}"],
                textfont=dict(size=9, color="#555"),
                hoverinfo="none",
                showlegend=False,
            ))

    # Build node traces (one per table)
    # node_x, node_y, node_text, node_hover = [], [], [], []
    # for table in tables:
    #     x, y = positions[table]
    #     node_x.append(x)
    #     node_y.append(y)
    #     node_text.append(f"<b>{table}</b>")
    #     # Hover shows all columns
    #     cols = schema[table]["columns"]
    #     col_lines = []
    #     for c in cols:
    #         prefix = "🔑 " if c["primary_key"] else "   "
    #         col_lines.append(f"{prefix}{c['name']} ({c['type']})")
    #     node_hover.append("<br>".join(col_lines))

    # node_trace = go.Scatter(
    #     x=node_x, y=node_y,
    #     mode="markers+text",
    #     marker=dict(size=36, color="#4C78A8", line=dict(width=2, color="white")),
    #     text=node_text,
    #     textposition="middle center",
    #     textfont=dict(size=11, color="#ffffff"),
    #     hovertext=node_hover,
    #     hoverinfo="text",
    #     showlegend=False,
    # )
    # Build node traces (one per table)
    node_x, node_y, node_text, node_hover = [], [], [], []
    for table in tables:
        x, y = positions[table]
        node_x.append(x)
        node_y.append(y)
        # Wrap long names: split into two lines if > 10 chars
        if len(table) > 10:
            mid = len(table) // 2
            # Find nearest space or just split at mid
            split_at = table.rfind("_", 0, mid + 1)
            if split_at == -1:
                split_at = mid
            wrapped = table[:split_at] + "<br>" + table[split_at:].lstrip("_")
        else:
            wrapped = table
        node_text.append(f"<b>{wrapped}</b>")
        # Hover shows all columns
        cols = schema[table]["columns"]
        col_lines = []
        for c in cols:
            prefix = "🔑 " if c["primary_key"] else "   "
            col_lines.append(f"{prefix}{c['name']} ({c['type']})")
        node_hover.append("<br>".join(col_lines))

    # Dynamically size each marker so the name fits inside
    marker_sizes = []
    for table in tables:
        marker_sizes.append(max(60, min(120, len(table) * 9)))

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        marker=dict(
            size=marker_sizes,
            color="#4C78A8",
            line=dict(width=2, color="white"),
            sizemode="diameter",
        ),
        text=node_text,
        textposition="middle center",
        textfont=dict(size=11, color="#ffffff"),
        hovertext=node_hover,
        hoverinfo="text",
        showlegend=False,
    )

    fig = go.Figure(
        data=edge_traces + edge_label_traces + [node_trace],
        layout=go.Layout(
            title="Entity Relationship Diagram",
            title_font_size=16,
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=520,
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(color="#333333"),
        )
    )
    st.plotly_chart(fig, use_container_width=True)

st.set_page_config(page_title="QueryMind: Natural Language to SQL", page_icon="🧠", layout="wide")
st.title("🧠 QueryMind: Natural Language to SQL")

# ---------------------------------------------------------------------------
# Initialize query history in session state (persists for the whole session)
# ---------------------------------------------------------------------------
if "query_history" not in st.session_state:
    st.session_state["query_history"] = []


# ---------------------------------------------------------------------------
# Helper: clear stale session state when the DB type changes
# ---------------------------------------------------------------------------
def _clear_discovery_state():
    for key in ("sqlite_dbs", "available_dbs", "schema", "conn_str",
                "db_type", "generated_sql", "_manual_conn_str"):
        st.session_state.pop(key, None)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("🔌 Database Connection")

    db_type = st.selectbox("Database Type", ["sqlite", "postgresql", "mysql"])

    # Wipe discovery/connection state whenever the user picks a different type
    if db_type != st.session_state.get("_db_type_ui"):
        _clear_discovery_state()
        st.session_state["_db_type_ui"] = db_type

    # ------------------------------------------------------------------
    # SQLite
    # ------------------------------------------------------------------
    if db_type == "sqlite":
        folder_path = st.text_input("SQLite Folder Path", value="sample_data/")

        # Wipe cached list if the folder path changes
        if folder_path != st.session_state.get("_sqlite_folder"):
            st.session_state.pop("sqlite_dbs", None)
            st.session_state["_sqlite_folder"] = folder_path

        discover_btn = st.button("🔍 Discover Databases")
        if discover_btn:
            try:
                found = list_sqlite_databases(folder_path)
                st.session_state["sqlite_dbs"] = found if found else []
            except Exception as e:
                st.error(f"Discovery failed: {e}")
                st.session_state["sqlite_dbs"] = []

        # Always initialise conn_str so it is never undefined below
        conn_str = None

        if "sqlite_dbs" in st.session_state:
            if st.session_state["sqlite_dbs"]:
                db_paths = st.session_state["sqlite_dbs"]
                db_names = [os.path.basename(p) for p in db_paths]
                selected_name = st.selectbox("Select SQLite Database", db_names)
                selected_db = db_paths[db_names.index(selected_name)]
                conn_str = build_connection_string(
                    "sqlite", None, None, None, None, None, selected_db
                )
            else:
                st.warning("No .db / .sqlite files found in that folder.")

        # Always offer a manual override so the user is never stuck
        with st.expander("Or enter file path manually"):
            manual_path = st.text_input(
                "SQLite File Path", value="sample_data/company.db", key="sqlite_manual"
            )
            if st.button("Use this path", key="use_manual_path"):
                conn_str = build_connection_string(
                    "sqlite", None, None, None, None, None, manual_path
                )
                st.session_state["_manual_conn_str"] = conn_str

        # Prefer explicitly chosen conn_str; fall back to manually stored one
        if conn_str is None:
            conn_str = st.session_state.get("_manual_conn_str")

    # ------------------------------------------------------------------
    # MySQL
    # ------------------------------------------------------------------
    elif db_type == "mysql":
        host     = st.text_input("Host", value="localhost")
        port     = st.number_input("Port", value=3306, step=1)
        user     = st.text_input("Username", value="root")
        password = st.text_input("Password", type="password")

        discover_btn = st.button("🔍 Discover Databases")
        if discover_btn:
            try:
                temp_conn = build_connection_string(
                    "mysql", host, int(port), user, password, "mysql"
                )
                dbs = list_databases(temp_conn)
                system_dbs = {"information_schema", "performance_schema", "sys", "mysql"}
                st.session_state["available_dbs_mysql"] = (
                    [d for d in dbs if d not in system_dbs] or dbs
                )
            except Exception as e:
                st.error(f"Discovery failed: {e}")
                st.session_state["available_dbs_mysql"] = []

        if st.session_state.get("available_dbs_mysql"):
            dbname = st.selectbox("Select Database", st.session_state["available_dbs_mysql"])
        else:
            dbname = st.text_input("Database Name")

        conn_str = (
            build_connection_string(db_type, host, int(port), user, password, dbname)
            if dbname else None
        )

    # ------------------------------------------------------------------
    # PostgreSQL
    # ------------------------------------------------------------------
    else:
        host     = st.text_input("Host", value="localhost")
        port     = st.number_input("Port", value=5432, step=1)
        user     = st.text_input("Username")
        password = st.text_input("Password", type="password")

        discover_btn = st.button("🔍 Discover Databases")
        if discover_btn:
            try:
                temp_conn = build_connection_string(
                    "postgresql", host, int(port), user, password, "postgres"
                )
                dbs = list_databases(temp_conn)
                system_dbs = {"template0", "template1"}
                st.session_state["available_dbs_pg"] = (
                    [d for d in dbs if d not in system_dbs] or dbs
                )
            except Exception as e:
                st.error(f"Discovery failed: {e}")
                st.session_state["available_dbs_pg"] = []

        if st.session_state.get("available_dbs_pg"):
            dbname = st.selectbox("Select Database", st.session_state["available_dbs_pg"])
        else:
            dbname = st.text_input("Database Name")

        conn_str = (
            build_connection_string(db_type, host, int(port), user, password, dbname)
            if dbname else None
        )

    # ------------------------------------------------------------------
    # Connect button — shared across all DB types
    # ------------------------------------------------------------------
    st.divider()
    connect_btn = st.button("🔗 Connect", type="primary", use_container_width=True)
    if connect_btn:
        if not conn_str:
            st.warning("Please select or enter a database before connecting.")
        else:
            with st.spinner("Connecting…"):
                try:
                    schema = extract_schema(conn_str)
                    st.session_state.pop("generated_sql", None)
                    st.session_state["schema"]   = schema
                    st.session_state["conn_str"] = conn_str
                    st.session_state["db_type"]  = db_type
                    st.success("✅ Connected!")
                except Exception as e:
                    st.error(f"Connection failed: {e}")

    # ------------------------------------------------------------------
    # Query History panel — shown below Connect button
    # ------------------------------------------------------------------
    if st.session_state["query_history"]:
        st.divider()
        st.subheader("📜 Query History")

        # Show most recent first, last 10 queries max
        history = list(reversed(st.session_state["query_history"][-10:]))

        for i, item in enumerate(history):
            with st.expander(f"🕐 {item['timestamp']}  •  {item['rows']} rows"):
                st.caption(f"❓ {item['question']}")
                st.code(item["sql"], language="sql")

                # Re-run button: pre-fills the question and SQL in the main area
                if st.button("🔁 Re-run this query", key=f"rerun_{i}"):
                    st.session_state["prefill_question"] = item["question"]
                    st.session_state["generated_sql"]    = item["sql"]
                    st.rerun()

        st.divider()
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state["query_history"] = []
            st.rerun()


# ---------------------------------------------------------------------------
# Main area — two tabs: Query and Schema Explorer
# ---------------------------------------------------------------------------
if "schema" in st.session_state:
    tab1, tab2 = st.tabs(["🔍 Query", "🗄️ Schema Explorer"])

    # -----------------------------------------------------------------------
    # Tab 1: Query (everything that existed before, unchanged)
    # -----------------------------------------------------------------------
    with tab1:
        with st.expander("📋 View Raw Schema"):
            st.code(st.session_state["schema"])

        prefill = st.session_state.pop("prefill_question", "")

        user_question = st.text_input(
            "Ask a question about your data:",
            value=prefill,
            placeholder="e.g. Which department has the highest average salary?",
        )

        if st.button("⚡ Generate SQL", type="primary") and user_question:
            dialect = {
                "sqlite":     "SQLite",
                "postgresql": "PostgreSQL",
                "mysql":      "MySQL",
            }[st.session_state["db_type"]]

            with st.spinner("Generating SQL…"):
                try:
                    raw_sql = generate_sql(
                        user_question, st.session_state["schema"], dialect
                    )
                    st.session_state["generated_sql"]    = raw_sql
                    st.session_state["pending_question"] = user_question
                except Exception as e:
                    st.error(f"SQL generation failed: {e}")

        if "generated_sql" in st.session_state:
            st.subheader("📝 Generated SQL (editable)")
            final_sql = st.text_area(
                "Review or edit before running:",
                value=st.session_state["generated_sql"],
                height=150,
            )

            if st.button("▶️ Run Query", type="primary"):
                if not final_sql.strip():
                    st.warning("SQL is empty — nothing to run.")
                else:
                    with st.spinner("Running query…"):
                        try:
                            df = run_query(final_sql, st.session_state["conn_str"])

                            st.success(f"✅ {len(df):,} row(s) returned")
                            st.dataframe(df, use_container_width=False)

                            auto_visualize(df)

                            csv = df.to_csv(index=False)
                            st.download_button(
                                "📥 Download CSV",
                                data=csv,
                                file_name="query_result.csv",
                                mime="text/csv",
                            )
                            IST = pytz.timezone("Asia/Kolkata")
                            st.session_state["query_history"].append({
                                "question":  st.session_state.get("pending_question", user_question),
                                "sql":       final_sql,
                                "rows":      len(df),
                                # "timestamp": datetime.now().strftime("%d %b %H:%M:%S"),
                                
                                "timestamp": datetime.now(IST).strftime("%d %b %H:%M:%S IST"),
                            })

                        except Exception as e:
                            raw_error = str(e)
                            st.error(f"Query failed: {raw_error}")
                            with st.spinner("Explaining error…"):
                                try:
                                    explanation = explain_error(final_sql, raw_error)
                                    st.warning(f"💡 **What went wrong:** {explanation}")
                                except Exception:
                                    pass

    # -----------------------------------------------------------------------
    # Tab 2: Schema Explorer
    # -----------------------------------------------------------------------
    with tab2:
        structured = extract_schema_structured(st.session_state["conn_str"])

        # Top metrics row
        total_tables  = len(structured)
        total_columns = sum(len(t["columns"]) for t in structured.values())
        total_fks     = sum(len(t["foreign_keys"]) for t in structured.values())

        m1, m2, m3 = st.columns(3)
        m1.metric("📦 Tables",        total_tables)
        m2.metric("📋 Columns",       total_columns)
        m3.metric("🔗 Relationships", total_fks)

        st.divider()

        schema_tab1, schema_tab2 = st.tabs(["🔀 ER Diagram", "📑 Table Details"])

        with schema_tab1:
            build_er_diagram(structured)

        with schema_tab2:
            for table_name, info in structured.items():
                fk_cols = {fk["column"] for fk in info["foreign_keys"]}
                with st.expander(f"🗂️ {table_name}  ({len(info['columns'])} columns)"):

                    rows = []
                    for col in info["columns"]:
                        if col["primary_key"]:
                            badge = "🔑 PK"
                        elif col["name"] in fk_cols:
                            badge = "🔗 FK"
                        else:
                            badge = ""
                        rows.append({
                            "Column":   col["name"],
                            "Type":     col["type"],
                            "Key":      badge,
                            "Nullable": "✅" if col["nullable"] else "❌",
                        })

                    import pandas as pd
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                    if info["foreign_keys"]:
                        st.caption("**Foreign Keys:**")
                        for fk in info["foreign_keys"]:
                            st.caption(f"  `{fk['column']}` → `{fk['ref_table']}.{fk['ref_column']}`")

else:
    st.info("👈 Configure and connect to a database to get started.")