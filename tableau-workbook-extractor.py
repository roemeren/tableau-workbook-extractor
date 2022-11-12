from twefunctions import *
from tableaudocumentapi import Workbook
import easygui
import warnings
from tqdm import tqdm

# ignore future warnings when reading field attributes (not applicable)
warnings.simplefilter(action = 'ignore', category = FutureWarning)

# logging config
logging.basicConfig(level = logging.DEBUG)
stepLog.counter = 1

# prompt user for twb file and extract file/directory names
stepLog("Prompt for input Tableau workbook...")
# inpFilePath = easygui.fileopenbox(default = "*.twb*")
inpFilePath = "C:\\Users\\remerencia\\Documents\\tableau-workbook-extractor\\notebooks\\Test Dashboard.twbx"
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
df["field_hidden"] = np.where(df["field_hidden"] == "true", 1, 0)
df[["data_source_caption", "field_caption", "field_calculation"]] = \
    df[["data_source_caption", "field_caption",
     "field_calculation"]].fillna('')

# data source and field IDs
df["data_source_name"] = "[" + df["data_source_name"]+ "]"
df["source_field_id"] = df["data_source_name"] + "." + df["field_id"]

# data source and field labels
df["field_label"] = df.apply(lambda x: \
    processCaptions(x.field_id, x.field_caption), axis = 1)
df["source_label"] = df.apply(lambda x: \
    processCaptions(x.data_source_name, x.data_source_caption), axis = 1)
df["source_field_label"] = df["source_label"] + "." + df["field_label"]

# filter out duplicate parameter rows
lstParam = list(df[df["source_label"] == "[Parameters]"]["field_label"])
df["field_is_param_duplicate"] = df.apply(lambda x: \
    isParamDuplicate(lstParam, x.source_label, x.field_label), axis = 1)
df = df[df["field_is_param_duplicate"] == 0]

# add a randomly generated ID field for each unique field
df["source_field_repl_id"] = getRandomReplacementID(df, "field_calculation")

# create source fields to ID mapping dictionary as well as the reverse
dictMapping1 = \
    sourceFieldMappingTable(df, "source_field_id", "source_field_repl_id")
dictMapping2 = \
    sourceFieldMappingTable(df, "source_field_id", "source_field_label")

# clean up field calculations
lstFieldID = list(df["field_id"].unique())
df["field_calculation_cleaned"] = \
    df.apply(lambda x: \
    fieldCalculationMapping(x.field_calculation, x.data_source_name, 
    dictMapping1, dictMapping2, lstFieldID), axis = 1)
    
# get list of field dependencies
lstSourceFields = list(df["source_field_label"].unique())
df["field_calculation_dependencies"] = \
    df["field_calculation_cleaned"].apply(lambda x: \
        fieldCalculationDependencies(lstSourceFields, x))

# calculate type of field
df["field_category"] = df.apply(lambda x: \
    fieldCategory(x.source_field_label, 
    x.field_calculation_dependencies, x.field_calculation_cleaned), axis = 1)

stepLog("Processing field dependencies...")
# get full list of backward dependencies
df["field_backward_dependencies"] = \
    df["source_field_label"].apply(lambda x: getBackwardDependencies(df, x))

# get full list of forward dependencies using exploded version of df (faster)
dfExplode = df[["source_field_label", "field_category", \
    "field_worksheets", "field_calculation_dependencies"]]
dfExplode = dfExplode.explode("field_calculation_dependencies")
dfExplode.columns = ["label", "category", "worksheets", "dependency"]
df["field_forward_dependencies"] = \
    df.apply(lambda x: \
        getForwardDependencies(dfExplode, x.source_field_label, 
        x.field_worksheets), axis = 1)

# only keep unique dependencies with their max level
df["field_backward_dependencies"] = \
    df.apply(lambda x: \
        getUniqueDependencies(x.field_backward_dependencies, 
        ["child", "parent", "category"], "level"), axis = 1)
df["field_forward_dependencies"] = \
    df.apply(lambda x: \
        getUniqueDependencies(x.field_forward_dependencies, 
        ["child", "parent", "category", "sheets"], 
        "level"), axis = 1)

# calculate max. forward and backward dependency levels
df["field_backward_dependencies_max_level"] = \
    df["field_backward_dependencies"].apply(lambda x: getMaxLevel(x))
df["field_forward_dependencies_max_level"] = \
    df["field_forward_dependencies"].apply(lambda x: getMaxLevel(x))

