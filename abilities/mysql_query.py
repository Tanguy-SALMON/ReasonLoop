import logging
import pandas as pd
from abilities.mysql_abilities import get_connection_pool

logger = logging.getLogger(__name__)


def mysql_query_ability(query: str) -> str:
    """
    Execute a MySQL query and return formatted results
    Supports SELECT queries only for safety
    """
    logger.info(f"MySQL query: {query[:100]}...")

    # Security check - only SELECT queries
    query_lower = query.strip().lower()
    if not query_lower.startswith('select'):
        return "Error: Only SELECT queries allowed"

    # Check for dangerous keywords
    dangerous = ['drop', 'delete', 'update', 'insert', 'alter', 'truncate', 'create']
    for keyword in dangerous:
        if f" {keyword} " in f" {query_lower} ":
            return f"Error: Dangerous keyword '{keyword}' detected"

    # Execute query
    pool = get_connection_pool()
    conn = pool.get_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Format results
    output = f"Query Results:\n"
    output += f"- Rows: {len(df):,}\n"
    output += f"- Columns: {', '.join(df.columns)}\n\n"

    # Numeric statistics
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    if len(numeric_cols) > 0:
        output += "Numeric Statistics:\n"
        for col in numeric_cols:
            stats = df[col].describe()
            output += f"\n{col}:\n"
            output += f"  Mean: {stats['mean']:.2f}, Min: {stats['min']:.2f}, Max: {stats['max']:.2f}\n"

    # Categorical analysis
    cat_cols = df.select_dtypes(include=['object']).columns
    if len(cat_cols) > 0:
        output += "\nCategorical Analysis:\n"
        for col in cat_cols:
            if df[col].nunique() <= 10:
                output += f"\n{col}:\n"
                for val, count in df[col].value_counts().head(5).items():
                    output += f"  {val}: {count} ({count/len(df)*100:.1f}%)\n"

    # Show data
    if len(df) > 0:
        output += f"\nFirst 10 rows:\n{df.head(10).to_string()}"
        if len(df) > 10:
            output += f"\n\n[{len(df)-10} more rows]"
    else:
        output += "\nNo results"

    logger.info(f"Query completed: {len(df)} rows")
    return output


# Register this ability
if __name__ != "__main__":
    from abilities.ability_registry import register_ability
    register_ability("mysql-query", mysql_query_ability)
