
def process_data(data):
    try:
        result = complex_calculation(data)
        return result
    except Exception:
        # This silently swallows the exception
        pass
        
    # Default return value with no indication of failure
    return 0

def complex_calculation(data):
    # This might raise various exceptions
    return data['value1'] / data['value2']