# flag fields with no dependencies and/or linked sheets
df["field_flagged"] = df.apply(lambda x: \
    np.where((len(x.field_backward_dependencies) == 0) & \
        (len(x.field_forward_dependencies) == 0) & \
            (len(x.field_worksheets) == 0), 1, 0), axis = 1)

# get some dependency aggregates
df["source_field_dependencies"] = \
    df.apply(lambda x: getFieldsFromCategory(x.field_backward_dependencies, 
    "Field", True), axis = 1)
df["lod_backward_dependencies"] = \
    df.apply(lambda x: getFieldsFromCategory(x.field_backward_dependencies, 
    "Calculated Field (LOD)", True), axis = 1)
df["n_source_field_dependencies"] = \
    df["source_field_dependencies"].apply(len)
df["n_lod_backward_dependencies"] = \
    df["lod_backward_dependencies"].apply(len)
df["n_worksheet_dependencies"] = \
    df["field_worksheets"].apply(len)

# final clean-up of backward and forward dependencies
lstClean = ["field_calculation_cleaned", "field_calculation_dependencies", 
    "field_backward_dependencies", "field_forward_dependencies", 
    "source_field_dependencies"]
for col in lstClean:
    df[col] = df.apply(lambda x: replaceSourceReference(x[col], x.source_label),
     axis = 1)

stepLog("Creating field dependency graphs...")
# Create master node graph
colors = {"Parameter": "#cbc3e3",
    "Field": "green", "Calculated Field (LOD)": "red", 
    "Calculated Field": "orange"}
shapes = {"Parameter": "parallelogram", 
    "Field": "box", "Calculated Field (LOD)": "oval", 
    "Calculated Field": "oval"}
nodes = df.apply(lambda x: \
    addNode(x.source_field_label, x.field_category, shapes, colors), axis = 1)
lstNodes = []
for node in nodes: lstNodes += node
gMaster = pydot.Dot()
for node in lstNodes: gMaster.add_node(node)

# calculate temporary version with parameter source references removed
df["field_backward_dependencies_temp"] = \
    df.apply(lambda x: \
        replaceSourceReference(x.field_backward_dependencies, "[Parameters]"), 
        axis = 1)
df["field_forward_dependencies_temp"] = \
    df.apply(lambda x: \
        replaceSourceReference(x.field_forward_dependencies, "[Parameters]"), 
        axis = 1)

# create dependency graphs per field
for index, row in tqdm(df.iterrows(), total = df.shape[0]):
    visualizeDependencies(df, row.source_field_label, gMaster, inpFilePath)

# output 1: field info
colKeep = ["source_label", "field_label", "source_field_label",
    "field_datatype", "field_role", 
    "field_role", "field_type", "field_aliases", "field_description", 
    "field_hidden", "field_category", "field_calculation_cleaned", 
    "field_calculation_dependencies", "field_backward_dependencies_max_level", 
    "field_forward_dependencies_max_level", "source_field_dependencies",
    "n_source_field_dependencies", "lod_backward_dependencies", 
    "n_lod_backward_dependencies", "field_worksheets", 
    "n_worksheet_dependencies", "field_flagged"]
dfWrite = df[colKeep]

# output 2: dependency info
df["field_backward_dependencies"] = \
    df.apply(lambda x: appendFieldsToDicts(x.field_backward_dependencies, 
    ["source_label", "field_label", "source_field_label"], 
    [x.source_label, x.field_label, x.source_field_label]), axis = 1)
df["field_forward_dependencies"] = \
    df.apply(lambda x: appendFieldsToDicts(x.field_forward_dependencies, 
    ["source_label", "field_label", "source_field_label"], 
    [x.source_label, x.field_label, x.source_field_label]), axis = 1)
lstBw = [item for x in list(df.field_backward_dependencies) for item in x]
lstFw = [item for x in list(df.field_forward_dependencies) for item in x]
dfWrite2 = pd.DataFrame(lstBw + lstFw)
dfWrite2 = dfWrite2[["source_label", "field_label", "source_field_label", 
"parent", "child", "level", "category", "sheets"]]
dfWrite2.columns = ["source_label", "field_label", "source_field_label", 
"dependency_from", "dependency_to", "dependency_level", "dependency_category", 
"dependency_worksheets_overlap"]

# store results and finish
stepLog("Saving table result in " + outFilePath + "...")
if not os.path.isdir(outFileDirectory):
    os.makedirs(outFileDirectory)

with pd.ExcelWriter(outFilePath) as writer:
    dfWrite.to_excel(writer, sheet_name = "fields", index = False)
    dfWrite2.to_excel(writer, sheet_name = "dependencies", index = False)
input("Done! Press Enter to continue...")