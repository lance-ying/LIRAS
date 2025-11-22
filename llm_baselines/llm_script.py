#!/usr/bin/env python3
import os
import base64
import io
from typing import List, Dict, Any, Tuple
from PIL import Image
import json
import re
import time
import concurrent.futures
from openai import OpenAI

# Constants and model definitions
MODELS = [
    "gpt-4o-2024-11-20",
    "o3-2025-04-16",
    "gemini-2.0-flash-001",
]

# Initialize clients - we'll create these in each worker process to avoid sharing connections
def get_openai_client():
    return OpenAI(
        api_key=''
    )

def get_google_client():
    return OpenAI(
        api_key='',
        base_url='https://generativelanguage.googleapis.com/v1beta/openai/'
    )

# Get the project directory
project_dir = os.path.dirname(os.getcwd())
print(f"Project directory: {project_dir}")

def get_folders(domain: str) -> List[str]:
    """Get all the stimulus folders in the domain"""
    # Path to the directory
    path = os.path.join(project_dir, 'dataset', 'stimuli', domain)
    # Get all the items in the directory
    items = os.listdir(path)
    # Filter for directories only
    folders = [item for item in items if os.path.isdir(os.path.join(path, item))]
    
    # Sort the folders numerically
    folders.sort(key=lambda x: int(x.rsplit('_', 1)[1]))
    return folders

def extract_gif_frames(gif_path: str) -> List[str]:
    """Extract all frames from a GIF and convert them to base64 strings"""
    gif = Image.open(gif_path)
    frames = []
    
    for frame_idx in range(gif.n_frames):
        gif.seek(frame_idx)
        # Convert frame to RGB if it's not already
        frame = gif.convert('RGB')
        
        # Save frame to bytes
        img_byte_arr = io.BytesIO()
        frame.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # Convert to base64
        img_base64 = base64.b64encode(img_byte_arr).decode('utf-8')
        frames.append(img_base64)
    
    return frames

def get_stimulus_files(domain: str, folder_name: str):
    """Get the txt description and gif frames"""
    folder_path = os.path.join(project_dir, 'dataset', 'stimuli', domain, folder_name)
    txt_path = os.path.join(folder_path, folder_name+'.txt')
    gif_path = os.path.join(folder_path, folder_name+'.gif')
    
    with open(txt_path, 'r') as file:
        description = file.read()
    
    frames = extract_gif_frames(gif_path)
    return description, frames

