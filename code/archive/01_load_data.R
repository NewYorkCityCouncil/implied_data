source("code/00_load_dependencies.R")
source("../tokens.R")
setAPI(gemini_key)

########################################################################################
# Code by: Anne Driscoll
# Last edited on: 12/02/2025
#
# Playing w Gemini to identify implied data in NYC Charter 
########################################################################################

dept = "Parks"

charter = read_file(paste0("data/input/", dept, "_charter.txt"))
adcode = read_file(paste0("data/input/", dept, "_adcode.txt"))
rules = read_file(paste0("data/input/", dept, "_rules.txt"))


prompt1 = read_file("data/input/prompt1.txt")
prompt2 = read_file("data/input/prompt2.txt")
prompt = paste(prompt1, "Here is the Charter:", charter, 
                        "Here is the Administrative Code:", adcode,
                        "Here are the Agency Rules:", rules, 
              prompt2)

gemini(prompt)
