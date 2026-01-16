import logging
import pandas as pd
from abilities.mysql_abilities import execute_query

logger = logging.getLogger(__name__)


def mysql_schema_ability(table_name: str = None) -> str:
    """
    Analyze and return MySQL schema information
    If table_name is provided, returns detailed info for that table
    Otherwise returns overview of all tables
    """
    logger.info(f"MySQL schema: {table_name or 'all tables'}")

    if table_name:
        # Get column information
        columns = execute_query("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY,
                   CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """, (table_name,))

        # Get table statistics
        stats = execute_query("""
            SELECT TABLE_ROWS, AVG_ROW_LENGTH, DATA_LENGTH, INDEX_LENGTH
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        """, (table_name,))

        # Get indexes
        indexes = execute_query("""
            SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE, SEQ_IN_INDEX
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """, (table_name,))

        # Format output
        output = f"Table: {table_name}\n\nColumns:\n"
        for col in columns:
            pk = " PRIMARY KEY" if col['COLUMN_KEY'] == 'PRI' else ""
            nullable = "" if col['IS_NULLABLE'] == 'YES' else " NOT NULL"
            output += f"- {col['COLUMN_NAME']} ({col['DATA_TYPE']}){pk}{nullable}\n"

        if stats and stats[0]:
            s = stats[0]
            output += f"\nStatistics:\n"
            output += f"- Rows: {s['TABLE_ROWS']:,}\n"
            output += f"- Data size: {s['DATA_LENGTH']/1024/1024:.2f} MB\n"
            output += f"- Index size: {s['INDEX_LENGTH']/1024/1024:.2f} MB\n"

        if indexes:
            output += f"\nIndexes:\n"
            current_index = None
            for idx in indexes:
                if current_index != idx['INDEX_NAME']:
                    current_index = idx['INDEX_NAME']
                    unique = "Unique" if not idx['NON_UNIQUE'] else "Non-unique"
                    output += f"- {current_index} ({unique}): {idx['COLUMN_NAME']}"
                else:
                    output += f", {idx['COLUMN_NAME']}"
            output += "\n"

        # Sample data
        sample = execute_query(f"SELECT * FROM {table_name} LIMIT 5")
        if sample:
            output += f"\nSample (5 rows):\n{pd.DataFrame(sample).to_string()}"

    else:
        # Get all tables
        tables = execute_query("""
            SELECT TABLE_NAME, TABLE_ROWS,
                   DATA_LENGTH/1024/1024 as data_mb,
                   INDEX_LENGTH/1024/1024 as index_mb
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            ORDER BY TABLE_ROWS DESC
        """)

        output = "Database Schema:\n\n"
        for table in tables:
            output += f"{table['TABLE_NAME']}\n"
            output += f"  Rows: {table['TABLE_ROWS']:,}\n"
            output += f"  Size: {table['data_mb']:.2f} MB (data) + {table['index_mb']:.2f} MB (index)\n\n"

        # Total size
        db_size = execute_query("""
            SELECT SUM(data_length + index_length) / 1024 / 1024 AS size_mb
            FROM information_schema.TABLES
            WHERE table_schema = DATABASE()
        """)

        if db_size and db_size[0]['size_mb']:
            output += f"Total: {db_size[0]['size_mb']:.2f} MB\n"

    logger.info(f"Schema analysis completed")
    return output


# Register this ability
if __name__ != "__main__":
    from abilities.ability_registry import register_ability
    register_ability("mysql-schema", mysql_schema_ability)
