from twefunctions import *
from tableaudocumentapi import Workbook
import easygui
import warnings
from tqdm import tqdm

# script parameters
fTest = False # run without prompt or not?
fDepFields = True # create field dependency graphs?
fDepSheets = True # create sheet dependency graphs?
fSVG = True # create SVG versions of dependency graphs next to PNG?

# ignore future warnings when reading field attributes (not applicable)
warnings.simplefilter(action = 'ignore', category = FutureWarning)

# logging config
logging.basicConfig(level = logging.DEBUG)
stepLog.counter = 1

# prompt user for twb file and extract file/directory names
stepLog("Prompt for input Tableau workbook...")
if fTest:
    inpFilePath = ("C:\\Users\\remerencia\\Documents\\" + 
        "tableau-workbook-extractor\\notebooks\\Test Dashboard.twbx")
else: 
    inpFilePath = easygui.fileopenbox(default = "*.twb*")
inpFileName = os.path.splitext(os.path.basename(inpFilePath))[0]
outFilePath = inpFilePath + ' Files\\Fields\\' + inpFileName + '.xlsx'
outFileDirectory = os.path.dirname(outFilePath)

# initial data frame with nested data source and field objects
stepLog("Extract data sources and fields from workbook...")
with suppress_stdout():
    inpTwb = Workbook(inpFilePath)
df1 = pd.DataFrame(inpTwb.datasources, columns = ["data_source"])
df1["fields"] = df1.apply(lambda x: \
    list(x.data_source.fields.values()), axis = 1)
dsAttr = ["name", "caption"]
for attr in dsAttr:
    df1["data_source_" + attr] = df1.apply(lambda x: \
         getattr(x.data_source, attr), axis = 1)
df2 = df1.apply(lambda x: pd.Series(x['fields']), axis = 1)
dfList = [df1, df2]
df = pd.concat(dfList, axis = 1)

# unpivot fields per data source
colId = ["data_source", "fields", "data_source_name", "data_source_caption"]
colVal = [x for x in df.columns if x not in colId]
df = pd.melt(df, id_vars = colId, value_vars = colVal)
df = df[df["value"].notnull()]

# extract field attributes
fieldAttr = ["id", "caption", "datatype", "role", "type", "alias", "aliases", \
    "calculation", "description", "hidden", "worksheets"]
for attr in fieldAttr:
    df["field_" + attr] = df.apply(lambda x: getattr(x.value, attr), axis = 1)

stepLog("Processing fields...")
# additional transformations
df["field_hidden"] = df["field_hidden"].apply(lambda x: \
    np.where(x == "true", 1, 0))
df[["data_source_caption", "field_caption", "field_calculation"]] = \
    df[["data_source_caption", "field_caption",
     "field_calculation"]].fillna('')

# add brackets to data source and field IDs if needed
df["data_source_name"] = "[" + df["data_source_name"]+ "]"
df["field_id"] = df["field_id"].apply(lambda x: 
    np.where(re.search(r"\[.*\]", x), x, "[{0}]".format(x)))
df["source_field_id"] = df["data_source_name"] + "." + df["field_id"]

# data source and field labels
df["field_label"] = df.apply(lambda x: \
    processCaptions(x.field_id, x.field_caption), axis = 1)
df["source_label"] = df.apply(lambda x: \
    processCaptions(x.data_source_name, x.data_source_caption), axis = 1)
df["source_field_label"] = df["source_label"] + "." + df["field_label"]

# remove duplicate rows based on source field ID
df, nDupl = removeDuplicatesByRowLength(df, "source_field_id")
print("\t{0} duplicate fields removed".format(nDupl))

# filter out duplicate parameter rows and [:Measure Names] field
lstParam = list(df[df["data_source_name"] == "[Parameters]"]["field_id"])
df["field_is_param_duplicate"] = df.apply(lambda x: \
    isParamDuplicate(lstParam, x.data_source_name, x.field_id), axis = 1)
nDupl2 = df.shape[0]
df = df[(df["field_is_param_duplicate"] == 0) & 
    (df["field_id"] != "[:Measure Names]")]
nDupl2 -= df.shape[0]
print("\t{0} duplicate parameters and/or measure names removed".format(nDupl2))

# add a randomly generated ID field for each unique field
baseID = getRandomReplacementBaseID(df, "field_calculation")
df["source_field_repl_id"] = "[" + baseID + df.index.astype(str) + "]"

# create source fields to ID mapping dictionary as well as the reverse
dictFieldIDToID = \
    fieldMappingTable(df, "source_field_id", "source_field_repl_id")

