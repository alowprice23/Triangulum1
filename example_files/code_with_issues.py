def get_user(user_id):
    # This is vulnerable to SQL injection
    cursor.execute("SELECT * FROM users WHERE id = " + user_id)
    return cursor.fetchone()

def process_data(data):
    # This will cause a null reference error if data is None
    return data.get('value')

def read_file(filename):
    # This file is opened but never closed
    f = open(filename, 'r')
    content = f.read()
    return content

def connect_to_database():
    # Hardcoded credentials are a security risk
    password = "supersecret123"
    connection = db.connect("localhost", "admin", password)
    return connection

def process_data(data):
    try:
        result = complex_operation(data)
        return result
    except Exception:
        # This silently swallows the exception
        pass
