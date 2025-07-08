
def connect_to_database():
    # Hardcoded credentials are a security risk
    username = "admin"
    password = "super_secret_password"
    
    # Connect to the database
    connection = database.connect(
        host="db.example.com",
        user=username,
        password=password,
        database="production"
    )
    return connection
