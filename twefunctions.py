import sys, os
from contextlib import contextmanager
import numpy as np
import re

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

# dictionary of [source ID].[field ID] -> [source caption].[label caption]
def fieldCalculationMappingTable(df, colFromSource, \
    colToSource, colFromField, colToField):
    dfRes = df.copy()
    # original [source].[field]
    dfRes["from"] = "[" + dfRes[colFromSource] + "]." + dfRes[colFromField]
    # mapped [source].[field]
    dfRes["to"] = ("[" + np.where(dfRes[colToSource] == '', \
        dfRes[colFromSource], dfRes[colToSource]) 
                   + "]." + np.where(dfRes[colToField] == '', \
                    dfRes[colFromField], "[" + dfRes[colToField] + "]"))
    dfRes = dfRes[["from", "to"]]
    arrRes = np.array(dfRes)
    # dict conversion automatically deduplicates mappings
    dictRes = dict(arrRes[1:]) 
    return dictRes

# clean up an expression x
def fieldCalculationClean(x, s):
    # remove all comments (important for dependencies)
    # pattern: starts with 2 forward slashes and ends with new line \n
    res = re.sub(r"\/{2}.*\n", '', x)
    # replace internal field reference (not . + [field]) by [source].[field]
    res = re.sub(r"([^.])(\[.*\])", r"\1" + "[" + s + r"].\2", res)
    return res

# apply a set of replacements to a string
# note: the mapping (field_id -> field_caption) appears to be unique
# (renaming in Tableau is reverted automatically when reopening the workbook)
def fieldCalculationMapping(d, x):
    res = x
    for key in d: res = res.replace(key, d.get(key))
    return res

# list direct dependencies in a calculation x based on a list l
def fieldCalculationDependencies(l, x):
    return [s for s in l if s in x]

# check if a field is a parameter duplicate
def isParamDuplicate(p, s, x):
    return x in p and s != "[Parameters]"

# get field category (parameter, field or calculated field)
def fieldCategory(s, d):
    if s.startswith("[Parameters]."): return "Parameter"
    if len(d) == 0: return "Field"
    else: return "Calculated Field"

# recursively get all backward dependencies of a field
def getBackwardDependencies(df, f, level = 0, p = None):
    x = df.loc[df.source_field_label == f]
    depList = list(x.field_calculation_dependencies)
    cat = list(x.field_category)[0]
    lst = []
    
    # add dependency
    if level > 0: lst += [{"child": f, "parent": p, \
        "level": "-{0}".format(level), "category": cat}]
    
    # add dependencies of dependency
    if len(depList) > 0:
        # remove reference by copying the list
        for y in depList[0].copy():
            lst += getBackwardDependencies(df, y, level + 1, f)
    return lst

# recursively get all forward dependencies of a field
def getForwardDependencies(df, f, level = 0, c = None):
    x = df.loc[df.source_field_label == f]
    depList = df.apply(lambda z: \
        f in z.field_calculation_dependencies, axis = 1)
    depList  = list(df.loc[depList]["source_field_label"])
    cat = list(x["field_category"])[0]
    lst = []
    
    # add dependency
    if level > 0: lst += [{"child": c, "parent": f, \
        "level": "+{0}".format(level), "category": cat}]
    
    # add dependencies of dependency
    if len(depList) > 0:
        # remove reference by copying the list
        for y in depList.copy(): 
            lst += getForwardDependencies(df, y, level + 1, f)
    return lst