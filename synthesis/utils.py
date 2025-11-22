# import pddlpy
import base64
import json
import numpy as np
import os 
from google.genai import types
from google import genai
import re
import time
from google.genai import errors as genai_errors
import pylcs

def find_LCS(s1, s2):
    res = pylcs.lcs_string_idx(s1, s2)
    return ''.join([s2[i] for i in res if i != -1])

def call_gemini_with_retry(
    client,
    problem_name: str,
    model_name: str,
    contents: any,
    config: types.GenerateContentConfig,
    initial_delay_seconds: int = 1,
    max_delay_seconds: int = 20
) -> str:
    """Calls the Gemini API with indefinite retry logic for transient errors."""
    num_attempts = 0
    current_delay = initial_delay_seconds
    while True:
        try:
            num_attempts += 1
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )

            if num_attempts > 1:
                print(f"API call succeeded on attempt {num_attempts}.")
            return response.text
        except genai_errors.ServerError as e:
            error_status_code = -1
            if hasattr(e, 'args') and e.args and isinstance(e.args[0], int):
                error_status_code = e.args[0]
            print(f"API ServerError ({e.__class__.__name__}, status: {error_status_code if error_status_code != -1 else 'N/A'}). Attempt {num_attempts}. Retrying in {current_delay}s...")
            time.sleep(current_delay)
            current_delay = min(current_delay * 1.1, max_delay_seconds)
    return "" 


