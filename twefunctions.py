import sys, os
from contextlib import contextmanager
import numpy as np
import pandas as pd
import re
import json
import copy
import pydot
import logging
import random
import string

@contextmanager
def suppress_stdout():
    """
    Temporarily suppress console output. 
    Source: http://thesmithfam.org/blog/2012/10/25/temporarily-suppress-console-output-in-python/

    Args:
        message: Input data frame

    Returns:
        Suppress console output for following commands e.g. when 
        opening a workbook
    """
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:  
            yield
        finally:
            sys.stdout = old_stdout

def stepLog(message, *args, **kwargs):
    """
    Log a message that includes an incremental step counter in a main script

    Args:
        message: Input data frame

    Returns:
        Log message containing incremental step count
    """
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
    """
    Replace all external and internal field references by unique
    source/field IDs

    Args:
        df: Input data frame
        colFrom: Column name containing original values
        colTo: Column name containing mapped values

    Returns:
        Dictionary containing (from: to) mappings
    """
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
    if c == '': return i
    else:
        # right brackets are doubled in calculations
        return "[{0}]".format(c.replace("]", "]]"))

def fieldCalculationDependencies(l, x):
    """
    # List direct dependencies in a calculation x based on a list l

    Args:
        l: List of all possible values that can be matched
        x: Input calculation string

    Returns:
        List of values from the list l that were matched in the string x
    """
    return [s for s in l if s in x]

def isParamDuplicate(p, s, x):
    """
    Checks if a field is a parameter duplicate

    Args:
        p: List of parameter fields
        s: Source name
        x: Field name

    Returns:
        True if the field is a parameter duplicate (and should be removed), 
        False otherwise
    """
    return x in p and s != "[Parameters]"

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

def getBackwardDependencies(df, f, rs, rf, level = 0, c = None):
    """
    Recursively get all backward dependencies of a field

    Args:
        df: Input data frame
        f: Source field name
        rs: Originating root source name
        rf: Originating root field name
        level: Dependency level (0 = root, -1 = level 1 backwards, etc.)
        c: Originating child source field name

    Returns: 
        List of all backward dependencies of the input source field
    """
    x = df.loc[df.source_field_label == f]
    depList = list(x.field_calculation_dependencies)
    cat = list(x.field_category)[0]
    lst = []

    # add dependency
    if level > 0: lst += [{"source": rs, "root": rf, "parent": f, "child": c, \
        "level": "-{0}".format(level), "category": cat}]
    
    # add dependencies of dependency
    if len(depList) > 0:
        # remove reference by copying the list
        for y in depList[0].copy():
            lst += getBackwardDependencies(df, y, rs, rf, level + 1, f)
    return lst

def getForwardDependencies(df, f, w, rs, rf, level = 0, p = None, ):
    """
    Recursively get all forward dependencies of a field

    Args:
        df: Input data frame
        f: Source field name
        w: List of root source field worksheet dependencies
        rs: Originating root source name
        rf: Originating root field name
        level: Dependency level (0 = root, -1 = level 1 backwards, etc.)
        p: Originating parent source field name

    Returns: 
        List of all forward dependencies of the input source field
    """
    x = df.loc[df.label == f][["category", "worksheets"]]
    cat, ws = x.head(1).values.flatten()
    depList = list(df.loc[df.dependency == f]["label"])
    lst = []

    # get overlap of worksheets with root list
    nSheet = len([x for x in w if x in ws])

    if level > 0: 
        # add field dependencies
        lst += [{"source": rs, "root": rf, "parent": p, "child": f, \
            "level": "+{0}".format(level), "category": cat, 
            "sheets": nSheet}]
    else:
        # add root sheet dependencies (already is full list)
        for sh in ws:
            lst += [{"source": rs, "root": rf, "parent": "", "child": sh, \
                "level": "0", "category": "Sheet", 
            "sheets": 1}]
    
    # add dependencies of dependency
    if len(depList) > 0:
        # remove reference by copying the list
        for y in depList.copy(): 
            lst += getForwardDependencies(df, y, w, rs, rf, level + 1, f)

    return lst

def getUniqueDependencies(d, g, f):
    """
    Keep unique dependencies from a list of dependencies with their minimum
    dependency level

    Args:
        d: input list of dependency dictionaries
        g: grouping list
        f: aggregation field

    Returns:
        Dependency dictionaries that only contains unique dependencies with 
        their minimum dependency level
    """
    res = []
    if len(d) > 0:
        df = pd.DataFrame(d)
        df = df.groupby(g)[f].min().reset_index()
        # convert result back to dictionary
        res = df.to_dict("records")
    return res

def getMaxLevel(l):
    """
    Return maximum forward or backward dependency level of a given input list

    Args:
        l: input list of dependency dictionaries

    Returns: 
        Maximum dependency level for the given dictionary list
    """
    res = 0
    # note: values are formatted as text -> max('-1', '-4') = -4
    if len(l) > 0: res = max([d.get("level") for d in l])
    return res

def getFieldsFromCategory(l, c, f):
    """
    Return list of fields of a given category from a list of 
    dependency dictionaries

    Args:
        l: input list of dependency dictionaries
        c: category type
        f: flag indicating backward (True) or forward (False) dependencies

    Returns: 
        List of field names corresponding to the category
    """
    res = []
    if len(l) > 0:
        if f == True:
            res = [d.get("parent") for d in l if d.get("category") == c]
        else:
            res = [d.get("child") for d in l if d.get("category") == c]
    # only keep unique values
    res = list(set(res))
    return res

def addNode(sf, cat, shapes, colors):
    """
    Creates graph node objects for an input source field

    Args:
        sf: Input source field name
        cat: Input source field category
        shapes: List of shapes per source field category
        colors: List of colors per source field category

    Returns: 
        List of 2 nodes related for resp. the field and source field name
    """
    s = sf.split(".")[0]
    f = sf.split(".")[1]
    node1 = pydot.Node(name = f, shape = shapes[cat], \
        fillcolor = colors[cat], style = "filled")
    node2 = pydot.Node(name = sf, shape = shapes[cat], \
        fillcolor = colors[cat], style = "filled")
    return [node1, node2]

def replaceSourceReference(x, s):
    """
    Remove references to a given source for an input string or dict list

    Args:
        x: Input string or dict list
        s: Source name

    Returns: 
        String or dict list with all references to the input source name removed
    """
    # perform the replacement as a string
    res = str(x).replace(s + ".", "")
    # restore original structure if needed
    if x.__class__.__name__ == 'list':
        res = [json.loads(idx.replace("'", '"')) for idx in [res]][0]
    return res

def visualizeDependencies(df, sf, g, fin):
    """
    Creates output PNG file containing all dependencies for a given source field

    Args:
        df: Input data frame containing backward and forward dependencies
        sf: Input source field name
        g: Master graph containing all source field and field node objects
        fin: Path to the input Tableau workbook

    Returns: 
        PNG file in "<workbook path> Files\Graphs\<source field name>.png"
    """
    s = sf.split(".")[0]
    f = sf.split(".")[1]
    dictBackward = \
        list(df[df.source_field_label == sf]\
            ["field_backward_dependencies_temp"])[0]
    dictForward = \
        list(df[df.source_field_label == sf]\
            ["field_forward_dependencies_temp"])[0]
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

        # add (parent -> child) edges to graph
        for d in dictDependency:
            # don't visualize sheet dependencies
            if d["category"] != "Sheet":
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