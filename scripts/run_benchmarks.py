"""
Performance and Quality Benchmark Suite for Triangulum LX LLM Providers.

This script iterates through all configured LLM providers and models,
runs a standardized set of prompts against them, and generates a
markdown report comparing their performance on key metrics.
"""

import yaml
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any

from triangulum_lx.providers.factory import get_provider
from triangulum_lx.agents.llm_config import LLM_CONFIG

PROMPTS_PATH = Path(__file__).parent.parent / "tests/benchmarks/standard_prompts.yaml"
RESULTS_PATH = Path(__file__).parent.parent / "benchmark_results.md"

def load_prompts() -> List[Dict[str, Any]]:
    """Loads the standard prompts from the YAML file."""
    if not PROMPTS_PATH.exists():
        return []
    with open(PROMPTS_PATH, 'r') as f:
        return yaml.safe_load(f)

def run_benchmark() -> List[Dict[str, Any]]:
    """
    Runs the benchmark across all configured providers and models.
    """
    from triangulum_lx.agents.llm_config import load_llm_config, get_llm_config

    try:
        get_llm_config()
    except RuntimeError:
        with open(Path(__file__).parent.parent / "triangulum.yaml", "r") as f:
            config = yaml.safe_load(f)
        load_llm_config(config.get("llm", {}))

    prompts = load_prompts()
    results = []

    providers_config = get_llm_config().get("providers", {})

    for provider_name, provider_info in providers_config.items():
        if not provider_info.get("api_key"):
            print(f"Skipping {provider_name}: No API key configured.")
            continue

        for model_name in provider_info.get("models", {}).keys():
            print(f"Benchmarking {provider_name}/{model_name}...")
            try:
                provider = get_provider(provider_name, {"model": model_name})
            except ValueError as e:
                print(f"Could not create provider {provider_name}: {e}")
                continue

            for task in prompts:
                start_time = time.time()
                
                try:
                    response = provider.generate(task["prompt"])
                    latency = time.time() - start_time
                    
                    results.append({
                        "provider": provider_name,
                        "model": model_name,
                        "task": task["task"],
                        "latency_s": round(latency, 3),
                        "tokens_used": response.tokens_used,
                        "cost_usd": response.cost,
                        "output_hash": hashlib.sha256(response.content.encode()).hexdigest()[:8],
                        "status": "Success",
                    })
                except Exception as e:
                    latency = time.time() - start_time
                    results.append({
                        "provider": provider_name,
                        "model": model_name,
                        "task": task["task"],
                        "latency_s": round(latency, 3),
                        "tokens_used": None,
                        "cost_usd": None,
                        "output_hash": None,
                        "status": f"Error: {type(e).__name__}",
                    })

    return results

def generate_report(results: List[Dict[str, Any]]):
    """Generates a markdown report from the benchmark results."""
    
    header = "| Provider | Model | Task | Latency (s) | Tokens | Cost ($) | Output Hash | Status |\n"
    separator = "|----------|-------|------|-------------|--------|----------|-------------|--------|\n"
    
    body = ""
    for res in results:
        body += f"| {res['provider']} | {res['model']} | {res['task']} | {res['latency_s']} | {res['tokens_used'] or 'N/A'} | {res['cost_usd'] or 'N/A'} | {res['output_hash'] or 'N/A'} | {res['status']} |\n"

    report = f"# LLM Provider Benchmark Results\n\n{header}{separator}{body}"
    
    with open(RESULTS_PATH, 'w') as f:
        f.write(report)
    
    print(f"\nBenchmark complete. Report generated at: {RESULTS_PATH}")

def main():
    benchmark_results = run_benchmark()
    if benchmark_results:
        generate_report(benchmark_results)
    else:
        print("No benchmarks were run. Please check your configuration.")

if __name__ == "__main__":
    main()
