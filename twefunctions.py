import sys, os
from contextlib import contextmanager
import numpy as np
import re
import json
import copy
import pydot
import logging
import random
import string

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

def stepLog(message, *args, **kwargs):
  logging.info(" STEP %d: " % stepLog.counter + message, *args, **kwargs)
  stepLog.counter += 1

def getRandomReplacementID(df, c):
    """
    Generate a random ID of 10 lower case letters combined with the data frame 
    index that will serve as a base for a generated field ID field

    Args:
        df: Input data frame
        c: Column name that is used to check if none of the generated ID are 
        accidentally matched in it
    
    Returns:
        Random ID consisting of the combination if 10 lower case letters 
        and the row index. This ID can be used to be replace references
        to fields in calculations because it is ensured that none of the IDs
        are accidentally matched
    """
    uniqueVals = list(df[c].unique())
    flagSucceed = False
    while not flagSucceed:
        baseID = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
        flagSucceed = not any(baseID in s for s in uniqueVals)
    res = "[" + baseID + df.index.astype(str) + "]"
    return res

def sourceFieldMappingTable(df, colFrom, colTo):
    dfRes = df.copy()
    dfRes = dfRes[[colFrom, colTo]]
    dfRes.columns = ["from", "to"]
    arrRes = np.array(dfRes)
    # dict conversion automatically deduplicates mappings
    dictRes = dict(arrRes[1:]) 
    return dictRes

def fieldCalculationMapping(c, s, d1, d2, l):
    """
    Replace all external and internal field references by unique
    source/field IDs

    Args:
        c: Source field calculation string
        s: Source field source name
        d1: Dictionary of source field -> replacement ID mappings
        d1: Dictionary of source field -> source label mappings
        l: List of unique field names

    Returns:
        Calculation string without comments and with all field ID references
        replaced by field label references
    """
    # remove comments
    res = re.sub(r"\/{2}.*\n", '', c)
    # external: [source ID].[field ID] -> [replacement ID]
    for key in d1: res = res.replace(key, d1.get(key))
    # internal: [field ID] -> [source ID].[field ID]
    for fld in l: res = res.replace(fld, "{0}.{1}".format(s, fld))
    # external: [replacement ID] -> [source ID].[field ID]
    for key in d1: res = res.replace(d1.get(key), key)
    # [source ID].[field ID] -> [source label].[field label]
    for key in d2: res = res.replace(key, d2.get(key))
    return res

def processCaptions(i, c):
    """
    Process captions to the format in which they are used in calculations

    Args:
        i: Source or field ID value
        x: Source or field caption value

    Returns:
        Processed caption enclosed in square brackets + any additional
        right square brackets doubled
    """
    if c == '':
        return i
    else:
        # right brackets are doubled in calculations
        return "[{0}]".format(c.replace("]", "]]"))

# list direct dependencies in a calculation x based on a list l
def fieldCalculationDependencies(l, x):
    return [s for s in l if s in x]

# check if a field is a parameter duplicate
def isParamDuplicate(p, s, x):
    return x in p and s != "[Parameters]"

# get field category (parameter, field or calculated field)
def fieldCategory(s, d, c):
    """
    Returns the category of a source field 

    Args:
        s: Source field label
        d: List of source field dependencies
        c: Source field cleaned calculation

    Returns: 
        Category of the source field: parameter, field, calculated field (LOD)
    """
    if s.startswith("[Parameters]."): return "Parameter"
    if len(d) == 0: return "Field"
    if re.search(r"{[^'\"].*?[^'\"]}", c): return "Calculated Field (LOD)"
    else: return "Calculated Field"

# recursively get all backward dependencies of a field
def getBackwardDependencies(df, f, level = 0, c = None):
    x = df.loc[df.source_field_label == f]
    depList = list(x.field_calculation_dependencies)
    cat = list(x.field_category)[0]
    lst = []
    
    # add dependency
    if level > 0: lst += [{"child": c, "parent": f, \
        "level": "-{0}".format(level), "parentCategory": cat}]
    
    # add dependencies of dependency
    if len(depList) > 0:
        # remove reference by copying the list
        for y in depList[0].copy():
            lst += getBackwardDependencies(df, y, level + 1, f)
    return lst

