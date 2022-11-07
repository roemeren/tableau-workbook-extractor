from twefunctions import *
import easygui
from tableaudocumentapi import Workbook
import pandas as pd

# prompt user for twb file and extract file/directory names
print("Prompt for input Tableau workbook...")
inpFile = easygui.fileopenbox(filetypes = ['*.twb'])
inpFileDirectory = os.path.dirname(inpFile)
inpFileName = os.path.splitext(os.path.basename(inpFile))[0]
outFile = inpFileDirectory + '\\' + inpFileName + '.csv'

# initial data frame with nested data source and field objects
print("Extract data sources and fields from workbook...")
with suppress_stdout():
    inpTwb = Workbook(inpFile)
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
fieldAttr = ["id", "caption", "datatype", "role", "type", "alias", \
    "calculation", "description", "hidden"]
for attr in fieldAttr:
    df["field_" + attr] = df.apply(lambda x: getattr(x.value, attr) , axis = 1)

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
df["field_calculation_corr"] = df.apply(lambda x: \
    fieldCalculationClean(x.field_calculation, x.data_source_name), axis = 1)

# apply field mappings to calculations
df["field_calculation_corr"] = df["field_calculation_corr"].apply(lambda x: \
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
    df["field_calculation_corr"].apply(lambda x: \
        fieldCalculationDependencies(lstFields, x))

# calculate type of field
df["field_category"] = df.apply(lambda x: \
    fieldCategory(x.field_label, x.field_calculation_dependencies), axis = 1)

# expand dependencies to full lists of backward and forward dependencies
df["field_backward_dependencies"] = \
    df["source_field_label"].apply(lambda x: getBackwardDependencies(df, x))
df["field_forward_dependencies"] = \
    df["source_field_label"].apply(lambda x: getForwardDependencies(df, x))

# remove intermediate results
colRemove = ["data_source", "fields", "variable", "value"]
colKeep = [x for x in df.columns if x not in colRemove]
df = df[colKeep]

# store results and finish
print("Saving results in " + outFile + "...")
df.to_csv(path_or_buf = outFile, index = False)
input("Done! Press Enter to continue...")