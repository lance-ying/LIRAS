import re
from typing import List, Dict, Any, Optional, Tuple
import os
import json
from PIL import Image, ImageSequence
import base64
import numpy as np
import io
import argparse
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
import time
from utils import call_gemini_with_retry

def load_gif_by_frame_and_cells(gif_path: str, dim: Tuple[int, int]) -> Tuple[List[List[List[str]]], List[List[List[float]]], List[List[List[float]]], Dict[float, List[Tuple[int, int, int]]]]:
    frames_cells = []
    frames_cells_vals = []
    frames_cells_stds = []
    pixel_value_to_all_indices = {} 
    
    with Image.open(gif_path) as gif:
        for frame_idx, frame in enumerate(ImageSequence.Iterator(gif)):
            rgb_frame = frame.convert('RGB')
            width, height = rgb_frame.size
            cell_width = width // dim[1]
            cell_height = height // dim[0]
            
            current_frame_cells_list = []
            current_frame_vals_list = []
            current_frame_stds_list = []
            for i in range(dim[0]):
                row_cells = []
                row_vals = []
                row_stds = []
                for j in range(dim[1]):
                    left = j * cell_width
                    upper = i * cell_height
                    right = left + cell_width
                    lower = upper + cell_height
                    
                    cell_image_pil = rgb_frame.crop((left, upper, right, lower))
                    cell_image_pil_resized = cell_image_pil.resize((100, 100)).crop((3, 3, 97, 97))

                    cell_pixel_array = np.array(cell_image_pil_resized)
                    cell_mean_val = str(int(np.ceil(cell_pixel_array.mean())))
                    cell_std_dev = round(np.array(cell_image_pil_resized).std(axis=(0,1)).mean(), 2)
                    
                    if cell_mean_val not in pixel_value_to_all_indices:
                        pixel_value_to_all_indices[cell_mean_val] = []
                    pixel_value_to_all_indices[cell_mean_val].append((frame_idx, i, j))
                    
                    buffer = io.BytesIO()
                    cell_image_pil_resized.save(buffer, format="JPEG")
                    buffer.seek(0)
                    cell_base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    
                    row_cells.append(cell_base64_str)
                    row_vals.append(cell_mean_val)
                    row_stds.append(cell_std_dev)

                current_frame_cells_list.append(row_cells)
                current_frame_vals_list.append(row_vals)
                current_frame_stds_list.append(row_stds)
            
            frames_cells.append(current_frame_cells_list)
            frames_cells_vals.append(current_frame_vals_list)
            frames_cells_stds.append(current_frame_stds_list)
            
    return frames_cells, frames_cells_vals, frames_cells_stds, pixel_value_to_all_indices


def _extract_pddl_block_content(text: str, keyword: str) -> str:
    if not keyword.startswith('('):
        keyword = "(" + keyword

    start_keyword_idx = text.find(keyword)
    if start_keyword_idx == -1:
        return ""
    
    content_start_idx = start_keyword_idx + len(keyword)
    while content_start_idx < len(text) and text[content_start_idx].isspace():
        content_start_idx += 1

    balance = 1 
    content_end_idx = -1

    for i in range(content_start_idx, len(text)):
        if text[i] == '(':
            balance += 1
        elif text[i] == ')':
            balance -= 1
            if balance == 0: 
                content_end_idx = i
                break
    
    if content_start_idx != -1 and content_end_idx != -1 and content_start_idx < content_end_idx:
        return text[content_start_idx:content_end_idx].strip()
    return ""

# def _get_pddl_domain_details(domain_pddl_content: str) -> Dict[str, List[str]]:
#     """Parses domain PDDL content to extract specific details like defined color constants."""
#     details = {"colors": []}
#     constants_section = _extract_pddl_block_content(domain_pddl_content, "(:constants")
#     if constants_section:
#         for line in constants_section.split('\n'):
#             line = line.strip().lower()
#             if ' - color' in line:
#                 color_names_str = line.split(' - color')[0]
#                 details["colors"].extend(c.strip() for c in color_names_str.split() if c.strip())
    
