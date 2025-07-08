
import utils
import analysis
from models import User

def main():
    user = User("test_user")
    data = utils.load_data("data.json")
    if data:
        results = analysis.process_data(data)
        utils.save_results(results)
    print(f"Processing complete for {user.name}")

if __name__ == "__main__":
    main()
