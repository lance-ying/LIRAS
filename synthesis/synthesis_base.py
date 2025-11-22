from utils import *
import os
import argparse
from google import genai
from segment_cells import *
import time

def __main__():
    parser = argparse.ArgumentParser(description="Synthesize domain and problem files for PDDL.")
    parser.add_argument("--api_addr", type=str, help="Path to the api file.")
    parser.add_argument("--problem_path", type=str, help="Path to the problem file.")
    parser.add_argument("--destination_folder", type=str, help="Path to the destination folder.")


    args = parser.parse_args()
    path = args.problem_path
    api_addr = args.api_addr
    destination_folder = args.destination_folder

    domain_name = path.split("/")[-2]
    problem_name = path.split("/")[-1]

    print(f"domain_name: {domain_name}")


    with open(api_addr, "r") as f:
        gemini_api_key = f.read()


    client_gemini = genai.Client(api_key=gemini_api_key)

    domain_name = path.split("/")[-2]
    problem_name = path.split("/")[-1]

    # print(f"domain_name: {domain_name}")
    # print(f"problem_name: {problem_name}")

    print(f"--- Processing problem: {problem_name} ---")

        # try:
    extract_objects(client_gemini, destination_folder, domain_name, problem_name)
    synthesize_domain(client_gemini, destination_folder, domain_name, problem_name)
    synthesize_config(client_gemini, destination_folder, domain_name, problem_name)
    generate_problem_pddl(client_gemini, destination_folder, domain_name, problem_name)
    print(f"--- Finished processing problem: {problem_name} ---")


if __name__ == "__main__":
    __main__()