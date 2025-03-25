import logging
import time
import pandas as pd
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

def mysql_schema_ability(table_name: Optional[str] = None) -> str:
    """
    Analyze and return MySQL schema information
    If table_name is provided, returns detailed info for that table
    Otherwise returns overview of all tables
    And implement and register one specific ability:
       - They import and use the utilities from `mysql_abilities.py`
       - Each file has a clear, single responsibility
       - Each file registers its own ability
    """
    from abilities.mysql_abilities import execute_query
    
    logger.debug(f"ABILITY CALLED: mysql-schema for table: {table_name}")
    start_time = time.time()

    try:
        if table_name:
            # Get column information
            columns = execute_query("""
                SELECT
                    COLUMN_NAME, DATA_TYPE,
                    IS_NULLABLE, COLUMN_KEY,
                    COLUMN_DEFAULT, EXTRA,
                    CHARACTER_MAXIMUM_LENGTH,
                    NUMERIC_PRECISION, NUMERIC_SCALE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """, (table_name,))

            # Get table statistics
            stats = execute_query("""
                SELECT
                    TABLE_ROWS, AVG_ROW_LENGTH,
                    DATA_LENGTH, INDEX_LENGTH
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            """, (table_name,))

            # Get index information
            indexes = execute_query("""
                SELECT
                    INDEX_NAME, COLUMN_NAME, NON_UNIQUE,
                    SEQ_IN_INDEX, CARDINALITY
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                ORDER BY INDEX_NAME, SEQ_IN_INDEX
            """, (table_name,))

            # Format detailed table information
            result = f"Table: {table_name}\n\nColumns:\n"
            for col in columns:
                result += (f"- {col['COLUMN_NAME']} ({col['DATA_TYPE']}"
                          f"{f'({col['CHARACTER_MAXIMUM_LENGTH']})' if col['CHARACTER_MAXIMUM_LENGTH'] else ''}"
                          f") {'PRIMARY KEY' if col['COLUMN_KEY'] == 'PRI' else ''}"
                          f" {'NOT NULL' if col['IS_NULLABLE'] == 'NO' else ''}\n")

            if stats and stats[0]:
                result += f"\nStatistics:\n"
                result += f"- Approximate rows: {stats[0]['TABLE_ROWS']:,}\n"
                result += f"- Average row length: {stats[0]['AVG_ROW_LENGTH']:,} bytes\n"
                result += f"- Data size: {stats[0]['DATA_LENGTH']/1024/1024:.2f} MB\n"
                result += f"- Index size: {stats[0]['INDEX_LENGTH']/1024/1024:.2f} MB\n"

            # Format index information
            if indexes:
                result += f"\nIndexes:\n"
                current_index = None
                for idx in indexes:
                    if current_index != idx['INDEX_NAME']:
                        current_index = idx['INDEX_NAME']
                        result += f"- {current_index} ({'Non-unique' if idx['NON_UNIQUE'] else 'Unique'}):\n"
                    result += f"  - Column: {idx['COLUMN_NAME']} (Position: {idx['SEQ_IN_INDEX']})\n"

            # Get sample data
            sample_data = execute_query(f"SELECT * FROM {table_name} LIMIT 5")
            if sample_data:
                result += f"\nSample Data (5 rows):\n"
                df = pd.DataFrame(sample_data)
                result += df.to_string()

        else:
            # Get overview of all tables
            tables = execute_query("""
                SELECT
                    TABLE_NAME,
                    TABLE_ROWS,
                    DATA_LENGTH/1024/1024 as data_size_mb,
                    INDEX_LENGTH/1024/1024 as index_size_mb,
                    CREATE_TIME,
                    UPDATE_TIME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                ORDER BY TABLE_ROWS DESC
            """)

            result = "Database Schema Overview:\n\n"
            for table in tables:
                result += f"Table: {table['TABLE_NAME']}\n"
                result += f"- Approximate rows: {table['TABLE_ROWS']:,}\n"
                result += f"- Data size: {table['data_size_mb']:.2f} MB\n"
                result += f"- Index size: {table['index_size_mb']:.2f} MB\n"
                if table['CREATE_TIME']:
                    result += f"- Created: {table['CREATE_TIME']}\n"
                if table['UPDATE_TIME']:
                    result += f"- Last updated: {table['UPDATE_TIME']}\n"
                result += "\n"

            # Add database size information
            db_size = execute_query("""
                SELECT
                    SUM(data_length + index_length) / 1024 / 1024 AS size_mb
                FROM information_schema.TABLES
                WHERE table_schema = DATABASE()
            """)

            if db_size and db_size[0]['size_mb']:
                result += f"Total Database Size: {db_size[0]['size_mb']:.2f} MB\n"

        execution_time = time.time() - start_time
        logger.debug(f"MySQL schema analysis completed in {execution_time:.2f}s")

        return result

    except Exception as e:
        logger.error(f"Error in MySQL schema analysis: {str(e)}")
        return f"Error analyzing MySQL schema: {str(e)}"

# Register this ability
if __name__ != "__main__":
    from abilities.ability_registry import register_ability
    register_ability("mysql-schema", mysql_schema_ability)