def save_pddl_to_file(pddl_content, path):
    os.makedirs(path, exist_ok=True)
    filename = path + "/domain.pddl"
    with open(filename, 'w') as f:
        f.write(pddl_content)


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    
def synthesize_domain(client, destination_folder, domain_name, problem_name):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    with open(f"{base_dir}/dataset/stimuli/{domain_name}/{problem_name}/{problem_name}.txt", "r") as f:
        instructions = f.read()

    with open(f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/objects.json", "r") as f:
        object_type = json.load(f)

    with open(f"{base_dir}/synthesis/prompts/pddl_domain_prompt.txt", "r") as f:
        prompt = f.read()

    # print(instructions)

    # print(object_type)

    synthesized_actions = 999
    pddl_domain = ""

    valid_flag = False
    
    while valid_flag == False:
        actions_text = call_gemini_with_retry(
            client=client,
            problem_name=problem_name,
            model_name="gemini-2.0-flash",
            contents="Please count the number of actions that can be performed by the agent, based on the text below. Only return a json file in the format of {\"action_name\": [action1, action2,...], \"action_count\": N} and nothing else \n\n" + instructions + "\n\nobjects = " + str(object_type),
            config=types.GenerateContentConfig(
                temperature=1.0
            )
        )
        actions = actions_text.replace("```json", "").strip("`")
            
        # print(actions)

        actions = json.loads(actions)
        print(actions)

        pddl_domain = call_gemini_with_retry(
            client=client,
            problem_name=problem_name,
            model_name="gemini-2.0-flash",
            contents=prompt +"\n\nobjects = " + str(object_type) + "\n\n" + "Please generate a PDDL domain file based on the text above. Only return the PDDL domain file and nothing else." +  instructions ,
            config=types.GenerateContentConfig(
                temperature=1.0
            )
        ).replace("```pddl", "").strip("`")

        if "whitespace" in object_type["background_cells"]:
            pddl_domain = pddl_domain.replace("whitesquare", "whitespace")

        if "whitesquare" in object_type["background_cells"]:
            pddl_domain = pddl_domain.replace("whitespace", "whitesquare")
        
        action_names = re.findall(r'\(:action\s+([^\s\)]+)', pddl_domain)

        print("action_names: ", action_names)

        print("count_actions: ", int(actions["action_count"]))

        if len(action_names)!= len(actions["action_name"]) and len([action for action in action_names if all(a not in action for a in actions["action_name"])]) > 0:
            print(pddl_domain)
            print("Extra actions found. Regenerating domain...")
            
            continue

        else:
            valid_flag = True

        # extra_actions = [action for action in action_names if all(action not in a for a in base_actions)]

        # if int(int(actions["action_count"]) / synthesized_actions) != int(actions["action_count"]) / synthesized_actions:
        #     print(pddl_domain)
        #     print("count_actions: ", int(actions["action_count"]))
        #     print("synthesized_actions: ", synthesized_actions)
        #     print("Number of actions mismatch. Regenerating domain...")
            


    save_pddl_to_file(pddl_domain, f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}")

    for o in object_type["generic_objects"]:
        if any(len(find_LCS(o, unique_obj))>3 for unique_obj in object_type["unique_objects"]):
            object_type["generic_objects"].remove(o)

    output_path = f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/objects.json"
    with open(output_path, "w") as json_file:
        json.dump(object_type, json_file, indent=4)

    return pddl_domain


def synthesize_config(client, destination_folder, domain_name, problem_name):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    with open(f"{base_dir}/dataset/stimuli/{domain_name}/{problem_name}/{problem_name}.txt", "r") as f:
        description = f.read()

    with open(f"{base_dir}/synthesis/prompts/nipe_config_prompt.txt", "r") as f:
        prompt = f.read()

    with open(f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/objects.json", "r") as f:
        object_type_str = f.read() # Renamed to avoid conflict with type keyword

    with open(f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/domain.pddl", "r") as f:
        domain_description = f.read()

    response_text = call_gemini_with_retry(
        client=client,
        problem_name=problem_name,
        model_name="gemini-2.0-flash",
        contents=prompt + "\nTask description:" +description + "\nPDDL domain file:" +domain_description + "\nObjects:" + object_type_str,
        config=types.GenerateContentConfig(
            temperature=1.0,
            response_mime_type = "application/json"
        )
    )
    
    config_data = json.loads(response_text.strip("`"))
    print(json.dumps(config_data, indent=4))

    # all the goal objects are unique objects so no need to modify them

    # try:
    #     parsed_object_info = json.loads(object_type_str)
    #     generic_objects_bases = parsed_object_info.get("generic_objects", [])

    #     if "goals" in config_data and generic_objects_bases:
    #         new_goals = []
    #         for goal_group in config_data["goals"]:
    #             new_goal_group = []
    #             if isinstance(goal_group, list):
    #                 for goal_statement_str in goal_group:
    #                     modified_statement = goal_statement_str
    #                     for base_obj_name in generic_objects_bases:
    #                         pattern = r'\b(' + re.escape(base_obj_name) + r')\b(?!\d)'
    #                         replacement = base_obj_name + "1"
    #                         modified_statement = re.sub(pattern, replacement, modified_statement)
    #                     new_goal_group.append(modified_statement)
    #             else:
    #                 modified_statement = str(goal_group)
    #                 for base_obj_name in generic_objects_bases:
    #                     pattern = r'\b(' + re.escape(base_obj_name) + r')\b(?!\d)'
    #                     replacement = base_obj_name + "1"
    #                     modified_statement = re.sub(pattern, replacement, modified_statement)
    #                 new_goal_group.append(modified_statement)
    #             new_goals.append(new_goal_group)
    #         config_data["goals"] = new_goals
    #         print("Modified config goals:")
    #         print(json.dumps(config_data["goals"], indent=4))
    # except Exception as e:
    #     print(f"Error during goal post-processing: {e}")


    output_path = f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/config.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as json_file:
        json.dump(config_data, json_file, indent=4)
    return config_data


def extract_objects(client, destination_folder, domain_name, problem_name):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    with open(f"{base_dir}/synthesis/prompts/nipe_object_prompt.txt", "r") as f:
        prompt = f.read()

    with open(f"{base_dir}/dataset/stimuli/{domain_name}/{problem_name}/{problem_name}.txt", "r") as f:
        description = f.read()

    # with open(f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/domain.pddl", "r") as f:
    #     domain = f.read()
    #     domain_script = domain.split("(:type")[1].split("(:action")[0]

    valid_objects = False

    while valid_objects == False:
        # try:
            response_text = call_gemini_with_retry(
                client=client,
                problem_name=problem_name,
                model_name="gemini-2.0-flash",
                contents=prompt + "Description:"+ description ,
                config=types.GenerateContentConfig(
                    temperature=1.0,
                    response_mime_type = "application/json"
                )
            )
            objects = response_text.strip("`")

            print(objects)

            objects_json = json.loads(objects)

            if "generic_objects" in objects_json and "unique_objects" in objects_json and "background_cells" in objects_json and "agent" in objects_json:
                if all(agent not in objects_json["generic_objects"] and agent not in objects_json["unique_objects"] for agent in objects_json["agent"]) and all(g_obj not in obj for obj in objects_json["unique_objects"] for g_obj in objects_json["generic_objects"]):    
                    valid_objects = True


            if len(objects_json["unique_objects"]) == 0:
                print("No unique objects found. Regenerating...")
                valid_objects = False

        # except:
        #     print("Error in generating objects. Retrying...")
        #     continue

    output_path = f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/objects.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as json_file:
        json.dump(objects_json, json_file, indent=4)

    return objects_json

def check_valid_synthesis(destination_folder, domain_name, problem_name):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    with open(f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/domain.pddl", "r") as f:
        domain = f.read()
        domain_script = domain.split("(:type")[1].split("(:action")[0]

    with open(f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/config.json", "r") as f:
        config = json.load(f)

    with open(f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/objects.json", "r") as f:
        objects = json.load(f)


        if any(len(val) < 2 for val in config["belief_config"].values()):
            print("belief_config name too short")
            return False

        
        domain_type = domain.split("(:types")[1].split("(:predicates")[0]
        print(domain)

        if "agent" not in domain:
            print("agent name not existent in domain")
            return False

        for obj in objects["background_cells"]:
            if obj not in domain:
                print(f'{obj} name not existent in domain')
                return False

        if config["observability"]=="partial":

            if config["belief_config"]["belief_object"] not in domain_type:
                print(f'{config["belief_config"]["belief_object"]} name not existent in domain')
                return False

            if config["belief_config"]["belief_container"] not in domain_type:
                print(f'{config["belief_config"]["belief_container"]} name not existent in domain')
                return False
            
            if config["belief_config"]["belief_container"] not in objects["generic_objects"]:
                print(f'{config["belief_config"]["belief_container"]} name not existent in object')
                return False

    return True

# def convert_pddl_problem(client,domain_name, problem_name):
#     data = []

#     with open(f"../{destination_folder}/{domain_name}/{problem_name}/objects.json", "r") as f:
#         objects = f.read()


#     with open(f'../{destination_folder}/{domain_name}/{problem_name}.json') as f:
#         data = json.loads(f)

#     for i, frame in data.items():
#         problem_pddl = ""
#         problem_pddl += f"(define (problem {problem_name})\n"
#         problem_pddl += f"  (:domain {problem_name})\n"
#         problem_pddl += synthesize_pddl_objects(client, problem_name)
#         problem_pddl += "  (:init\n"

#         height = len(frame)
#         width = len(frame[0])
#         for obj in objects["static_obj"]:
#             problem_pddl += f"(= ({obj}) (new-bit-matrix false {height} {width}))\n"

#         # for i, row in enumerate(frame):
#         #     for j, cell in enumerate(row):
#         #         for k, obj in enumerate(cell):
#         #             if obj["name"] in objects["static_obj"]:
#         #                 problem_pddl += f"(= ({obj["name"]}) (set-index {obj["name"]} true {i} {j}))\n"
#         #             else:
#         #                 problem_pddl += f"(= xloc {obj["name"]} i)\n"
#         #                 problem_pddl += f"(= yloc {obj["name"]} j)\n"

#         #                 # if obj["attribute"]
#         #             problem_pddl += f"    {obj}\n"
#         problem_pddl += "  )\n"

#         problem_pddl += "(:goal true)"

#     save_pddl_to_file(problem_pddl, f"../{destination_folder}/{problem_name}/problem.pddl")