# recursively get all forward dependencies of a field (SLOW)
def getForwardDependencies(df, f, level = 0, p = None):
    x = df.loc[df.source_field_label == f]
    depList = df.apply(lambda z: \
        f in z.field_calculation_dependencies, axis = 1)
    depList  = list(df.loc[depList]["source_field_label"])
    cat = list(x["field_category"])[0]
    ws = list(x["field_worksheets"])[0]
    lst = []
    
    # add dependency (including its sheets)
    if level > 0: lst += [{"child": f, "parent": p, \
        "level": "+{0}".format(level), "childCategory": cat, 
        "childSheets": ws}]
    
    # add dependencies of dependency
    if len(depList) > 0:
        # remove reference by copying the list
        for y in depList.copy(): 
            lst += getForwardDependencies(df, y, level + 1, f)

    return lst

def addNode(sf, cat, shapes, colors):
    s = sf.split(".")[0]
    f = sf.split(".")[1]
    node1 = pydot.Node(name = f, shape = shapes[cat], \
        fillcolor = colors[cat], style = "filled")
    node2 = pydot.Node(name = sf, shape = shapes[cat], \
        fillcolor = colors[cat], style = "filled")
    return [node1, node2]

# d: dictionary of dependencies (formatted as string)
def replaceSourceReference(d, s):
    return str(d).replace(s + ".", "")
    
# Replace all source references from the same source
# s: source name
# d: dictionary of dependencies (formatted as string)
def replaceParamReference(x):
    return str(x).replace("[Parameters].", "")

def visualizeDependencies(df, sf, g, fin):
    s = sf.split(".")[0]
    f = sf.split(".")[1]
    dictBackward = \
        list(df[df.source_field_label == sf]\
            ["field_backward_dependencies_temp"])
    dictBackward = [json.loads(idx.replace("'", '"')) \
        for idx in dictBackward][0]
    dictForward = \
        list(df[df.source_field_label == sf]\
            ["field_forward_dependencies_temp"])
    dictForward = [json.loads(idx.replace("'", '"')) for idx in dictForward][0]
    dictDependency = copy.deepcopy(dictBackward + dictForward)
    # only generate graph if there are dependencies
    if len(dictDependency) > 0:

        # create a copy of the master node list in order to not modify it
        MGCopy = copy.deepcopy(g)

        # set properties for main node
        G = pydot.Dot(graph_type = "digraph")
        subject = '"' + f + '"'
        G.add_node(MGCopy.get_node(subject)[0])
        G.get_node(subject)[0].set("fillcolor", "lightblue")

        # retain unique (parent, child) relationships
        keysKeep = {"key", "parent", "child"}
        for d in dictDependency:
            # add surrogate key that defines a unique edge
            keyValue = "{0}->{1}".format(d.get("parent"), d.get("child"))
            d.update(key = keyValue)
            keysDict = set(dictDependency[0].keys())
            keysRemove = keysDict - keysKeep
            for k in keysRemove: del d[k]
        dictDependency = list({v["key"]: v for v in dictDependency}.values())

        # add (parent -> child) edges to graph
        for d in dictDependency:
            parent = '"' + d["parent"] + '"'
            child = '"' + d["child"] + '"'
            nodeParent = MGCopy.get_node(parent)[0]
            nodeChild = MGCopy.get_node(child)[0]
            G.add_node(nodeParent)
            G.add_node(nodeChild)
            edge = pydot.Edge(nodeParent, nodeChild)
            G.add_edge(edge)

        # create output graphs folder if it doesn't exist yet
        specialChar = "[^A-Za-z0-9]+"
        sout = re.sub(specialChar, '', s)
        fout = re.sub(specialChar, '', f)
        dout = "{0} Files\\Graphs\\{1}\\".format(fin, sout)
        if not os.path.isdir(dout):
            os.makedirs(dout)
        
        # write output file
        outFile = "{0}{1}-{2}.png".format(dout, sout, fout)
        G.write_png(outFile)
        return outFile