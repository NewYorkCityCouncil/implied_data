source("00_load_dependencies.R")
source("../../tokens.R")
setAPI(gemini_key)

################################################################################
# Settings
################################################################################

dept = "Fire"


################################################################################
# Prep
################################################################################

# read in texts
charter = read_file(paste0("../data/input/", dept, "_charter.txt"))
adcode = read_file(paste0("../data/input/", dept, "_adcode.txt"))
rules = read_file(paste0("../data/input/", dept, "_rules.txt"))

# read in prompts
prompt_persona = read_file("../data/input/prompt_persona.txt")
prompt_instructions = read_file("../data/input/prompt_instructions.txt")
prompt_format = read_file("../data/input/prompt_format.txt")
prompt_examples = read_file("../data/input/prompt_examples.txt")
prompt_final = read_file("../data/input/prompt_final.txt")

# combine to final prompt
prompt = paste("<role>", prompt_persona, "</role>\n\n",
               
               "<instructions>", prompt_instructions, "</instructions>\n\n",
               
               "<context>", "Here is the Charter: ", charter, 
               "Here is the Administrative Code: ", adcode,
               "Here are the Agency Rules: ", rules,  "</context>\n\n",
               
               "<instructions>", prompt_instructions, "</instructions>\n\n",
               "<examples>", prompt_examples, "</examples>\n\n",
               "<output_format>", prompt_format, "</output_format>\n\n",
               "<final_instructions>", prompt_final, "</final_instructions>")
write_file(prompt, "../data/output/full_prompt.txt")


################################################################################
# Run
################################################################################

response = gemini(prompt, model = "2.5-flash", temperature = 0,
                  maxOutputTokens = 60000, timeout = 1800)

if (length(response) > 1) {
  lengths = sapply(response, nchar)
  id = which(lengths == max(lengths))
  response = response[[id]]
  
}


################################################################################
# Save
################################################################################

file_name = paste0("../data/output/", dept, "_", Sys.Date(), ".txt")
write_file(response, file_name)
write_file(response, "../data/output/temp.txt")