#     types_section = _extract_pddl_block_content(domain_pddl_content, "(:types")
#     if types_section:
#         for line in types_section.split('\n'):
#             line = line.strip().lower()
#             if ' - color' in line:
#                 color_names_str = line.split(' - color')[0]
#                 details["colors"].extend(c.strip() for c in color_names_str.split() if c.strip())

#     details["colors"] = sorted(list(set(details["colors"])))
#     return details


def synthesize_pddl_objects(client, domain_name, problem_name, objects):
    # with open(f"../dataset/stimuli/{domain_name}/{problem_name}/{problem_name}.txt", "r") as f:
    #     description = f.read()

    objects_kind = set([re.sub(r'\d+$', '', obj) for obj in objects])

    object_dict ={}
    for kind in objects_kind:
        object_dict[kind] = []
        for o in objects:
            if kind in o:
                object_dict[kind].append(o)

    pddl_obj_str = "(:objects\n"
    for k, val in object_dict.items():
        if len(val) > 1:
            pddl_obj_str += f"{' '.join(sorted(list(set(val))))} - {k}\n"

    pddl_obj_str += ")\n"

    return pddl_obj_str


# def synthesize_pddl_objects(client, domain_name, problem_name, objects_detected_in_frame: Dict[str, List[str]], object_categories_config: Dict[str, Any]):
#     """Manually constructs the PDDL (:objects ...) string based on detected objects and domain constants/types."""
#     base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
#     domain_pddl_path = f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/domain.pddl"
#     if not os.path.exists(domain_pddl_path):
#         return ""
        
#     with open(domain_pddl_path, "r") as f:
#         domain_content = f.read()

#     parsed_domain_object_to_type = {} 
#     defined_pddl_types = set() 
    
#     types_section_content = _extract_pddl_block_content(domain_content, "(:types")
#     for line in types_section_content.split('\n'):
#         line = line.strip()
#         if not line or line.startswith(';'): continue
#         line = line.split(';')[0].strip()
#         if not line: continue

#         if '-' in line: 
#             parts = line.split('-', 1)
#             if len(parts) == 2:
#                 names_str = parts[0].strip()
#                 supertype_name_str = parts[1].strip()
#                 supertype_name = supertype_name_str.split()[0] if supertype_name_str.split() else None
#                 if supertype_name:
#                     object_names = names_str.split()
#                     for name in object_names:
#                         if name: 
#                             parsed_domain_object_to_type[name.lower()] = supertype_name
#                             defined_pddl_types.add(name.lower())
#                             defined_pddl_types.add(supertype_name.lower())
#         else: 
#             object_names = line.split()
#             for name in object_names:
#                 if name:
#                     if name.lower() not in parsed_domain_object_to_type: 
#                         parsed_domain_object_to_type[name.lower()] = name 
#                     defined_pddl_types.add(name.lower()) 
    
#     constants_section_content = _extract_pddl_block_content(domain_content, "(:constants")
#     constants_set_lower = set()
#     for line in constants_section_content.split('\n'):
#         line = line.strip()
#         if not line or line.startswith(';') or line == ")": continue
#         line = line.split(';')[0].strip()
#         if not line: continue

#         type_name_from_constant = None
#         names_str = line

#         if ' - ' in line:
#             parts = line.rsplit(' - ', 1)
#             if len(parts) == 2:
#                 names_str = parts[0].strip()
#                 type_name_str = parts[1].strip()
#                 if type_name_str.split():
#                     type_name_from_constant = type_name_str.split()[0]
        
#         constant_names_in_line = names_str.split() 
#         for const_name in constant_names_in_line:
#             if const_name: 
#                 const_name_lower = const_name.lower()
#                 constants_set_lower.add(const_name_lower)
#                 if type_name_from_constant:
#                      parsed_domain_object_to_type[const_name_lower] = type_name_from_constant
#                      defined_pddl_types.add(type_name_from_constant.lower())

#     objects_to_declare_by_type = {} 
#     all_seen_objects_original_case = set()
#     if "unique_objects" in objects_detected_in_frame:
#         all_seen_objects_original_case.update(objects_detected_in_frame["unique_objects"])
#     if "generic_objects" in objects_detected_in_frame:
#         all_seen_objects_original_case.update(objects_detected_in_frame["generic_objects"])
#     if "agent" in objects_detected_in_frame: 
#         all_seen_objects_original_case.update(objects_detected_in_frame["agent"])