# clean up field calculations and aliases
lstFieldID = list(df["field_id"].unique())
df["field_calculation_cleaned"] = \
    df.apply(lambda x: \
    fieldCalculationMapping(x.field_calculation, x.data_source_name, 
    dictFieldIDToID, lstFieldID), axis = 1)

# map sheet names to sheet IDs
dictSheetToID = sheetMappingTable(df, "field_worksheets")
df["field_worksheets_id"] = df["field_worksheets"].apply(lambda x: 
    sheetMapping(x, dictSheetToID))

# get list of field dependencies
lstSourceFields = list(df["source_field_repl_id"].unique())
df["field_calculation_dependencies"] = \
    df["field_calculation_cleaned"].apply(lambda x: \
        fieldCalculationDependencies(lstSourceFields, x))

# calculate type of field
df["field_category"] = df.apply(lambda x: \
    fieldCategory(x.source_field_label, x.field_calculation_cleaned), axis = 1)

stepLog("Processing field dependencies...")
# get full list of backward dependencies
df["field_backward_dependencies"] = \
    df["source_field_repl_id"].apply(lambda x: backwardDependencies(df, x))

# get full list of forward dependencies using exploded version of df (faster)
dfExplode = df[["source_field_repl_id", "field_category", \
    "field_worksheets_id", "field_calculation_dependencies"]]
dfExplode = dfExplode.explode("field_calculation_dependencies")
dfExplode.columns = ["id", "category", "worksheets", "dependency"]
df["field_forward_dependencies"] = \
    df.apply(lambda x: \
        forwardDependencies(dfExplode, x.source_field_repl_id, 
        x.field_worksheets_id), axis = 1)

# only keep unique dependencies with their max level
df["field_backward_dependencies"] = \
    df.apply(lambda x: \
        uniqueDependencies(x.field_backward_dependencies, 
        ["child", "parent", "category"], "level"), axis = 1)
df["field_forward_dependencies"] = \
    df.apply(lambda x: \
        uniqueDependencies(x.field_forward_dependencies, 
        ["child", "parent", "category", "sheets"], 
        "level"), axis = 1)

# get some dependency aggregates
df["field_backward_dependencies_max_level"] = \
    df["field_backward_dependencies"].apply(maxDependencyLevel)
df["field_forward_dependencies_max_level"] = \
    df["field_forward_dependencies"].apply(maxDependencyLevel)
df["source_field_dependencies"] = \
    df.apply(lambda x: fieldsFromCategory(x.field_backward_dependencies, 
    "Field", True), axis = 1)
df["lod_backward_dependencies"] = \
    df.apply(lambda x: fieldsFromCategory(x.field_backward_dependencies, 
    "Calculated Field (LOD)", True), axis = 1)
df["n_backward_dependencies"] = \
    df["field_backward_dependencies"].apply(len)
df["n_worksheet_dependencies"] = \
    df["field_worksheets"].apply(len)
df["n_forward_dependencies"] = \
    df["field_forward_dependencies"].apply(len)
df["n_forward_dependencies"] = df["n_forward_dependencies"] - \
    df["n_worksheet_dependencies"] 
df["n_backward_dependencies_field"] = \
    df["source_field_dependencies"].apply(len)
df["n_backward_dependencies_lod"] = \
    df["lod_backward_dependencies"].apply(len)

# flag unused fields (field and its forward dependencies not used in sheets)
df["flag_unused"] = df.apply(lambda x: \
    np.where(x.n_worksheet_dependencies == 0, 1, 0), axis = 1)

if fDepFields or fDepSheets:
    # Create master node graph
    colors = {"Parameter": "#cbc3e3",
        "Field": "green", "Calculated Field (LOD)": "red", 
        "Calculated Field": "orange"}
    shapes = {"Parameter": "parallelogram", 
        "Field": "box", "Calculated Field (LOD)": "oval", 
        "Calculated Field": "oval"}
    nodes = df.apply(lambda x: \
        addFieldNode(x.source_field_repl_id, x.source_field_label, 
            x.field_category, shapes, colors, x.field_calculation_cleaned), 
            axis = 1)
    lstNodes = []
    for node in nodes: lstNodes += node
    gMaster = pydot.Dot()
    for node in lstNodes: gMaster.add_node(node)

    # add sheet nodes
    for x in dictSheetToID:
        node = pydot.Node(name = dictSheetToID[x], label = x, shape = "box",
            fillcolor = "grey", style = "filled", tooltip = " ")
        gMaster.add_node(node)

