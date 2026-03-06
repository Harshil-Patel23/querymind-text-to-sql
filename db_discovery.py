import os
import glob
from sqlalchemy import create_engine, text


def list_databases(conn_str: str) -> list[str]:
    """
    Lists all user-accessible databases on a PostgreSQL or MySQL server.
    For PostgreSQL, conn_str should point to the 'postgres' default DB.
    For MySQL, conn_str should point to any DB (e.g. empty or 'mysql').
    """
    engine = create_engine(conn_str)
    with engine.connect() as conn:
        if "postgresql" in conn_str or "psycopg2" in conn_str:
            result = conn.execute(text(
                "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname"
            ))
        elif "mysql" in conn_str:
            result = conn.execute(text("SHOW DATABASES"))
        else:
            raise ValueError("Unsupported DB type for listing databases.")
        return [row[0] for row in result]


def list_sqlite_databases(folder_path: str) -> list[str]:
    """
    Scans a folder for .db and .sqlite files and returns their paths.
    """
    folder_path = folder_path.rstrip("/").rstrip("\\")
    patterns = [
        os.path.join(folder_path, "*.db"),
        os.path.join(folder_path, "*.sqlite"),
        os.path.join(folder_path, "*.sqlite3"),
    ]
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))
    return sorted(files)