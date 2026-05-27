exec(open("code/00_settings.py").read())
exec(open("code/01_pull_data.py").read())

#-----------------------------------------------------------------------------------
# bring in prompt info
#-----------------------------------------------------------------------------------

# read in prompts for second pass
prompt_persona_db = open("data/input/prompt_persona_db.txt").read()
prompt_instructions_two = open("data/input/prompt_instructions_two.txt").read()
prompt_format_two = open("data/input/prompt_format_two.txt").read()
prompt_schemas = open("data/input/prompt_schemas.txt").read()


#-----------------------------------------------------------------------------------
# combining - state has two level, all others one
#-----------------------------------------------------------------------------------

if dept == "Education": 
    start = time.time()
    response = pull_gemini_statedb(dept) #, date_str = "2026-05-07")
    print(f"{time_elapsed(start)} to finish first pass combination.")
    response = pull_gemini_statedb(dept, chunk_size = 500000, #, date_str = "2026-05-07"
                                   input_str = "statecomb1", output_str = "statecomb2")
    print(f"{time_elapsed(start)} to finish combining of datasets from all documents.")
else: 
    start = time.time()
    response = pull_gemini_db(dept, state_data = (dept == "Education"))
    print(f"{time_elapsed(start)} to finish combining the datasets from all documents.")