#     if "unique_objects" in object_categories_config:
#         all_seen_objects_original_case.update(object_categories_config["unique_objects"])
#     if "agent" in object_categories_config:
#         all_seen_objects_original_case.update(object_categories_config["agent"])

#     for obj_name_orig_case in all_seen_objects_original_case:
#         obj_name_lower = obj_name_orig_case.lower()
#         if obj_name_lower in constants_set_lower:
#             continue 

#         obj_pddl_type = None
#         base_name_lower = re.sub(r'\d+$', '', obj_name_lower)
#         if obj_name_lower in parsed_domain_object_to_type:
#             obj_pddl_type = parsed_domain_object_to_type[obj_name_lower]
#         elif base_name_lower in parsed_domain_object_to_type:
#             obj_pddl_type = parsed_domain_object_to_type[base_name_lower]
        
#         if not obj_pddl_type:
#             if "item" in defined_pddl_types:
#                 obj_pddl_type = "item"
#             elif "object" in defined_pddl_types: 
#                 obj_pddl_type = "object"
#             else:
#                 print(f"Warning: Type for non-constant object '{obj_name_orig_case}' (lc: '{obj_name_lower}') not found, and neither 'item' nor 'object' are defined PDDL types. Skipping declaration.")
#                 continue
        
#         actual_name_to_declare = obj_name_orig_case
#         generic_object_bases_lower = [gn.lower() for gn in object_categories_config.get("generic_objects", [])]
#         is_generic = (base_name_lower in generic_object_bases_lower) or (obj_name_lower in generic_object_bases_lower)

#         if is_generic and not obj_name_lower[-1].isdigit():
#             actual_name_to_declare = obj_name_orig_case + "1"

#         if obj_pddl_type not in objects_to_declare_by_type:
#             objects_to_declare_by_type[obj_pddl_type] = []
#         objects_to_declare_by_type[obj_pddl_type].append(actual_name_to_declare)

#     pddl_objects_parts = []
#     for type_name, names_list in objects_to_declare_by_type.items():
#         if names_list:
#             pddl_objects_parts.append(f"{' '.join(sorted(list(set(names_list))))} - {type_name}")
    
#     final_pddl_objects_str = ""
#     if pddl_objects_parts:
#         final_pddl_objects_str = f"(:objects {' '.join(pddl_objects_parts)})"
    
#     return final_pddl_objects_str

