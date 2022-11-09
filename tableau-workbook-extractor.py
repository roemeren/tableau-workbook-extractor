from twefunctions import *
from tableaudocumentapi import Workbook
import pandas as pd
import easygui
import warnings
from tqdm import tqdm

# ignore future warnings when reading field attributes (not applicable)
warnings.simplefilter(action='ignore', category=FutureWarning)

# logging config
logging.basicConfig(level = logging.DEBUG)
step_log.counter = 1

# prompt user for twb file and extract file/directory names
step_log("Prompt for input Tableau workbook...")
inpFilePath = easygui.fileopenbox(default = "*.twb*")
inpFileName = os.path.splitext(os.path.basename(inpFilePath))[0]
outFilePath = inpFilePath + ' Files\\Fields\\' + inpFileName + '.csv'
outFileDirectory = os.path.dirname(outFilePath)

# initial data frame with nested data source and field objects
step_log("Extract data sources and fields from workbook...")
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

# additional transformations
df["field_hidden"] = np.where(df["field_hidden"] == "true", 1, 0)
df[["data_source_caption", "field_caption", "field_calculation"]] = \
    df[["data_source_caption", "field_caption",
     "field_calculation"]].fillna('')

# create data sources & fields mapping dictionary
dictMapping = fieldCalculationMappingTable(df, "data_source_name", \
    "data_source_caption", "field_id", "field_caption")

# create cleaned copy of field calculations
# replace na by empty string otherwise errors due to NaN
df["field_calculation_cleaned"] = df.apply(lambda x: \
    fieldCalculationClean(x.field_calculation, x.data_source_name), axis = 1)

# apply field mappings to calculations
df["field_calculation_cleaned"] = df["field_calculation_cleaned"].apply(lambda x: \
    fieldCalculationMapping(dictMapping, x))

# merge field and data source name fields
df["field_label"] = np.where(df["field_caption"] == '', \
    df["field_id"], '[' + df["field_caption"] + ']')
df["source_label"] = "[" + np.where(df["data_source_caption"] == '', 
                                   df["data_source_name"], \
                                    df["data_source_caption"]) + "]"

# filter out duplicate parameter rows
lstParam = list(df[df["source_label"] == "[Parameters]"]["field_label"])
df["field_is_param_duplicate"] = df.apply(lambda x: \
    isParamDuplicate(lstParam, x.source_label, x.field_label), axis = 1)
df = df[df["field_is_param_duplicate"] == 0]

# create list of unique combinations of data sources + field names
df["source_field_label"] = df["source_label"] + "." + df["field_label"]
lstFields = list(dict.fromkeys(list(df["source_field_label"])))

# get list of field dependencies
df["field_calculation_dependencies"] = \
    df["field_calculation_cleaned"].apply(lambda x: \
        fieldCalculationDependencies(lstFields, x))

# calculate type of field
df["field_category"] = df.apply(lambda x: \
    fieldCategory(x.source_field_label, 
    x.field_calculation_dependencies), axis = 1)

# expand dependencies to full lists of backward and forward dependencies
df["field_backward_dependencies"] = \
    df["source_field_label"].apply(lambda x: getBackwardDependencies(df, x))
df["field_forward_dependencies"] = \
    df["source_field_label"].apply(lambda x: getForwardDependencies(df, x))

# flag fields with no dependencies and/or linked sheets
df["field_flagged"] = df.apply(lambda x: \
    np.where((len(x.field_backward_dependencies) == 0) & \
        (len(x.field_forward_dependencies) == 0) & \
            (len(x.field_worksheets) == 0), 1, 0), axis = 1)

step_log("Creating field dependency graphs...")
# Create master node graph
colors = {"Parameter": "#cbc3e3", "Field": "green", "Calculated Field": "orange"}
shapes = {"Parameter": "parallelogram", "Field": "box", "Calculated Field": "oval"}
nodes = df.apply(lambda x: \
    addNode(x.source_field_label, x.field_category, shapes, colors), axis = 1)
lstNodes = []
for node in nodes: lstNodes += node
gMaster = pydot.Dot()
for node in lstNodes: gMaster.add_node(node)

# final clean-up of backward and forward dependencies
df["field_backward_dependencies"] = df.apply(lambda x: \
    replaceSourceReference(x.field_backward_dependencies, 
    x.source_label), axis = 1)
df["field_forward_dependencies"] = df.apply(lambda x: \
    replaceSourceReference(x.field_forward_dependencies, 
    x.source_label), axis = 1)

# calculate temporary version with parameter source references removed
df["field_backward_dependencies_temp"] = \
    df["field_backward_dependencies"].apply(lambda x: replaceParamReference(x))
df["field_forward_dependencies_temp"] = \
    df["field_forward_dependencies"].apply(lambda x: replaceParamReference(x))

# create dependency graphs per field
for index, row in tqdm(df.iterrows(), total = df.shape[0]):
    visualizeDependencies(df, row.source_field_label, gMaster, inpFilePath)

# remove intermediate results
colRemove = ["data_source", "fields", "variable", "value", \
    "field_backward_dependencies_temp", "field_forward_dependencies_temp", 
    "field_is_param_duplicate"]
colKeep = [x for x in df.columns if x not in colRemove]
df = df[colKeep]

# store results and finish
step_log("Saving table result in " + outFilePath + "...")
if not os.path.isdir(outFileDirectory):
    os.makedirs(outFileDirectory)
df.to_csv(path_or_buf = outFilePath, index = False, sep = ',')
input("Done! Press Enter to continue...")