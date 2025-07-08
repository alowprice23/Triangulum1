import unittest
from example_files.null_pointer_example import User, process_user_settings

class TestUserSettings(unittest.TestCase):
    def test_process_user_settings_with_profile(self):
        # Create a user with a profile
        class Profile:
            def get_settings(self):
                return {"theme": "dark"}
        
        user = User("Bob")
        user.profile = Profile()
        
        # Process settings should work
        result = process_user_settings(user)
        self.assertEqual(result, {"theme": "dark"})
    
    def test_process_user_settings_without_profile(self):
        # Create a user without a profile
        user = User("Charlie")
        
        # Process settings should handle None profile
        result = process_user_settings(user)
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()
