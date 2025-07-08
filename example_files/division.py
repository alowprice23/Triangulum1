
def divide(a, b):
    # This will raise a ZeroDivisionError if b is 0
    return a / b

def calculate_ratio(numerator, denominator):
    # Missing check for denominator being zero
    return divide(numerator, denominator)

def safe_calculate_ratio(numerator, denominator):
    # Safe version with proper error handling
    if denominator == 0:
        return float('inf')  # Return infinity for division by zero
    return divide(numerator, denominator)
