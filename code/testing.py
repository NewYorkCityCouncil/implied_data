import google.generativeai as genai
from google.generativeai.types import RequestOptions
from google.api_core import retry
from datetime import datetime
import time

#-----------------------------------------------------------------------------------
# prep + settings
#-----------------------------------------------------------------------------------

dept = "Parks"
exec(open("../tokens.py").read())


#-----------------------------------------------------------------------------------
# functions
# first from https://stackoverflow.com/questions/78846882/gemini-status-429-no-matter-what
#-----------------------------------------------------------------------------------

def submit_gemini_query(api_key, system_message, user_message):
    
    genai.configure(api_key=api_key)

    safety_settings = [ 
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}, 
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"}, 
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"}, 
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]

    generation_config = {
        "temperature": 0,
        "max_output_tokens": 60000
    }
    
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config=generation_config,
        system_instruction=system_message,
        safety_settings=safety_settings
    )

    chat_session = model.start_chat(history=[])

    response = chat_session.send_message(user_message,
                                            request_options=RequestOptions(
                                                retry=retry.Retry(
                                                    initial=10, 
                                                    multiplier=2, 
                                                    maximum=60, 
                                                    timeout=300
                                                )
                                            )
                                        )

    return response.text

def pull_gemini_ops(dept, type):

    file = open("data/input/nyc_code/" + dept + "_" + type + ".txt").read()
    prompt = "<instructions>" + prompt_instructions_one + "</instructions>\n\n" +\
        "<context>" +\
            "Here is the ", type + ": " + file +\
        "</context>\n\n" +\
        "<instructions>" + prompt_instructions_one + "</instructions>\n\n" +\
        "<examples>" + prompt_examples + "</examples>\n\n" +\
        "<output_format>" + prompt_formatshort + "</output_format>\n\n" +\
        "<final_instructions>" + prompt_final + "</final_instructions>"

    response = submit_gemini_query(api_key = gemini_key, 
                                   system_message = prompt_persona_ops, 
                                   user_message = prompt)

    file_name = "data/output/"+dept+"_"+type+"_"+datetime.today().strftime('%Y-%m-%d')+".txt" 
    with open(file_name, "w") as file:
        file.write(response)

    return response

def pull_gemini_db(dept):

    d = datetime.today().strftime('%Y-%m-%d')
    charter = open("data/output/"+dept+"_charter_"+d+".txt" ).read()
    adcode = open("data/output/"+dept+"_adcode_"+d+".txt" ).read()
    rules = open("data/output/"+dept+"_rules_"+d+".txt" ).read()

    prompt = "<instructions>" + prompt_instructions_two + " " +\
        prompt_schemas + "</instructions>\n\n" +\
        "<context>" +\
            "Here are the datasets identified from the Charter: " + charter +\
            "Here are the datasets identified from the Administrative Code: " + adcode +\
            "Here are the datasets identified from the Rules: " + rules +\
        "</context>\n\n" +\
        "<instructions>" + prompt_instructions_two + "</instructions>\n\n" +\
        "<output_format>" + prompt_format + "</output_format>\n\n" +\
        "<final_instructions>" + prompt_final + "</final_instructions>"

    response = submit_gemini_query(api_key = gemini_key, 
                                   system_message = prompt_persona_db, 
                                   user_message = prompt)

    file_name = "data/output/"+dept+"_combined_"+datetime.today().strftime('%Y-%m-%d')+".txt" 
    with open(file_name, "w") as file:
        file.write(response)

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
prompt_formatshort = open("data/input/prompt_formatshort.txt").read()
prompt_examples = open("data/input/prompt_examples.txt").read()
prompt_final = open("data/input/prompt_final.txt").read()

# read in prompts for second pass
prompt_persona_db = open("data/input/prompt_persona_db.txt").read()
prompt_instructions_two = open("data/input/prompt_instructions_one.txt").read()
prompt_format = open("data/input/prompt_format.txt").read()
prompt_schemas = open("data/input/prompt_schemas.txt").read()


#-----------------------------------------------------------------------------------
# query gemini
#-----------------------------------------------------------------------------------

# query data from each document
for cur_doc in ['charter', 'adcode', 'rules']:
    start = time.time()
    response = pull_gemini_ops(dept, cur_doc)
    print(f"{time_elapsed(start)} to finish query for: {cur_doc}.")

# combine the datasets from each document
start = time.time()
response = pull_gemini_db(dept)
print(f"{time_elapsed(start)} to finish combining the datasets from all documents.")
