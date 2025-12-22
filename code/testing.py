import google.generativeai as genai
from google.generativeai.types import RequestOptions
from google.api_core import retry

#-----------------------------------------------------------------------------------
# prep + settings
#-----------------------------------------------------------------------------------

dept = "Fire"
exec(open("../tokens.py").read())


#-----------------------------------------------------------------------------------
# define query that deals with calling when it gets a 429
# from https://stackoverflow.com/questions/78846882/gemini-status-429-no-matter-what
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
                                                    timeout=1800
                                                )
                                            )
                                        )

    return response.text


#-----------------------------------------------------------------------------------
# bring in prompt info
#-----------------------------------------------------------------------------------

# read in texts
f = open('path/to/file.txt')
content = f.read()
f.close()

charter = open("data/input/" + dept + "_charter.txt").read()
adcode = open("data/input/" + dept + "_adcode.txt").read()
rules = open("data/input/" + dept + "_rules.txt").read()

# read in prompts
prompt_persona = open("data/input/prompt_persona.txt").read()
prompt_instructions = open("data/input/prompt_instructions.txt").read()
prompt_format = open("data/input/prompt_format.txt").read()
prompt_examples = open("data/input/prompt_examples.txt").read()
prompt_final = open("data/input/prompt_final.txt").read()

# combine to final prompt
prompt = "<role>" + prompt_persona + "</role>\n\n" +\
    "<instructions>" + prompt_instructions + "</instructions>\n\n" +\
    "<context>" + "Here is the Charter: " + charter +\
    "Here is the Administrative Code: " + adcode +\
    "Here are the Agency Rules: " + rules +  "</context>\n\n" +\
    "<instructions>" + prompt_instructions + "</instructions>\n\n" +\
    "<examples>" + prompt_examples + "</examples>\n\n" +\
    "<output_format>" + prompt_format + "</output_format>\n\n" +\
     "<final_instructions>" + prompt_final + "</final_instructions>"

with open("data/output/full_prompt.txt", "a") as file:
    file.write(prompt)

#-----------------------------------------------------------------------------------
# query gemini
#-----------------------------------------------------------------------------------

response = submit_gemini_query(api_key = gemini_key, system_message = prompt_persona, 
                                user_message = prompt)
