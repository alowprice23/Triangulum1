
import models

def process_data(data):
    # Inefficient processing
    results = []
    for item in data:
        if item.get("value") > 50:
            results.append(models.Result(item["id"], "high"))
    return results