if fDepFields:
    inpPath = "{0} Files\\Graphs\\".format(inpFilePath)

    stepLog("Creating field dependency graphs per source in {0}..."
        .format(inpPath))
    # create dependency graphs per field
    for index, row in tqdm(df.iterrows(), total = df.shape[0]):
        # only generate graph if there are dependencies
        nDependency = row.n_backward_dependencies + row.n_forward_dependencies
        if nDependency > 0: 
            visualizeFieldDependencies(df, row.source_field_repl_id, 
                row.source_field_label, gMaster, inpPath, fSVG)

# create new data frame with flattened dependencies
df["field_backward_dependencies"] = \
    df.apply(lambda x: appendFieldsToDicts(x.field_backward_dependencies, 
    ["source_field_repl_id"], [x.source_field_repl_id]), axis = 1)
df["field_forward_dependencies"] = \
    df.apply(lambda x: appendFieldsToDicts(x.field_forward_dependencies, 
    ["source_field_repl_id"], [x.source_field_repl_id]), axis = 1)
lstBw = [item for x in list(df.field_backward_dependencies) for item in x]
lstFw = [item for x in list(df.field_forward_dependencies) for item in x]
df2 = pd.DataFrame(lstBw + lstFw)
# join with other field attributes
dfSel = df[["source_field_repl_id", "source_label", "field_label", 
    "source_field_label", "field_category"]]
df2 = pd.merge(left = df2, right = dfSel, on = "source_field_repl_id")
# reorder and rename columns
df2 = df2[["source_label", "field_label", "source_field_label", 
    "source_field_repl_id", "field_category", "parent", "child", 
    "level", "category", "sheets"]]
df2.columns = ["source_label", "field_label", "source_field_label",  
                "source_field_repl_id", "field_category", "dependency_from",
                    "dependency_to", "dependency_level", "dependency_category",
                    "dependency_worksheets_overlap"]

if fDepSheets:
    # create output folder if it doesn't exist yet
    inpPath = "{0} Files\\Graphs\\Sheets\\".format(inpFilePath)
    if not os.path.isdir(inpPath): os.makedirs(inpPath)

    stepLog("Creating sheet dependency graphs in {0}...".format(inpPath))
    # get list of unique sheets
    lstSheets = list(df2[df2.dependency_category == "Sheet"]
                ["dependency_to"].unique())

    # create dependency graphs per sheet
    for sh in tqdm(lstSheets, total = len(lstSheets)):
        visualizeSheetDependencies(df2, sh, gMaster, inpPath, fSVG)

stepLog("Saving table results in " + outFilePath + "...")
# final clean-up of backward and forward dependencies
dictFieldToID = fieldMappingTable(df, "source_field_label", 
    "source_field_repl_id")
dictLabelToID = {**dictFieldToID, **dictSheetToID}

# output 1: field info
lstClean = ["field_calculation_cleaned", "field_calculation_dependencies", 
   "field_backward_dependencies", "field_forward_dependencies", 
   "source_field_dependencies"]
for col in lstClean:
   df[col] = df.apply(lambda x: fieldIDMapping(x[col], x.source_label, 
    dictLabelToID), axis = 1)

colKeep = ["source_label", "field_label", "source_field_label",
    "field_datatype", "field_role", 
    "field_role", "field_type", "field_aliases", "field_description", 
    "field_hidden", "field_worksheets", "field_category", 
    "field_calculation_cleaned", "source_field_dependencies", 
    "field_backward_dependencies_max_level", 
    "field_forward_dependencies_max_level", 
    "n_backward_dependencies", "n_forward_dependencies",
    "n_backward_dependencies_field", "n_backward_dependencies_lod",
    "n_worksheet_dependencies", "flag_unused"]
df = df[colKeep]

# output 2: dependencies info
lstClean = ["dependency_from", "dependency_to"]
for col in lstClean:
   df2[col] = df2.apply(lambda x: fieldIDMapping(x[col], x.source_label, 
    dictLabelToID), axis = 1)
df2 = df2.drop(["source_field_repl_id"], axis = 1)

# store results and finish
if not os.path.isdir(outFileDirectory):
    os.makedirs(outFileDirectory)

with pd.ExcelWriter(outFilePath) as writer:
    df.to_excel(writer, sheet_name = "fields", index = False)
    df2.to_excel(writer, sheet_name = "dependencies", index = False)
input("Done! Press Enter to continue...")