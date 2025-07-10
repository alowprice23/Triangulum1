def get_user_profile(user_id):
    # Get user from database
    user = get_user_from_database(user_id)
    
    # Bug: No check if user is None before accessing properties
    name = user.name
    email = user.email
    
    return {
        "name": name,
        "email": email
    }

def get_user_from_database(user_id):
    # This is a mock function that might return None
    if user_id <= 0:
        return None
    
    # For demo purposes, create a user object
    class User:
        def __init__(self, user_id):
            self.id = user_id
            self.name = f"User {user_id}"
            self.email = f"user{user_id}@example.com"
    
    return User(user_id)
