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

#-----------------------------------------------------------------------------------
# prep + settings
#-----------------------------------------------------------------------------------

dept = "Education"
exec(open("../tokens.py").read())
#gemini_key = os.getenv("gemini_key2")
genai.configure(api_key=gemini_key)


#-----------------------------------------------------------------------------------
# bring in open dataset info
#-----------------------------------------------------------------------------------

# load in data
datasets = pd.read_csv("https://data.cityofnewyork.us/resource/5tqd-u88y.csv?$limit=99999999999")
datasets = datasets[(~datasets.uid.isna()) & (~datasets.datasetinformation_agency.isna())]

# identify data from correct agency
agency_names = datasets.datasetinformation_agency.unique()
matches = [bool(re.search(dept, s)) for s in list(agency_names)]
full_dept = agency_names[matches][0]
print(full_dept)

# keep only relevant data
dept_opendata = datasets[datasets.datasetinformation_agency == full_dept][['name',  'type']] # took out 'description',

# clean data to condense datasets across years etc
temp = dept_opendata
temp.name = temp.name.replace("[0-9\-]+", " ", regex=True)  
temp.name = temp.name.replace("\s+", " ", regex=True).str.strip()


#-----------------------------------------------------------------------------------
# bring in mmr info
#-----------------------------------------------------------------------------------

# load in data
mmr = pd.read_csv("https://data.cityofnewyork.us/resource/wcrd-6u4m.csv?$limit=99999999999")

# identify data from correct agency
agency_names = mmr.agency.unique()
matches = [bool(re.search(dept, s)) for s in list(agency_names)]
full_dept = agency_names[matches][0]
print(full_dept)

# keep only relevant data
dept_mmr = mmr[(mmr.agency == full_dept) & 
               (mmr.is_the_source_of_this == 'The underlying data is owned by another agency or entity.')] #[['name', 'description', 'type']]


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
        out_name = f"{base_path}/data/output/{dept}_state_{idx}_{date_str}.txt"
        with open(out_name, "w", encoding='utf-8') as out_file:
            out_file.write(response_text)
        
        print(f"Done. Saved to {out_name}")

def pull_gemini_ops(dept, level_gov, doc_type):

    file_type = "data/input/" + level_gov + "/" + dept + "_" + doc_type + ".txt"
    file_save = "data/output/"+dept+"_"+doc_type+"_"+datetime.today().strftime('%Y-%m-%d')+".txt" 

    f_exists = os.path.exists(file_type)
    if not f_exists: 
        print(f"{doc_type} file does not exist - saving dummy file for the {dept} {doc_type}")
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

    with open(file_save, "w") as file:
        file.write(response)

    return response

def pull_gemini_db(dept, date_str = datetime.today().strftime('%Y-%m-%d'), state_data=False):

    charter = open("data/output/"+dept+"_charter_"+d+".txt" ).read()
    adcode = open("data/output/"+dept+"_adcode_"+d+".txt" ).read()
    rules = open("data/output/"+dept+"_rules_"+d+".txt" ).read()
    
    # read in all the state text as one big string
    if state_data:
        # figure out which files are relevant
        base_path = pathlib.Path("data/output/")
        glob_pattern = f"Education_state_*_{d}.txt"
        number_regex = re.compile(f"Education_state_\d+_{d}\.txt")
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

    file_name = "data/output/"+dept+"_combined_"+datetime.today().strftime('%Y-%m-%d')+".txt" 
    with open(file_name, "w") as file:
        file.write(response)

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


#-----------------------------------------------------------------------------------
# bring in prompt info
#-----------------------------------------------------------------------------------

# read in prompts for first pass
prompt_persona_ops = open("data/input/prompt_persona_ops.txt").read()
prompt_instructions_one = open("data/input/prompt_instructions_one.txt").read()
prompt_format_one = open("data/input/prompt_format_one.txt").read()
prompt_examples = open("data/input/prompt_examples.txt").read()
prompt_final = open("data/input/prompt_final.txt").read()

# read in prompts for second pass
prompt_persona_db = open("data/input/prompt_persona_db.txt").read()
prompt_instructions_two = open("data/input/prompt_instructions_two.txt").read()
prompt_format_two = open("data/input/prompt_format_two.txt").read()
prompt_schemas = open("data/input/prompt_schemas.txt").read()


#-----------------------------------------------------------------------------------
# query gemini
#-----------------------------------------------------------------------------------

# query data from each city document
for cur_doc in ['charter', 'adcode', 'rules']:
    start = time.time()
    response = pull_gemini_ops(dept, "nyc_code", cur_doc)
    print(f"{time_elapsed(start)} to finish query for: {cur_doc}.")

if dept == "Education": 
    files_to_load = ['nys_code/Education_title1_incomplete.txt', # general provisions
                    #'nys_code/Education_title2_incomplete.txt', # school district org
                    'nys_code/Education_title4_incomplete.txt'] # teachers + pupils
                    #'nys_code/Education_title5.txt', # financial administration 
                    #'nys_code/Education_title6.txt', # special schools + instruction
                    #'nys_code/Education_title7.txt'  # State and City Colleges and Institutions

    # query data for state documents
    pull_gemini_state(
        base_path=".",
        file_list=files_to_load,
        chunk_size=71000
    )


#-----------------------------------------------------------------------------------
# combine state level calls
#-----------------------------------------------------------------------------------

if dept == "Education": 
    response = pull_gemini_statedb(dept, date_str = "2026-05-07")


if dept == "Education": 
    response = pull_gemini_statedb(dept, date_str = "2026-05-07", chunk_size = 300000,
                                   input_str = "statecomb1", output_str = "statecomb2")


#-----------------------------------------------------------------------------------
# final combinations
#-----------------------------------------------------------------------------------

start = time.time()
response = pull_gemini_db(dept, state_data = dept == "Education")
print(f"{time_elapsed(start)} to finish combining the datasets from all documents.")
