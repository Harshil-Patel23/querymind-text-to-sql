import pandas as pd
from sqlalchemy import create_engine,text
import sqlparse
import streamlit as st

BLOCKED_KEYWORD = ["DROP","DELETE","TRUNCATE","ALTER","INSERT","UPDATE","CREATE"]

def is_select_query(sql:str)->bool:
    parsed=sqlparse.parse(sql.strip())
    if not parsed:
        return False
    statement=parsed[0]
    return statement.get_type()=="SELECT"

def is_safe_query(sql:str)->tuple[bool,str]:
    upper_sql=sql.upper()
    for keyword in BLOCKED_KEYWORD:
        if keyword in upper_sql:
            return False,f"Query contains blocked keyword: {keyword}"
        return True,""

def run_query(sql: str, connection_string: str) -> pd.DataFrame:
    safe, reason = is_safe_query(sql)
    if not safe:
        raise ValueError(reason)
    
    engine = create_engine(connection_string)
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        return pd.DataFrame(result.fetchall(), columns=result.keys())

