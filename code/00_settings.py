import google.generativeai as genai
from google.generativeai.types import RequestOptions
from google.api_core import retry
from datetime import datetime
import time
import pandas as pd 
import re
import os
import sys
import pathlib
import glob
from pathlib import Path

exec(open("../tokens.py").read())
genai.configure(api_key=gemini_key)

#-----------------------------------------------------------------------------------
# prep + settings
#-----------------------------------------------------------------------------------

dept = "Finance"

dept_options = ["Health", "Parks", "Probation", "Fire", "Emergency", "moRemediation", "Finance", 
]


#-----------------------------------------------------------------------------------
# functions
# first from https://stackoverflow.com/questions/78846882/gemini-status-429-no-matter-what
#-----------------------------------------------------------------------------------

def submit_gemini_query(api_key, system_message, user_message, temp = 0, max_tokens = 60000):
    
    genai.configure(api_key=api_key)

    safety_settings = [ 
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}, 
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"}, 
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"}, 
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]

    generation_config = {
        "temperature": temp,
        "max_output_tokens": max_tokens
    }
    
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config=generation_config,
        system_instruction=system_message,
        safety_settings=safety_settings
    )

    response = model.generate_content(
            user_message,
            request_options=RequestOptions(retry=retry.Retry(initial=10, multiplier=2, maximum=60, timeout=300))
        )

    return response.text

def pull_gemini_state(base_path, file_list, chunk_size=35000):
    """
    base_path: The root directory where 'data/input' lives.
    file_list: List of paths relative to 'data/input/', 
               e.g., ['nyc_code/Education_adcode.txt', 'nys_code/Education_adcode.txt']
    """

    date_str = datetime.today().strftime('%Y-%m-%d')

    # check all the files exist
    full_paths = [os.path.join(base_path, "data/input", f) for f in file_list]
    missing = [p for p in full_paths if not os.path.exists(p)]
    
    if missing:
        print(f"ERROR: The following files were not found:\n{missing}")
        sys.exit(1)

    # read in text and combine in to one big blob
    full_text_blob = ""
    for path in full_paths:
        full_text_blob += f"\n\n{'='*30}\nFILE SOURCE: {path}\n{'='*30}\n"
        with open(path, 'r', encoding='utf-8') as f:
            f = f.read()
            print(f"Reading: {path}, has {len(f)} characters")
            full_text_blob += f

    # chunk in to blocks, regardless of which text file it came from
    chunks = [full_text_blob[i:i + chunk_size] for i in range(0, len(full_text_blob), chunk_size)]
    print(f"Total size: {len(full_text_blob)} chars. Split into {len(chunks)} queries.")

    # load in my prompts
    def read_p(name): return open(f"{base_path}/data/input/{name}.txt").read()
    sys_msg = read_p("prompt_persona_ops")
    instr = read_p("prompt_instructions_one")
    fmt = read_p("prompt_format_one")
    ex = read_p("prompt_examples")
    fin = read_p("prompt_final")

    # run each query chunk
    for idx, chunk in enumerate(chunks, 1):
        
        user_prompt = (
            f"<instructions>{instr}</instructions>\n"
            f"<context>Part {idx} of combined Gov docs:\n{chunk}</context>\n"
            f"<examples>{ex}</examples>\n"
            f"<output_format>{fmt}</output_format>\n"
            f"<final_instructions>{fin}</final_instructions>"
        )

        # query and SAVE 
        response_text = submit_gemini_query(gemini_key, sys_msg, user_prompt)
        out_name = f"{base_path}/data/output/lists/{dept}_state_{idx}_current.txt"
        with open(out_name, "w", encoding='utf-8') as out_file:
            out_file.write(response_text)
        out_name = f"{base_path}/data/output/lists/archive/{dept}_state_{idx}_{date_str}.txt"
        with open(out_name, "w", encoding='utf-8') as out_file:
            out_file.write(response_text)
        
        print(f"Done. Saved to {out_name}")

def pull_gemini_ops(dept, level_gov, doc_type):

    file_type = "data/input/" + level_gov + "/" + dept + "_" + doc_type + ".txt"

    f_exists = os.path.exists(file_type)
    if not f_exists: 
        print(f"{doc_type} file does not exist - saving dummy file for the {dept} {doc_type}")
        file_save = "data/output/lists/"+dept+"_"+doc_type+"_current.txt" 
        with open(file_save, "w") as file:
            file.write("NA")
        file_save = "data/output/lists/archive/"+dept+"_"+doc_type+"_"+datetime.today().strftime('%Y-%m-%d')+".txt" 
        with open(file_save, "w") as file:
            file.write("NA")
        return

    file = open(file_type).read()

    prompt = "<instructions>" + prompt_instructions_one + "</instructions>\n\n" +\
        "<context>" +\
            "Here is the ", doc_type + ": " + file +\
        "</context>\n\n" +\
        "<instructions>" + prompt_instructions_one + "</instructions>\n\n" +\
        "<examples>" + prompt_examples + "</examples>\n\n" +\
        "<output_format>" + prompt_format_one + "</output_format>\n\n" +\
        "<final_instructions>" + prompt_final + "</final_instructions>"

    response = submit_gemini_query(api_key = gemini_key, 
                                   system_message = prompt_persona_ops, 
                                   user_message = prompt)
    
    file_save = "data/output/lists/"+dept+"_"+doc_type+"_current.txt" 
    with open(file_save, "w") as file:
        file.write(response)
    file_save = "data/output/lists/archive/"+dept+"_"+doc_type+"_"+datetime.today().strftime('%Y-%m-%d')+".txt" 
    with open(file_save, "w") as file:
        file.write(response)

    return response

