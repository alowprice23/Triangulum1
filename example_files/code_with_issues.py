"""
This file contains various issues that the CodeFixer should detect and fix.
"""

# Issue 1: Hardcoded credentials
password = "supersecret123"
api_key = "abcdef1234567890"

# Issue 2: Resource leak
def read_file_with_leak(filename):
    f = open(filename, 'r')
    content = f.read()
    # No f.close() - resource leak
    return content

# Issue 3: SQL injection vulnerability
def get_user(user_id):
    import sqlite3
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # SQL injection vulnerability
    cursor.execute("SELECT * FROM users WHERE id = " + user_id)
    result = cursor.fetchone()
    conn.close()
    return result

# Issue 4: Exception swallowing
def divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        pass  # Swallowing the exception

# Issue 5: Null pointer issue
def process_data(data):
    # No null check before accessing data
    result = data['key'].strip()
    return result
