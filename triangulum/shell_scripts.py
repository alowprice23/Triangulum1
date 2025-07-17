def get_shell_scripts():
    """
    Returns a dictionary of all available shell scripts.
    """
    scripts = {}
    return scripts

if __name__ == '__main__':
    import json
    print(json.dumps(get_shell_scripts(), indent=2))
