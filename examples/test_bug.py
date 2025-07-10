# Simple file with a bug for testing
def risky_operation():
    try:
        # This could fail
        result = 10 / 0
        return result
    except Exception:
        # Exception swallowing bug - not handling or logging the error
        pass

def main():
    value = risky_operation()
    print(f"Result: {value}")

if __name__ == "__main__":
    main()
