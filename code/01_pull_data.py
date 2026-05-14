exec(open("code/00_settings.py").read())


#-----------------------------------------------------------------------------------
# bring in open dataset info
#-----------------------------------------------------------------------------------

# load in data
datasets = pd.read_csv("https://data.cityofnewyork.us/resource/5tqd-u88y.csv?$limit=99999999999")
datasets = datasets[(~datasets.uid.isna()) & (~datasets.datasetinformation_agency.isna())]

if dept == "SocialServices":  
    # need to include HRA + DHS under DSS
    dept_opendata = datasets[(datasets.datasetinformation_agency == 'Human Resources Administration (HRA)') | 
                             (datasets.datasetinformation_agency == 'Department of Homeless Services (DHS)')][['name',  'type']] 
else: 
    # identify data from correct agency
    agency_names = datasets.datasetinformation_agency.unique()
    matches = [bool(re.search(dept, s)) for s in list(agency_names)]
    full_dept = agency_names[matches][0]
    print(full_dept)

    # keep only relevant data
    dept_opendata = datasets[datasets.datasetinformation_agency == full_dept][['name',  'type']]
        

# clean data to condense datasets across years etc
temp = dept_opendata
temp.name = temp.name.replace("[0-9\-]+", " ", regex=True)  
temp.name = temp.name.replace("\s+", " ", regex=True).str.strip()



#-----------------------------------------------------------------------------------
# bring in mmr info
#-----------------------------------------------------------------------------------

# load in data
mmr = pd.read_csv("https://data.cityofnewyork.us/resource/wcrd-6u4m.csv?$limit=99999999999")

if dept == "SocialServices":  
    # need to include HRA + DHS under DSS
    dept_mmr = mmr[((mmr.agency == 'Department of Social Services (DSS) - Department of Homeless Services (DHS)') | 
                    (mmr.agency == 'Department of Social Services (DSS) - Human Resources Administration (HRA)')) & 
                   (mmr.is_the_source_of_this != 'The underlying data is owned by another agency or entity.')] 

else: 
    # identify data from correct agency
    agency_names = mmr.agency.unique()
    matches = [bool(re.search(dept, s)) for s in list(agency_names)]
    full_dept = agency_names[matches][0]
    print(full_dept)

    # keep only relevant data
    dept_mmr = mmr[(mmr.agency == full_dept) & 
                (mmr.is_the_source_of_this == 'The underlying data is owned by another agency or entity.')] #[['name', 'description', 'type']]

dept_mmr = dept_mmr[['mmr_indicator_name', 'mmr_indicator_description', 'mmr_indicator_source']]
