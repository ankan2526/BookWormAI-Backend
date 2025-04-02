MODEL = "gemini-2.0-flash"
DB_PATH = r"/Users/ankanmahapatra/Desktop/genAI/BookWormAI/backend/books.db"
DB_URI = r"sqlite:////Users/ankanmahapatra/Desktop/genAI/BookWormAI/backend/books.db"
LIMIT_ROWS = 10

TEXT_TO_SQL_PROMPT = """
For a given user query, generate a one line SQLite query.
User query: {user_query}

Database details:
dialect: {dialect}

Table information:
{table_info}

Limit rows: {LIMIT_ROWS}

One line SQLite query:
"""