def extract_answer_content(text, method):
    """Answer extraction"""
    if method == 'cot':
        patterns = [
            r'Answer: (.*)',
            r'Answer:\n(.*)',
            r'\*\*Answer:\*\* (.*)',
            r'\*\*Answer\*\*: (.*)',
            r'```\n(.*)\n```',
            r'```python\n(.*)\n```'
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                return matches[-1].replace('```', '').replace('\\', '').replace('`', '').strip()
        return text.strip()
    else:
        pattern = r'<answer>(.*?)</answer>'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        else:
            return text.strip()

def run_baseline(config: Tuple[str, str, str, int]) -> Dict[str, Any]:
    """
    Run a baseline for a given domain, model, and method
    
    Args:
        config: A tuple of (domain, model, method, run_num)
        
    Returns:
        A dictionary with results of the run
    """
    domain, model, method, run_num = config
    
    # Create clients for this process
    openai_client = get_openai_client()
    google_client = get_google_client()
    
    print(f"\n[STARTING] Domain: {domain}, Model: {model}, Method: {method}, Run: {run_num}")
    
    # Get folders and stimulus files
    print(f"  [INFO] Getting folders for {domain}...")
    folders = get_folders(domain)
    print(f"  [INFO] Found {len(folders)} folders")
    
    print(f"  [INFO] Loading stimulus files...")
    all_files = [get_stimulus_files(domain, folder) for folder in folders]
    print(f"  [INFO] Loaded {len(all_files)} stimulus files")

    if "ablated" in method:

        if "dkg" not in domain:
            prompt_path = os.path.join(project_dir, 'llm_baselines', 'prompts', domain, f'cot.txt')
        else:
            prompt_path = os.path.join(project_dir, 'llm_baselines', 'prompts', 'dkg', f'cot.txt')

    else:
    # Get prompt file path
        if "dkg" not in domain:
            prompt_path = os.path.join(project_dir, 'llm_baselines', 'prompts', domain, f'{method}.txt')
        else:
            prompt_path = os.path.join(project_dir, 'llm_baselines', 'prompts', 'dkg', f'{method}.txt')
        
    # Read prompt
    print(f"  [INFO] Reading prompt from {prompt_path}")
    with open(prompt_path, 'r') as file:
        prompt = file.read()
    
    # Load additional info for astronaut domain
    counts = None
    order_info = None
    if 'astronaut' in domain:
        print(f"  [INFO] Loading additional astronaut data...")
        counts_path = os.path.join(project_dir, 'llm_baselines', 'prompts', 'astronaut', 'counts.json')
        order_info_path = os.path.join(project_dir, 'llm_baselines', 'prompts', 'astronaut', 'order_info.json')
        
        with open(counts_path, 'r') as file:
            counts = json.load(file)
        
        with open(order_info_path, 'r') as file:
            order_info = json.load(file)
        print(f"  [INFO] Loaded astronaut data successfully")
    
    # Setup results and tokens dictionaries
    results = {}
    tokens = {}
    
    # Process each stimulus
    print(f"  [INFO] Processing {len(all_files)} stimulus files...")
    for i in range(len(all_files)):
        description, gif_frames = all_files[i]
        index = folders[i].rsplit('_', 1)[1]
        print(f"  [PROGRESS] Processing stimulus {index} ({i+1}/{len(all_files)})")
        
        # Create message with text and images
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": description},
                ],
            }
        ]
        
        # Add images to message
        print(f"    [INFO] Adding {len(gif_frames)} frames to message")
        for frame in gif_frames:
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{frame}"
                }
            })
        
        # Process index and add prompt
        if 'astronaut' in domain:
            order = order_info[index] if order_info else ""
            formatted_prompt = prompt.format(count=counts[index], order=order)
        else:
            formatted_prompt = prompt




        if "ablated" in method:
            model_path = os.path.join(project_dir, 'temp', domain, domain+"_"+str(index))

            with open(model_path+ "/domain.pddl", 'r') as file:
                domain_pddl = file.read()

            with open(model_path+ "/config.json", 'r') as file:
                config_str = file.read()

            with open(model_path+ "/frame_0.pddl", 'r') as file:
                frame_pddl = file.read()

            with open(model_path+ "/plan.txt", 'r') as file:
                plan = file.read()

            additional_prompt = """

            To help you with your task, we have synthesized a PDDL representation for this domain. \n

            PDDL Domain (Defines object types, predicates, and actions): \n

            {{domain}}

            Configuration (Defines priors over goals, beliefs, costs, and rewards, as well as agent's observability and action parameters): \n
            {{config}}

            Initial State (Defines the initial state of the environment): \n
            {{state}}

            Paths (Defines the actions taken by the agent): \n
            {{paths}}

            Now, given this information, please answer the question below. \n

            """.replace("{{domain}}", domain_pddl).replace("{{config}}", config_str).replace("{{state}}", frame_pddl).replace("{{paths}}", plan)

            
            formatted_prompt = formatted_prompt + additional_prompt
        
        messages[0]["content"].append({
            "type": "text",
            "text": formatted_prompt
        })
        
        # Select client based on model
        client = google_client if 'gemini' in model else openai_client
        
        # Call API with retry mechanism
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                print(f"    [API] Sending request to {model}...")
                start_time = time.time()
                
                if 'o3' in model:
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages
                    )
                else:
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=1.0
                    )
                
                elapsed_time = time.time() - start_time
                print(f"    [API] Response received in {elapsed_time:.2f} seconds")
                
                # Extract answer
                answer = response.choices[0].message.content
                final_answer = extract_answer_content(answer, method)
                output_tokens = response.usage.total_tokens
                
                # Store results
                results[domain+'_'+index] = final_answer
                tokens[domain+'_'+index] = output_tokens
                
                print(f"    [RESULT] {domain} {index} (Run {run_num}): {final_answer}")
                break  # Success, exit retry loop
                
            except Exception as e:
                retry_count += 1
                print(f"    [ERROR] Processing {domain} {index} (Run {run_num}, attempt {retry_count}/{max_retries}): {str(e)}")
                
                if retry_count < max_retries:
                    # Wait before retrying with exponential backoff
                    wait_time = 2 ** retry_count  # 2, 4, 8... seconds
                    print(f"    [RETRY] Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    # All retries failed
                    print(f"    [FAILED] Could not process {domain} {index} (Run {run_num}) after {max_retries} attempts")
                    results[domain+'_'+index] = f"ERROR: {str(e)}"
                    tokens[domain+'_'+index] = 0
        
        # Add a small delay between requests to avoid rate limiting
        print(f"    [DELAY] Waiting 0.5 seconds before next request...")
        time.sleep(0.5)
    
    # Save results with run number in filename
    result_file = f'{domain}_{model}_{method}_run_{run_num}.json'
    token_file = f'{domain}_{model}_{method}_tokens_run_{run_num}.json'
    
    print(f"  [SAVING] Writing results to {result_file}")
    with open(result_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"  [SAVING] Writing token counts to {token_file}")
    with open(token_file, 'w') as f:
        json.dump(tokens, f, indent=2)
    
    print(f"[COMPLETED] Domain: {domain}, Model: {model}, Method: {method}, Run: {run_num}")
    
    return {
        "domain": domain,
        "model": model,
        "method": method,
        "run_num": run_num,
        "result_file": result_file,
        "token_file": token_file,
        "stimulus_count": len(all_files),
        "success_count": len([r for r in results.values() if not str(r).startswith("ERROR")])
    }

def main():
    """Main function to run the script"""
    # All configurations to run
    configurations = [
        # Configuration 1
        # {
        #     'models': ['o3-2025-04-16'],
        #     'methods': ['reasoning'],
        #     'domains': ['mdkg', 'foodtruck']
        # },
        # # Configuration 2
        # {
        #     'models': ['gpt-4o-2024-11-20'],
        #     'methods': ['direct'],
        #     'domains': ['dkg_double', 'dkg_single', 'dkg_inverse', 'dkg_reuse', 'astronaut']
        # },
        # Configuration 3
        # {
        #     'models': ['gpt-4o-2024-11-20'],
        #     'methods': ['cot'],
        #     'domains': ['mdkg', 'foodtruck']
        # },
        # # Configuration 4
        {
            'models': ['gemini-2.0-flash-001'],
            'methods': ['ablated'],
            'domains': ['mdkg']
        },
        # # Configuration 5
        # {
        #     'models': ['gemini-2.0-flash-001'],
        #     'methods': ['direct'],
        #     'domains': ['dkg_double', 'dkg_single', 'dkg_inverse', 'dkg_reuse', 'astronaut']
        # }
    ]
    
    # Number of runs for each configuration
    num_runs = 5
    
    # Group tasks by model to avoid running the same model at the same time
    model_tasks = {}
    for config in configurations:
        for model in config['models']:
            if model not in model_tasks:
                model_tasks[model] = []
            
            for method in config['methods']:
                for domain in config['domains']:
                    for run_num in range(1, num_runs + 1):
                        model_tasks[model].append((domain, model, method, run_num))
    
    # Print task information
    print("\n===== TASK DISTRIBUTION =====")
    for model, tasks in model_tasks.items():
        print(f"Model {model}: {len(tasks)} tasks")
    
    total_tasks = sum(len(tasks) for tasks in model_tasks.values())
    print(f"Total number of tasks: {total_tasks}")
    print("=============================\n")
    
    # Maximum number of concurrent workers per model
    # Adjust this based on your system's capabilities and API rate limits
    concurrent_tasks_per_model = 3
    
    # Process model by model to avoid running the same model concurrently
    all_results = []
    for model, tasks in model_tasks.items():
        print(f"\n[MODEL GROUP] Starting tasks for model: {model}")
        print(f"[MODEL GROUP] {len(tasks)} tasks to run with {concurrent_tasks_per_model} concurrent workers")
        
        # Run tasks for this model in parallel
        model_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_tasks_per_model) as executor:
            # Submit all tasks for this model
            future_to_task = {executor.submit(run_baseline, task): task for task in tasks}
            
            # Process results as they complete
            completed = 0
            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                domain, model, method, run_num = task
                try:
                    result = future.result()
                    model_results.append(result)
                    completed += 1
                    print(f"[PROGRESS] Completed task: {domain} {model} {method} (Run {run_num}) - {completed}/{len(tasks)} tasks done")
                except Exception as e:
                    print(f"[ERROR] Task failed: {domain} {model} {method} (Run {run_num}): {str(e)}")
        
        all_results.extend(model_results)
        print(f"[MODEL GROUP] Completed all tasks for model: {model}")
    
    # Print summary
    print(f"\n========== ALL TASKS COMPLETED ==========")
    print(f"Successfully completed {len(all_results)} out of {total_tasks} tasks.")
    
    # Print success rates by model
    print("\n===== SUCCESS RATES BY MODEL =====")
    model_success = {}
    for result in all_results:
        model = result["model"]
        if model not in model_success:
            model_success[model] = {"total": 0, "success": 0}
        
        model_success[model]["total"] += result["stimulus_count"]
        model_success[model]["success"] += result["success_count"]
    
    for model, stats in model_success.items():
        success_rate = (stats["success"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        print(f"Model {model}: {stats['success']}/{stats['total']} stimuli ({success_rate:.2f}%)")
    
    print("=================================\n")
    print("Baseline runner execution complete!")

if __name__ == "__main__":
    main()