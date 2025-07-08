
def get_user_by_id(user_id):
    # This is vulnerable to SQL injection
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchone()

def search_users(search_term):
    # This is also vulnerable
    query = "SELECT * FROM users WHERE name LIKE '%" + search_term + "%'"
    cursor.execute(query)
    return cursor.fetchall()
