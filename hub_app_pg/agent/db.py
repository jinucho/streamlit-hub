from agent.config import LLM, get_logger
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
import os
from dotenv import load_dotenv

load_dotenv()

# 로깅 설정
logger = get_logger()


def get_db_connection():
    """데이터베이스 연결을 반환합니다."""
    llm = LLM()
    url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    db = SQLDatabase.from_uri(url)
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    return db, toolkit