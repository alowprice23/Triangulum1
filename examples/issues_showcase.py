import os
import logging # For exception swallowing fix

logger = logging.getLogger(__name__)

# Hardcoded credentials
password = "supersecret123"
api_key = "abcdef123456"

# Resource leak
def process_file(filename):
    f = open(filename, 'r') # Potential leak
    data = f.read()
    # f.close() is missing
    return data

# SQL injection
def get_user_data(user_id, cursor):
    # Vulnerable to SQL injection
    cursor.execute("SELECT * FROM users WHERE id = " + user_id)
    return cursor.fetchone()

def get_user_data_fstring(user_id, cursor):
    # Vulnerable with f-string
    cursor.execute(f"SELECT * FROM users WHERE name = '{user_id}'")
    return cursor.fetchone()

# Exception swallowing
def divide_numbers(a, b):
    try:
        result = a / b
    except ZeroDivisionError:
        pass # Exception swallowed
    except: # Broad except
        pass # Also swallowed
    return result

# Null pointer issues
def get_property(data, key):
    # Potential null pointer if data is None
    # Also, direct dict access can cause KeyError if key is missing
    value = data[key]
    return value.property

def process_optional_data(data):
    # Potential null pointer if data or data.attribute is None
    if data: # Checks data, but not data.attribute
        return data.attribute.another_attribute
    return None

class MyClass:
    def __init__(self, config):
        self.config_value = config['value'] # Potential KeyError

    def get_deep_value(self, my_obj):
        # my_obj could be None, my_obj.first could be None
        return my_obj.first.second.third

# Example usage (not directly tested by fixer, but for context)
if __name__ == '__main__':
    # Example for credentials (won't be fixed, but shows usage)
    print(f"Password: {password}, API Key: {api_key}")

    # Example for resource leak
    # In a real scenario, you'd create a dummy file for this to run
    # For testing the fixer, the content of this file doesn't matter as much
    # as the `open()` call itself.

    # Example for SQL injection (conceptual)
    # class MockCursor:
    #     def execute(self, query, params=None): print(f"Executing: {query}, {params}")
    #     def fetchone(self): return ("dummy_user",)
    # get_user_data("1", MockCursor())

    # Example for exception swallowing
    divide_numbers(5, 0)

    # Example for null pointer
    # get_property(None, "some_key")
    # process_optional_data(None)
    pass
