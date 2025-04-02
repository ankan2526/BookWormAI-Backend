

class DB_Helper:
    def __init__(self):
        pass

    def get_books(self, conn):
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM books LIMIT 10;
        ''')
        result = cursor.fetchall()
        cursor.close()
        return list(result)
    
    def search_books(self, conn, search):
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM books WHERE `Book-Title` LIKE ? LIMIT 10;
        ''', ('%' + search + '%',))
        result = cursor.fetchall()
        cursor.close()
        return list(result)