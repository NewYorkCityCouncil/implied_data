exec(open("code/00_settings.py").read())

#-----------------------------------------------------------------------------------
# bring in prompt info
#-----------------------------------------------------------------------------------

# read in prompts
prompt_persona_ops = open("data/input/prompt_persona_ops.txt").read()
prompt_instructions_three = open("data/input/prompt_instructions_three.txt").read()



#-----------------------------------------------------------------------------------
# prep for query
#-----------------------------------------------------------------------------------

start = time.time()
file_path = "data/output/" + dept + "_combined_current.txt"
f_exists = os.path.exists(file_path)
if not f_exists: 
    print("DOESN'T EXIST")
else:  
    file = open(file_path).read()
    prompt = prompt_instructions_three +\
        "Here is the file I would like you to reformat: " +\
        "<input>" + file + "</input>\n\n"

    response = submit_gemini_query(api_key = gemini_key, 
                                   system_message = prompt_persona_ops, 
                                   user_message = prompt)
    
    date_str = datetime.today().strftime('%Y-%m-%d')
    file_name = "data/output/compiled_archive/"+dept+"_combined_analyst_"+date_str+".md" 

    with open(file_name, "w") as file:
        file.write(response)
    file_name = "data/output/analyst/"+dept+"_combined_analyst_current.md" 
    with open(file_name, "w") as file:
        file.write(response)
print(f"{time_elapsed(start)} to finish query for: {dept}.")