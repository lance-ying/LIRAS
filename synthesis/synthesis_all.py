from utils import *
import os
import argparse
from google import genai
from segment_cells import *
import time


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synthesize domain and problem files for PDDL.")
    parser.add_argument("--domain", type=str, help="The name of the domain to process (e.g., foodtruck).", default="foodtruck")
    args = parser.parse_args()

    domain_name = args.domain

    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    client_gemini = genai.Client(api_key=gemini_api_key)

    project_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    domain_stimuli_path = os.path.join(project_base_dir, "dataset/stimuli", domain_name)

    print(f"Processing domain: {domain_name}")
    problem_names = [
        p_name for p_name in os.listdir(domain_stimuli_path)
        if os.path.isdir(os.path.join(domain_stimuli_path, p_name)) and p_name != "TEXT_ONLY"
    ]

    for problem_name in problem_names:
        print(f"--- Processing problem: {problem_name} ---")
        synthesize_domain(client_gemini, domain_name, problem_name)
        extract_objects(client_gemini, domain_name, problem_name)
        synthesize_config(client_gemini, domain_name, problem_name)
        generate_problem_pddl(client_gemini, domain_name, problem_name)
        print(f"--- Finished processing problem: {problem_name} ---")
        time.sleep(5)

    print(f"Finished processing all problems in domain: {domain_name}")
