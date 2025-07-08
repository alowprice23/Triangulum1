class User:
    def __init__(self, name):
        self.name = name
        self.profile = None
    
    def get_profile(self):
        return self.profile

def process_user_settings(user):
    # Bug: user.get_profile() might return None
    result = user.get_profile().get_settings()
    return result

user = User("Alice")
process_user_settings(user)  # This will cause a NoneType error
