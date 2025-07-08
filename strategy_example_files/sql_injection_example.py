
def search_users(search_term):
    # Bug: SQL injection vulnerability
    query = "SELECT * FROM users WHERE name LIKE '%" + search_term + "%'"
    
    # Execute query (not actual implementation)
    results = db_execute(query)
    
    return results

def get_user_by_id(user_id):
    # Bug: Another SQL injection vulnerability
    query = "SELECT * FROM users WHERE id = " + user_id
    
    # Execute query (not actual implementation)
    result = db_execute(query)
    
    return result

def db_execute(query):
    # Mock function for demonstration
    return [{"id": 1, "name": "User 1"}, {"id": 2, "name": "User 2"}]
