
import unittest
from pathlib import Path

# Add the current directory to path
import sys
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from division import calculate_ratio, safe_calculate_ratio

class TestDivision(unittest.TestCase):
    
    def test_calculate_ratio(self):
        # This test will fail with ZeroDivisionError
        result = calculate_ratio(10, 0)
        self.assertEqual(result, float('inf'))
    
    def test_safe_calculate_ratio(self):
        # This test will pass
        result = safe_calculate_ratio(10, 0)
        self.assertEqual(result, float('inf'))

if __name__ == "__main__":
    unittest.main()
