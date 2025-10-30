import logging
import time
import pandas as pd
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

def mysql_query_ability(query: str) -> str:
    """
    Execute a MySQL query and return formatted results
    Supports SELECT queries only for safety
    And implement and register one specific ability:
       - They import and use the utilities from `mysql_abilities.py`
       - Each file has a clear, single responsibility
       - Each file registers its own ability
    """
    from abilities.mysql_abilities import execute_query, get_connection_pool
    
    logger.debug(f"ABILITY CALLED: mysql-query with query: {query[:100]}...")
    start_time = time.time()

    # Basic security check
    query_lower = query.strip().lower()
    if not query_lower.startswith('select'):
        return "Error: Only SELECT queries are allowed for safety reasons."

    # Additional security checks
    dangerous_keywords = ['drop', 'delete', 'update', 'insert', 'alter', 'truncate', 'create']
    for keyword in dangerous_keywords:
        if f" {keyword} " in f" {query_lower} ":
            return f"Error: Potentially dangerous keyword '{keyword}' detected in query."

    try:
        # Use pandas to execute query and format results
        pool = get_connection_pool()
        conn = pool.get_connection()

        try:
            df = pd.read_sql_query(query, conn)
        finally:
            conn.close()

        # Generate summary statistics
        summary = f"Query Results Summary:\n"
        summary += f"- Rows returned: {len(df):,}\n"
        summary += f"- Columns: {', '.join(df.columns)}\n\n"

        # Add basic statistical analysis for numeric columns
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
        if len(numeric_cols) > 0:
            summary += "Numeric Column Statistics:\n"
            for col in numeric_cols:
                stats = df[col].describe()
                summary += f"\n{col}:\n"
                summary += f"- Mean: {stats['mean']:.2f}\n"
                summary += f"- Std Dev: {stats['std']:.2f}\n"
                summary += f"- Min: {stats['min']:.2f}\n"
                summary += f"- Max: {stats['max']:.2f}\n"

                # Add distribution information
                summary += f"- Distribution: "
                try:
                    # Calculate quartiles
                    q1, q2, q3 = df[col].quantile([0.25, 0.5, 0.75])
                    summary += f"Q1={q1:.2f}, Median={q2:.2f}, Q3={q3:.2f}\n"

                    # Check for outliers
                    iqr = q3 - q1
                    lower_bound = q1 - 1.5 * iqr
                    upper_bound = q3 + 1.5 * iqr
                    outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)][col]
                    if len(outliers) > 0:
                        summary += f"- Outliers: {len(outliers)} values outside range [{lower_bound:.2f}, {upper_bound:.2f}]\n"
                except:
                    summary += "Could not calculate distribution\n"

        # Add categorical column analysis
        cat_cols = df.select_dtypes(include=['object']).columns
        if len(cat_cols) > 0:
            summary += "\nCategorical Column Analysis:\n"
            for col in cat_cols:
                if df[col].nunique() <= 10:  # Only show distribution for columns with few unique values
                    summary += f"\n{col} value counts:\n"
                    value_counts = df[col].value_counts().head(5)
                    for val, count in value_counts.items():
                        summary += f"- {val}: {count} ({count/len(df)*100:.1f}%)\n"
                else:
                    summary += f"\n{col}:\n"
                    summary += f"- Unique values: {df[col].nunique()}\n"
                    summary += f"- Most common: {df[col].value_counts().index[0]} ({df[col].value_counts().iloc[0]} occurrences)\n"

        # Format results as string table
        if len(df) > 0:
            summary += "\nFirst 10 rows of results:\n"
            summary += df.head(10).to_string()

            if len(df) > 10:
                summary += f"\n\n[{len(df)-10} more rows not shown]"
        else:
            summary += "\nNo results returned by query."

        execution_time = time.time() - start_time
        logger.debug(f"MySQL query completed in {execution_time:.2f}s")
        logger.debug(f"Returned {len(df)} rows")

        return summary

    except Exception as e:
        logger.error(f"Error executing MySQL query: {str(e)}")
        return f"Error executing MySQL query: {str(e)}"

# Register this ability
if __name__ != "__main__":
    from abilities.ability_registry import register_ability
    register_ability("mysql-query", mysql_query_ability)