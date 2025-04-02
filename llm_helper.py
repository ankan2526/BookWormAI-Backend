import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import START, StateGraph, MessagesState
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.checkpoint.memory import MemorySaver

import sqlite3
from typing import List
from langchain_community.utilities import SQLDatabase
from langchain_community.tools import TavilySearchResults
from constants import DB_PATH, DB_URI, LIMIT_ROWS, TEXT_TO_SQL_PROMPT, MODEL

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    filename='logfile.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("Loading environment variables")
load_dotenv()

logger.info("Initializing database connection")
db = SQLDatabase.from_uri(DB_URI)
dialect = db.dialect
table_info = db.get_table_info()
logger.info(f"Database connection initialized with dialect: {dialect}")
logger.info(f"Table information: {table_info}")

## These are tools that will be used by AI Agent to make decisions and answer questions
def text_to_sqlite_query(user_query: str) -> str:
    """Converts natural language query to a valid sqlite query

    Args:
        user_query (str): The user query in natural language

    Returns:
        str: A valid sqlite query
    """
    logger.info(f"Generating SQL prompt for query: {user_query}")
    text_to_sqlite_prompt = TEXT_TO_SQL_PROMPT.format(dialect=dialect, LIMIT_ROWS=LIMIT_ROWS, table_info=table_info, user_query=user_query)
    logger.info(f"Generated SQL prompt: {text_to_sqlite_prompt}")
    sqlite_query = llm.invoke(text_to_sqlite_prompt).content
    logger.info(f"Generated SQLite query: {sqlite_query}")
    return str(sqlite_query)

def execute_sqlite_query(query: str) -> List:
    """Execute a sqlite query and get a list of table rows

    Args:
        query (str): The sqlite query to be executed

    Returns:
        List: List of table rows
    """
    logger.info(f"Executing SQLite query: {query}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        conn.close()
        logger.info(f"Query executed successfully, returned {len(result)} rows")
        return result
    except Exception as e:
        logger.error(f"Error executing SQLite query: {str(e)}")
        raise

def search_tool(query: str) -> List:
    """This function will search results from web

    Args:
        query (str): The query to be searched

    Returns:
        List: The search results
    """
    logger.info(f"Performing web search for query: {query}")
    tool = TavilySearchResults(
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=True,
        include_images=True,
    )
    try:
        result = tool.invoke(query)
        logger.info(f"Search completed successfully, found {len(result)} results")
        return result
    except Exception as e:
        logger.error(f"Error during web search: {str(e)}")
        raise

logger.info("Initializing LLM and tools")
llm = ChatGoogleGenerativeAI(
    model=MODEL,
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

tools = [text_to_sqlite_query, execute_sqlite_query, search_tool]

llm_with_tools = llm.bind_tools(tools)

sys_msg = SystemMessage(content="""You are an AI agent that helps readers answer book related queries. You can use multiple tools to answer the question""")

def assistant(state: MessagesState):
    logger.debug("Processing assistant state")
    response = llm_with_tools.invoke([sys_msg] + state["messages"])
    logger.debug(f"Assistant generated response: {response}")
    return {"messages": [response]}

logger.info("Building state graph")
builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "assistant")
builder.add_conditional_edges("assistant", tools_condition)
builder.add_edge("tools", "assistant")

memory = MemorySaver()
react_graph_memory = builder.compile(checkpointer=memory)
logger.info("State graph compiled successfully")

def invoke(query, thread_id):
    """Main invocation function for the LLM helper

    Args:
        query (str): The user's query
        thread_id: The thread identifier

    Returns:
        dict: Contains the original query and the result
    """
    logger.info(f"Processing query with thread_id {thread_id}: {query}")
    try:
        config = {"thread_id": thread_id}
        messages = react_graph_memory.invoke({"messages": [HumanMessage(content=query)]}, config=config)
        # messages = builder.compile().invoke({"messages": [HumanMessage(content=query)]})
        logger.info(f"Messages received from state graph: {messages}")
        result = messages["messages"][-1].content
        logger.info("Query processed successfully")
        return {"query": query, "result": result}
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise