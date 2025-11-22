import os
import json
from segment_cells import *
from google import genai
from utils import *

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

domain_name = "astronaut"
problem_name = "astronaut_2"

synthesize_domain(client, domain_name, problem_name)
extract_objects(client, domain_name, problem_name)
synthesize_config(client, domain_name, problem_name)
generate_problem_pddl(client, domain_name, problem_name)

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

pddl_file_path = f"{base_dir}/temp/{domain_name}/{problem_name}/frame_0.pddl"
with open(pddl_file_path, "r") as f:
    print(f"--- Contents of {pddl_file_path} ---")
    print(f.read())
