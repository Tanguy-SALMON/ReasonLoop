import logging
import mysql.connector
from mysql.connector import pooling
from typing import Optional, Dict, Any, List, Tuple
import time
from config.settings import get_setting

logger = logging.getLogger(__name__)

# Connection pool for MySQL
_connection_pool = None

def get_connection_pool():
    """Initialize and return the MySQL connection pool and contains the core database utilities:
       - Connection pool management
       - Query execution helpers
       - No direct ability registrations"""
    global _connection_pool

    if _connection_pool is None:
        try:
            db_config = get_setting("DB_CONFIG")
            _connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="reasonloop_pool",
                pool_size=5,
                **db_config
            )
            logger.info("MySQL connection pool initialized")
        except Exception as e:
            logger.error(f"Error initializing MySQL connection pool: {str(e)}")
            raise

    return _connection_pool

def execute_query(query: str, params: Optional[Tuple] = None, fetch: bool = True) -> Any:
    """Execute a query and return results"""
    conn = None
    cursor = None

    try:
        pool = get_connection_pool()
        conn = pool.get_connection()
        cursor = conn.cursor(dictionary=True)

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if fetch:
            return cursor.fetchall()
        else:
            conn.commit()
            return cursor.rowcount

    except Exception as e:
        logger.error(f"Query execution error: {str(e)}")
        logger.error(f"Query: {query}")
        if params:
            logger.error(f"Parameters: {params}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()