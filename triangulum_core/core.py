import yaml

def start():
    print("Starting Triangulum...")
    with open("triangulum.yaml", "r") as f:
        config = yaml.safe_load(f)
    print(config)

def stop():
    print("Stopping Triangulum...")

def status():
    print("Triangulum is running.")

def shell():
    print("Starting Triangulum shell...")
