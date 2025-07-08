
def read_data_from_file(filename):
    # This file is opened but never closed
    f = open(filename, 'r')
    data = f.read()
    # Missing f.close()
    return data

def write_data_to_file(filename, data):
    # This file is also not properly closed
    f = open(filename, 'w')
    f.write(data)
    # What if an exception occurs before we reach this point?
    f.close()
    return True
