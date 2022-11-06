from contextlib import contextmanager
import sys, os
import easygui
from tableaudocumentapi import Workbook
import pandas as pd
import numpy as np

# suppress console output when workbook is opened
# source: http://thesmithfam.org/blog/2012/10/25/temporarily-suppress-console-output-in-python/
@contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:  
            yield
        finally:
            sys.stdout = old_stdout

# prompt user for twb file and extract file/directory names
print("Prompt for input Tableau workbook...")
inpFile = easygui.fileopenbox(filetypes=['*.twb'])
inpFileDirectory = os.path.dirname(inpFile)
inpFileName = os.path.splitext(os.path.basename(inpFile))[0]
outFile = inpFileDirectory + '\\' + inpFileName + '.csv'

# initial data frame with nested data source and field objects
print("Extract data sources and fields from workbook...")
with suppress_stdout():
    inpTwb = Workbook(inpFile)
df1 = pd.DataFrame(inpTwb.datasources, columns = ["data_source"])
df1["fields"] = df1.apply(lambda x: list(x.data_source.fields.values()), axis = 1)
dsAttr = ["name", "caption"]
for attr in dsAttr:
    df1["data_source_" + attr] = df1.apply(lambda x: getattr(x.data_source, attr), axis = 1)
df2 = df1.apply(lambda x: pd.Series(x['fields']), axis = 1)
dfList = [df1, df2]
df = pd.concat(dfList, axis = 1)

# unpivot fields per data source
colId = ["data_source", "fields", "data_source_name", "data_source_caption"]
colVal = [x for x in df.columns if x not in colId]
df = pd.melt(df, id_vars = colId, value_vars = colVal)
df = df[df["value"].notnull()]

# extract field attributes
fieldAttr = ["id", "caption", "datatype", "role", "type", "alias", "calculation", "description", "hidden"]
for attr in fieldAttr:
    df["field_" + attr] = df.apply(lambda x: getattr(x.value, attr) , axis = 1)

# additional transformations
df["field_hidden"] = np.where(df["field_hidden"] == "true", 1, 0)

# remove intermediate results
colRemove = ["data_source", "fields", "variable", "value"]
colKeep = [x for x in df.columns if x not in colRemove]
df = df[colKeep]

# store results and finish
print("Saving results in " + outFile + "...")
df.to_csv(path_or_buf = outFile, index = False)
input("Done! Press Enter to continue...")