from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class DBConfig:
    name: str
    db_type: str  # sqlite, postgresql, mysql
    connection_string: str

def build_connection_string(db_type, host, port, user, password, dbname, filepath=None):
    if db_type == "sqlite":
        return f"sqlite:///{filepath}"
    elif db_type == "postgresql":
        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    elif db_type == "mysql":
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{dbname}"
    else:
        raise ValueError(f"Unsupported DB type: {db_type}")