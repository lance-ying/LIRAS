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

    # # Create a JSON file to store token counts
    # token_count = {"dkg_single": 0}
    # json_file_path = os.path.join(os.path.dirname(__file__), "../synthesis_exp/token_count.json")

    # with open(json_file_path, "w") as json_file:
    #     json.dump(token_count, json_file)


    with open(api_addr, "r") as f:
        gemini_api_key = f.read()


    client_gemini = genai.Client(api_key=gemini_api_key)

    domain_name = path.split("/")[-2]
    problem_name = path.split("/")[-1]

    # print(f"domain_name: {domain_name}")
    # print(f"problem_name: {problem_name}")

    print(f"--- Processing problem: {problem_name} ---")

    valid_synthesis = False
    num_retries = 0
    max_retries = 7
    while not valid_synthesis and num_retries < max_retries:
        # try:
            extract_objects(client_gemini, destination_folder,domain_name, problem_name)
            synthesize_domain(client_gemini, destination_folder,domain_name, problem_name)
            synthesize_config(client_gemini, destination_folder,domain_name, problem_name)


            valid_synthesis = check_valid_synthesis(destination_folder,domain_name, problem_name)
        # except Exception as e:
        #     print(f"Error during synthesis: {e}")
            num_retries += 1
            time.sleep(5)  # Wait before retrying
    generate_problem_pddl(client_gemini, destination_folder, domain_name, problem_name)
    print(f"--- Finished processing problem: {problem_name} ---")


if __name__ == "__main__":
    __main__()