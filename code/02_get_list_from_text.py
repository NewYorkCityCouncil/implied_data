exec(open("code/00_settings.py").read())

#-----------------------------------------------------------------------------------
# bring in prompt info
#-----------------------------------------------------------------------------------

# read in prompts for first pass
prompt_persona_ops = open("data/input/prompt_persona_ops.txt").read()
prompt_instructions_one = open("data/input/prompt_instructions_one.txt").read()
prompt_format_one = open("data/input/prompt_format_one.txt").read()
prompt_examples = open("data/input/prompt_examples.txt").read()
prompt_final = open("data/input/prompt_final.txt").read()


#-----------------------------------------------------------------------------------
# query list of potential datasets from the CITY legal text
#-----------------------------------------------------------------------------------

# query list for each city document
for cur_doc in ['charter', 'adcode', 'rules']:
    start = time.time()
    response = pull_gemini_ops(dept, "nyc_code", cur_doc)
    print(f"{time_elapsed(start)} to finish query for: {cur_doc}.")



#-----------------------------------------------------------------------------------
# query list of potential datasets from the STATE legal text (only for Ed)
#-----------------------------------------------------------------------------------

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