def get_cell_prompt(destination_folder, loc, objects, domain_name, problem_name):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    with open(f"{base_dir}/dataset/stimuli/{domain_name}/{problem_name}/{problem_name}.txt", "r") as f:
        description = f.read()
    with open(f"{base_dir}/synthesis/prompts/pddl_classify_cell_type.txt", "r") as f:
        cell_prompt = f.read()
    with open(f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/objects.json", "r") as f:
        object_types = json.load(f)

    cell_prompt += f"Description of the domain: {description}\n"
    cell_prompt += f"List of cell types in the domain: {object_types['background_cells']}\n"
    cell_prompt += "Please classify the cell in the image and return a json file.\n"
    return cell_prompt

def get_object_prompt(destination_folder, domain_name, problem_name):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    with open(f"{base_dir}/dataset/stimuli/{domain_name}/{problem_name}/{problem_name}.txt", "r") as f:
        description = f.read()
    with open(f"{base_dir}/synthesis/prompts/pddl_problem_prompt.txt", "r") as f:
        object_prompt = f.read()
    with open(f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/objects.json", "r") as f:
        object_types_config = json.load(f)

        relevant_object_categories = []
        
        for k in ["unique_objects", "generic_objects", "agent"]:
            relevant_object_categories.extend(object_types_config[k])
        print(f"Relevant object categories: {relevant_object_categories}")
    with open(f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/domain.pddl", "r") as f:
        domain_pddl_content = f.read()

    attributes_str = ""
    if "(:predicates" in domain_pddl_content:
        predicates_section = _extract_pddl_block_content(domain_pddl_content, "(:predicates")
        attributes_str = "\n".join([line.strip() for line in predicates_section.split('\n') if line.strip() and not line.strip().startswith(';')])
    
    object_prompt += f"Description of the domain: {description}\n"
    object_prompt += f"List of objects in the domain: {relevant_object_categories}. Please only use object names in this list\n"
    object_prompt += f"List of attributes in the domain: {attributes_str}\n"
    object_prompt += "Please parse the object in the image and return a json file.\n"
    return object_prompt

def classify_cell(    
    client,
    destination_folder,
    image: str, 
    loc: List[int],
    domain_name: str,
    problem_name: str,
    objects: List[str],
    temperature: float = 0.2):
    config_obj = types.GenerateContentConfig(
        temperature=temperature,
        response_mime_type= 'application/json'
    )
    cell_prompt = get_cell_prompt(destination_folder, loc,  objects, domain_name, problem_name)
    header, encoded_data = image.split(",", 1)
    mime_type = header.split(":")[1].split(";")[0]
    image_bytes = base64.b64decode(encoded_data)
    
    return call_gemini_with_retry(
        client=client,
        problem_name=problem_name,
        model_name="gemini-2.0-flash",
        contents=[
            cell_prompt,
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        ],
        config=config_obj 
    )

def classify_object(
    client,
    destination_folder,
    image: str, 
    domain_name: str,
    problem_name: str,
    temperature: float = 0.2,
) -> str:
    config_obj = types.GenerateContentConfig(
        temperature=temperature,
        response_mime_type= 'application/json'
    )
    object_prompt = get_object_prompt(destination_folder, domain_name, problem_name)
    header, encoded_data = image.split(",", 1)
    mime_type = header.split(":")[1].split(";")[0] 
    image_bytes = base64.b64decode(encoded_data)
    
    return call_gemini_with_retry(
        client=client,
        problem_name=problem_name,
        model_name="gemini-2.0-flash",
        contents=[
            object_prompt,
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        ],
        config=config_obj 
    )

def classify_unique_cells(
    client,
    destination_folder: str,
    pixel_value_to_all_indices: Dict[float, List[Tuple[int, int, int]]],
    frames_cells: List[List[List[str]]],
    frames_cells_stds: List[List[List[float]]],
    domain_name: str,
    problem_name: str,
    objects: List[str], 
    temperature: float = 0.2
) -> Dict[float, str]:
    """Classify cells based on their unique average pixel values."""


    unique_pixel_value_to_cell_type_path = f"../{destination_folder}/{domain_name}/{problem_name}/unique_pixel_value_to_cell_type.json"
    # if os.path.exists(unique_pixel_value_to_cell_type_path):
    #     with open(unique_pixel_value_to_cell_type_path, "r") as f:
    #         return json.load(f)
    pixel_value_to_type = {}
    total_cell_instances = sum(len(indices_list) for indices_list in pixel_value_to_all_indices.values())
    unique_pixel_values_count = len(pixel_value_to_all_indices)
    
    print(f"Total cell instances across all frames: {total_cell_instances}")
    print(f"Unique mean pixel values to classify: {unique_pixel_values_count}")
    if total_cell_instances > unique_pixel_values_count:
         print(f"LLM calls for background saved by unique classification: {total_cell_instances - unique_pixel_values_count}")
    
    for i, (pixel_value, indices_list) in enumerate(pixel_value_to_all_indices.items()):
        frame_idx, row, col = indices_list[0]
        cell_image_base64 = frames_cells[frame_idx][row][col]
        

        cell_image_url = f"data:image/jpeg;base64,{cell_image_base64}"
        
        print(f"Classifying unique cell type {i+1}/{unique_pixel_values_count} (pixel_value: {pixel_value})...")

        cell_type_json_str = classify_cell(
            client,
            destination_folder,
            image=cell_image_url,
            loc=[row+1, col+1], 
            domain_name=domain_name,
            problem_name=problem_name,
            objects=objects, 
            temperature=temperature
        )

        cell_type_data = json.loads(cell_type_json_str.strip("`").strip("json"))

        if frames_cells_stds[frame_idx][row][col] < 0.1:
            cell_content_data = {"object_name": [], "object_pddl_str": ""}
        else:
            cell_content_json_str = classify_object(
                        client, destination_folder, cell_image_url, domain_name, 
                        problem_name,temperature=0.2,
                )

            cell_content_data = json.loads(cell_content_json_str.strip("`").strip("json"))

        # print(f"Cell ({row+1},{col+1}) classified as: {cell_type_data}")
        classified_type = {"type": cell_type_data["cell_type"], "objects": cell_content_data["object_name"], "object_pddl_str": cell_content_data["object_pddl_str"]}
        pixel_value_to_type[pixel_value] = classified_type

    return pixel_value_to_type

def generate_pddl_from_mapping(
    pixel_value_to_indices_current_frame: Dict[float, List[Tuple[int, int, int]]],
    unique_pixel_value_to_cell_type: Dict[float, str],
    rows: int,
    cols: int,
    domain_name: str 
) -> str:
    """Generate PDDL init facts for background cells for the current frame."""
    pddl_init_bg_facts = []
    frame_specific_actual_pddl_types = set()
    for pixel_value, _ in pixel_value_to_indices_current_frame.items():
        classified_type = unique_pixel_value_to_cell_type.get(str(pixel_value))

        actual_pddl_type = classified_type["type"]
        # if domain_name == "foodtruck" and classified_type == "blackspace":
        #     actual_pddl_type = "building"

        frame_specific_actual_pddl_types.add(actual_pddl_type)

    for pddl_type_to_init in frame_specific_actual_pddl_types:
        pddl_init_bg_facts.append(f"(= ({pddl_type_to_init}) (new-bit-matrix false {rows} {cols}))")
    pddl_init_bg_facts.append(f"(= (gridheight) {rows})")
    pddl_init_bg_facts.append(f"(= (gridwidth) {cols})")
    
    for pixel_value, indices_list_for_pv in pixel_value_to_indices_current_frame.items():
        classified_type = unique_pixel_value_to_cell_type.get(str(pixel_value))

        actual_pddl_type = classified_type["type"]
        # if domain_name == "foodtruck" and classified_type == "blackspace":
        #     actual_pddl_type = "building"
        
        for frame_idx, row, col in indices_list_for_pv: 
            pddl_init_bg_facts.append(f"(= ({actual_pddl_type}) (set-index {actual_pddl_type} true {row+1} {col+1}))")

    return "\n".join(pddl_init_bg_facts)

def generate_per_image(
    client,
    destination_folder,
    current_frame_cells: List[List[str]],
    current_frame_vals: List[List[float]],
    current_frame_stds: List[List[float]],
    domain_name: str, 
    problem_name: str,
    frame_number: int,
    pixel_value_to_all_indices: Dict[float, List[Tuple[int, int, int]]], 
    unique_pixel_value_to_cell_content: Dict[float, str]
):
    """Generates PDDL for a single frame using unique pixel classification for background and object detection for dynamic elements."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    rows = len(current_frame_cells)
    cols = len(current_frame_cells[0]) if rows > 0 else 0
    
    # Initialize/load here
    unique_objects_detected_in_frame = set()
    generic_objects_detected_in_frame = []
    object_type_path = f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/objects.json"
    object_categories_config = {}
    if os.path.exists(object_type_path):
        with open(object_type_path, "r") as f:
            object_categories_config = json.load(f)

    domain_pddl_path = f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/domain.pddl"
    with open(domain_pddl_path, "r") as f:
        domain_pddl_content = f.read()

    # valid_pddl_colors = set()
    # domain_details = _get_pddl_domain_details(domain_pddl_content)
    # valid_pddl_colors = set(domain_details.get("colors", []))

    pddl_problem_header = f"(define (problem {problem_name})\n (:domain {domain_name})"
    
    current_frame_pixel_value_indices = {}
    if frame_number is not None:
        for pv, all_indices_for_pv in pixel_value_to_all_indices.items():
            indices_for_current_frame = [(f_idx, r, c) for f_idx, r, c in all_indices_for_pv if f_idx == frame_number]
            if indices_for_current_frame:
                current_frame_pixel_value_indices[pv] = indices_for_current_frame
    
    pddl_init_background_facts_str = generate_pddl_from_mapping(
        current_frame_pixel_value_indices, 
        unique_pixel_value_to_cell_content,
        rows, cols, domain_name
    )
    pddl_init_dynamic_objects_facts_list = []

    generic_object_dict = {}

    if len(object_categories_config["agent"]) > 1:
        pddl_init_dynamic_objects_facts_list.append(f"(= (agentcode {object_categories_config['agent'][0]}) 0)")
        pddl_init_dynamic_objects_facts_list.append(f"(= (agentcode {object_categories_config['agent'][1]}) 1)")
        pddl_init_dynamic_objects_facts_list.append(f"(= (turn) {frame_number % 2})")

    for r in range(rows):
        for c in range(cols):
            if current_frame_stds[r][c] > 0.1:
                cell_image_base64 = current_frame_cells[r][c]
                cell_image_url = f"data:image/jpeg;base64,{cell_image_base64}"

                object_list = unique_pixel_value_to_cell_content.get(current_frame_vals[r][c])["objects"]

                cell_object_pddl_str = unique_pixel_value_to_cell_content.get(current_frame_vals[r][c])["object_pddl_str"]

                cell_object_pddl_str = cell_object_pddl_str.replace("$i", str(r+1)).replace("$j", str(c+1))

                for o in object_list:
                    if o in object_categories_config["unique_objects"]:
                        unique_objects_detected_in_frame.add(o)
                    if o in object_categories_config["generic_objects"]:
                        if o not in generic_object_dict:
                            generic_object_dict[o] = 1
                            cell_object_pddl_str = cell_object_pddl_str.replace(" "+o," "+o + "1")
                            generic_objects_detected_in_frame.append(o + "1")
                        else:
                            generic_object_dict[o] += 1
                            cell_object_pddl_str = cell_object_pddl_str.replace(" "+o, " "+o + str(generic_object_dict[o]))
                            generic_objects_detected_in_frame.append(o + str(generic_object_dict[o]))
                pddl_init_dynamic_objects_facts_list.append(cell_object_pddl_str)
                # print(f"Cell ({r+1},{c+1}) classified as: {cell_object_data}")
                # if "object_pddl_str" in cell_object_data and cell_object_data["object_pddl_str"]:
                #     for pred_line in cell_object_data["object_pddl_str"].split('\n'):
                #         clean_line = pred_line.strip()
                #         if not clean_line: continue
                #         modified_pred_line = clean_line
                #         constants_set_lower = set() 
                #         if domain_pddl_content:
                #             constants_section_content = _extract_pddl_block_content(domain_pddl_content, "(:constants")
                #             for line_const in constants_section_content.split('\n'):
                #                 line_const = line_const.strip()
                #                 if not line_const or line_const.startswith(';') or line_const == ")": continue
                #                 line_const = line_const.split(';')[0].strip()
                #                 if not line_const: continue
                #                 names_str_const = line_const.split(' - ')[0] if ' - ' in line_const else line_const
                #                 for const_name in names_str_const.split():
                #                     if const_name: constants_set_lower.add(const_name.lower())

                #         for generic_base_name in object_categories_config.get("generic_objects", []):
                #             if generic_base_name.lower() not in constants_set_lower:
                #                 pattern = r'([\(\s])(' + re.escape(generic_base_name) + r')([\s\)])'
                #                 replacement_str = r'\1' + generic_base_name + "1" + r'\3'
                #                 modified_pred_line = re.sub(pattern=pattern, repl=replacement_str, string=modified_pred_line, flags=re.IGNORECASE)
                        
                #         if modified_pred_line.startswith("(iskeycolor") or modified_pred_line.startswith("(isdoorcolor"):
                #             color_val = modified_pred_line.split()[-1][:-1].lower()
                #             if color_val not in valid_pddl_colors:
                #                 print(f"Warning: LLM proposed invalid PDDL color '{color_val}' in predicate: {modified_pred_line}. Valid colors: {valid_pddl_colors}. Frame: {frame_number}, Cell: ({r+1},{c+1})")

                #         pddl_init_dynamic_objects_facts_list.append(modified_pred_line)
                # if "object_name" in cell_object_data:
                #     for o_name in cell_object_data["object_name"]:
                #         if not o_name: continue
                #         o_name_base = re.sub(r'\d+$', '', o_name)
                #         for category, cat_names in object_categories_config.items():
                #             if isinstance(cat_names, list) and (o_name in cat_names or o_name_base in cat_names):
                #                 if category in objects_detected_in_frame and o_name not in objects_detected_in_frame[category]:
                #                     objects_detected_in_frame[category].append(o_name)
                #                 break
    
    for cat_key in object_categories_config["unique_objects"]:
        if cat_key not in unique_objects_detected_in_frame:
            pddl_init_dynamic_objects_facts_list.append(f"(= (xloc {cat_key}) -1)")
            pddl_init_dynamic_objects_facts_list.append(f"(= (yloc {cat_key}) -1)")


    full_pddl_str = pddl_problem_header + "\n"

    # print(f"Unique objects detected in frame {frame_number}: {unique_objects_detected_in_frame}")
    if len(generic_objects_detected_in_frame) > 0:

        if frame_number == 0:

            pddl_objects_declaration_str = synthesize_pddl_objects(client, domain_name, problem_name, generic_objects_detected_in_frame)
            full_pddl_str += pddl_objects_declaration_str + "\n"

            object_categories_config["obj_str"] = pddl_objects_declaration_str

            with open(object_type_path, "w") as f:
                json.dump(object_categories_config, f, indent=4)

        else:

            pddl_objects_declaration_str = object_categories_config["obj_str"]
            full_pddl_str += pddl_objects_declaration_str + "\n"
        
        
    full_pddl_str += "(:init \n"
    full_pddl_str += pddl_init_background_facts_str + "\n"
    if pddl_init_dynamic_objects_facts_list:
        full_pddl_str += "\n".join(pddl_init_dynamic_objects_facts_list) + "\n"
    full_pddl_str += ")\n" 
    full_pddl_str += "(:goal (true)) \n)" 
    
    pddl_file_path = f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/frame_{frame_number}.pddl"
    os.makedirs(os.path.dirname(pddl_file_path), exist_ok=True)
    with open(pddl_file_path, "w") as pddl_file:
        pddl_file.write(full_pddl_str)
    return None

def generate_problem_pddl(client, destination_folder, domain_name, problem_name):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    config_path = f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/config.json"
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        return
    with open(config_path, "r") as f:
        config = json.load(f)

    image_path = f"{base_dir}/dataset/stimuli/{domain_name}/{problem_name}/{problem_name}.gif"
    if not os.path.exists(image_path):
        print(f"Error: GIF file not found at {image_path}")
        return
    grid_size = config.get("grid_size")
    if not grid_size or not (isinstance(grid_size, list) and len(grid_size) == 2):
        print(f"Error: Invalid grid_size in config: {grid_size}. Expected [rows, cols].")
        return

    frames_cells, frames_cells_vals, frames_cells_stds, pixel_value_to_all_indices = load_gif_by_frame_and_cells(image_path, grid_size)
    
    unique_pixel_value_to_cell_type = classify_unique_cells(
        client,
        destination_folder,
        pixel_value_to_all_indices, 
        frames_cells, 
        frames_cells_stds,
        domain_name,
        problem_name,
        [], 
        temperature=0.2
    )

    print(f"Unique pixel values classified: {unique_pixel_value_to_cell_type}")

    # Save the unique pixel value to cell type mapping to a JSON file
    output_path = f"{base_dir}/{destination_folder}/{domain_name}/{problem_name}/unique_pixel_value_to_cell_type.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as json_file:
        json.dump(unique_pixel_value_to_cell_type, json_file, indent=4)
    print(f"Unique pixel value to cell type mapping saved to: {output_path}")
    
    total_frames = len(frames_cells)
    print(f"Processing {total_frames} frames from GIF: {problem_name}")

    for frame_idx in range(total_frames):
        generate_per_image(
            client,
            destination_folder,
            frames_cells[frame_idx],
            frames_cells_vals[frame_idx],
            frames_cells_stds[frame_idx],
            domain_name,
            problem_name,
            frame_idx,      
            pixel_value_to_all_indices, 
            unique_pixel_value_to_cell_type
        )
        
    return None