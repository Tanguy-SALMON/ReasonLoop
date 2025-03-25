from abilities.text_completion import text_completion_ability
from abilities.web_search import web_search_ability
from abilities.web_scrape import web_scrape_ability
from abilities.file_abilities import write_file_ability
from abilities.mysql_schema import mysql_schema_ability
from abilities.mysql_query import mysql_query_ability

from abilities.ability_registry import register_ability

# Register all abilities
register_ability("text-completion", text_completion_ability)
register_ability("web-search", web_search_ability)
register_ability("web-scrape", web_scrape_ability)
register_ability("write-file", write_file_ability)
register_ability("mysql-schema", mysql_schema_ability)
register_ability("mysql-query", mysql_query_ability)