def pull_gemini_db(dept, state_data=False):

    date_str = datetime.today().strftime('%Y-%m-%d')

    charter = open("data/output/lists/"+dept+"_charter_current.txt" ).read()
    adcode = open("data/output/lists/"+dept+"_adcode_current.txt" ).read()
    rules = open("data/output/lists/"+dept+"_rules_current.txt" ).read()
    
    # read in all the state text as one big string
    if state_data:
        # figure out which files are relevant
        base_path = pathlib.Path("data/output/lists/")
        glob_pattern = f"Education_state_*_current.txt"
        number_regex = re.compile(f"Education_state_\d+_current\.txt")
        state_text = []

        # read them in 
        for file_path in base_path.glob(glob_pattern):
            Path(path_string).read_text(encoding="utf-8")
            if file_path.is_file() and number_regex.match(file_path.name):
                content = file_path.read_text(encoding='utf-8')
                state_text.append(content)
        state_text = "\n".join(state_text) # combine all of them

        # create the prompt
        prompt = "<instructions>" + prompt_instructions_two + " " +\
            prompt_schemas + "</instructions>\n\n" +\
            "<context>" +\
                "Here are the datasets identified from the Charter: " + charter +\
                "Here are the datasets identified from the Administrative Code: " + adcode +\
                "Here are the datasets identified from the Rules: " + rules +\
                "Here are the datasets identified from the State Code: " + state_text +\
                "Here are the titles and descriptions of all the datasets the agency has on Open Data: " +\
                dept_opendata.to_string() + " \n\n " + "</context>\n\n " +\
            "<instructions>" + prompt_instructions_two + "</instructions>\n\n " +\
            "<output_format>" + prompt_format_two + "</output_format>\n\n " +\
            "<final_instructions>" + prompt_final + "</final_instructions>"

    else:  
        # create the prompt
        prompt = "<instructions>" + prompt_instructions_two + " " +\
            prompt_schemas + "</instructions>\n\n" +\
            "<context>" +\
                "Here are the datasets identified from the Charter: " + charter +\
                "Here are the datasets identified from the Administrative Code: " + adcode +\
                "Here are the datasets identified from the Rules: " + rules +\
                "Here are the titles and descriptions of all the datasets the agency has on Open Data: " +\
                dept_opendata.to_string() + " \n\n " + "</context>\n\n " +\
            "<instructions>" + prompt_instructions_two + "</instructions>\n\n " +\
            "<output_format>" + prompt_format_two + "</output_format>\n\n " +\
            "<final_instructions>" + prompt_final + "</final_instructions>"
    
    # actually call gemini
    response = submit_gemini_query(api_key = gemini_key, 
                                   system_message = prompt_persona_db, 
                                   user_message = prompt)

    file_name = "data/output/compiled_archive/"+dept+"_combined_"+date_str+".txt" 
    with open(file_name, "w") as file:
        file.write(response)
    file_name = "data/output/"+dept+"_combined_current.txt" 
    with open(file_name, "w") as file:
        file.write(response)

# NEEDS TO BE FIXED FOR NEW DATA STRUCTURE, WILL BREAKKKKK 
def pull_gemini_statedb(dept, input_str = "state", output_str = "statecomb1", date_str = datetime.today().strftime('%Y-%m-%d'), chunk_size = 150000):

    # prep to read in data
    files_to_load = sorted(glob.glob(f'data/output/*Education_{input_str}*{date_str}*'))
    i = 1

    # run in chunks. load in data and remove from the list until nothing left
    while len(files_to_load) > 0:

        # prep
        n_read = 0
        tot_char = 0
        state_text = []

        # read in until 
        for file_path in files_to_load:
            content = Path(file_path).read_text(encoding="utf-8")
            if tot_char + len(content) <= chunk_size or n_read <= 1:
                tot_char = tot_char + len(content)
                n_read = n_read + 1
                state_text.append(content)
                files_to_load = [x for x in files_to_load if not x == file_path]
            else: 
                print(f"Documents read: {n_read}, Tot chars: {tot_char}, Chunk size: {chunk_size}")
                break
        state_text = "\n".join(state_text) # combine all of them

        # if that file already exists
        file_name = f"data/output/{dept}_{output_str}_{i}_{date_str}.txt" 
        if Path(file_name).is_file():
            print(f"Combination {i} has already been run. Skipping...")
        
        # create the prompt
        prompt = "<instructions>" + prompt_instructions_two + " " +\
                prompt_schemas + "</instructions>\n\n" +\
                "<context>" +\
                    "Here are the datasets identified from the State Code: " + state_text +\
                    "Here are the titles and descriptions of all the datasets the agency has on Open Data: " +\
                    dept_opendata.to_string() + " \n\n " + "</context>\n\n " +\
                "<instructions>" + prompt_instructions_two + "</instructions>\n\n " +\
                "<output_format>" + prompt_format_two + "</output_format>\n\n " +\
                "<final_instructions>" + prompt_final + "</final_instructions>"

        # actually call gemini
        response = submit_gemini_query(api_key = gemini_key, 
                                       system_message = prompt_persona_db, user_message = prompt)

        # save 
        file_name = f"data/output/{dept}_{output_str}_{i}_{date_str}.txt" 
        with open(file_name, "w") as file:
            file.write(response)

        # iterate
        i = i+1

def time_elapsed(start):
    elapsed = round(time.time() - start, 0)
    if elapsed > 60: 
        elapsed = round(elapsed/60, 1)
        return(f"{elapsed} (minutes)")
    elif elapsed > 3600: 
        elapsed = round(elapsed/3600, 2)
        return(f"{elapsed} (hours)")
    else: 
        return(f"{int(elapsed)} (seconds)")
