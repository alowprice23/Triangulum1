def save_log_entry(log_entry):
    # Bug: File is opened but not properly closed
    log_file = open("application.log", "a")
    log_file.write(log_entry + "\n")
    
    # Missing log_file.close()
    
    return True

def read_configuration():
    # Bug: Another resource leak
    config_file = open("config.ini", "r")
    config_data = config_file.read()
    
    # What if an exception occurs?
    
    config_file.close()
    return config_data
