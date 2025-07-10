def process_data(data):
    try:
        # Process the data
        result = transform_data(data)
        return result
    except Exception:
        # Bug: Exception is swallowed without logging or handling
        pass
    
    # Default return value with no indication of failure
    return None

def transform_data(data):
    # This might raise various exceptions
    if not isinstance(data, dict):
        raise TypeError("Data must be a dictionary")
    
    if "value" not in data:
        raise ValueError("Data must contain a 'value' key")
    
    return data["value"] * 2
