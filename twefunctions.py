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

# constants
MAXPATHSIZE = 260

@contextmanager
def suppress_stdout():
    """
    Temporarily suppress console output. 
    Source: http://thesmithfam.org/blog/2012/10/25/temporarily-suppress-console-output-in-python/

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

def show_exception_and_exit(exc_type, exc_value, tb):
    """
    Keeps the application alive when an unhandled exception occurs
    Source: https://stackoverflow.com/questions/779675/stop-python-from-closing-on-error
    """
    import traceback
    traceback.print_exception(exc_type, exc_value, tb)
    input("Error encountered. Press Enter to exit...")
    sys.exit(-1)

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

def getRandomReplacementBaseID(df, c, suffix = ""):
    """
    Generate a random ID of 10 lower case letters combined with the data frame 
    index that will serve as a base for a generated field ID field

    Args:
        df: Input data frame
        c: Column name that is used to check if none of the generated ID are 
        accidentally matched in it
        suffix: optional fixed suffix to add to random ID
    
    Returns:
        Random ID consisting of the combination if 10 lower case letters 
        and the row index. This ID can be used to be replace references
        to fields in calculations because it is ensured that none of the IDs
        are accidentally matched
    """
    uniqueVals = list(df[c].unique())
    random.seed(10)
    flagSucceed = False
    while not flagSucceed:
        res = ''.join(random.choice(string.ascii_lowercase) 
            for x in range(10)) + suffix
        flagSucceed = not any(res in s for s in uniqueVals)
    return res

def fieldMappingTable(df, colFrom, colTo):
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
    dictRes = dict(arrRes[:]) 
    return dictRes

def sheetMappingTable(df, colFrom):
    """
    Create dictionary of (sheet name) -> (sheet ID) mappings

    Args:
        df: Input data frame
        colFrom: Column name containing sheet lists

    Returns:
        Dictionary containing (from: to) mappings
    """
    # unique list of sheet names
    lstFrom = list(set([x for l in list(df[colFrom]) for x in l]))
    # sequential numbering of unique sheets
    baseID = getRandomReplacementBaseID(df, "field_calculation", "sh")
    lstTo = ["[" + baseID + str(s) + "]" for s in list(range(len(lstFrom)))]
    # dictionary of from -> to
    res = dict(zip(lstFrom, lstTo))
    return res

def fieldCalculationMapping(c, s, d, l):
    """
    Replace all external and internal field references by unique
    source/field IDs

    Args:
        c: Source field calculation string
        s: Source field source name
        d: Dictionary of source field -> replacement ID mappings
        l: List of unique field names

    Returns:
        Calculation string without comments and with all field ID references
        replaced by unique replacement ID references

    Notes:
        The function assumes that external fields are 
        referenced as [source ID].[field ID] and internal 
        fields [field ID]. If this is not the case the function may return
        incorrect results.
    """
    # remove comments (anything that starts with // until end of line)
    res = re.sub(r"\/{2}.*\n", "", c)
    res = re.sub(r"\/{2}.*", "", res)
    # remove empty lines
    res = re.sub(r"^\n", "", res)
    # external: [source ID].[field ID] -> [replacement ID]
    for key in d: res = res.replace(key, d.get(key))
    # internal: [field ID] -> [source ID].[field ID]
    for fld in l: res = res.replace(fld, "{0}.{1}".format(s, fld))
    # external: [replacement ID] -> [source ID].[field ID]
    for key in d: res = res.replace(d.get(key), key)
    # [source ID].[field ID] -> [replacement ID]
    for key in d: res = res.replace(key, d.get(key))
    return res

def sheetMapping(s, d):
    """
    Replace all sheet names by a sequential sheet ID

    Args:
        s: List of sheet names
        d: Dictionary of sheet name -> sheet ID mappings

    Returns:
        List of mapped sheet names to sheet IDs
    """
    return list(map(d.get, s.copy()))

def processCaptions(i, c):
    """
    Process captions to the format in which they are used in calculations and 
    with some invalid characters removed for JSON parsing

    Args:
        i: Source or field ID value
        x: Source or field caption value

    Returns:
        lbl: Original field name enclosed with brackets
        res: Processed caption enclosed in square brackets + any additional
        right square brackets doubled. Single and double quotes are 
        replaced by HTML codes resp. &apos and &quot while a backslash (\)
        is replaced by 2 backslashes (\\)
    """
    if c == '': 
        lbl = i
        res = i
    else:
        lbl = "[{0}]".format(c)
        # right brackets are doubled in calculations
        res = "[{0}]".format(c.replace("]", "]]"))
    # replace invalid characters for later json.loads use
    res = res.replace("'", "&apos")
    res = res.replace('"', "&quot")
    res = res.replace("\\", '\\\\')
    return lbl, res

def fieldCalculationDependencies(l, x):
    """
    List direct dependencies in a calculation x based on a list l

    Args:
        l: List of all possible values that can be matched
        x: Input calculation string

    Returns:
        List of values from the list l that were matched in the string x
    """
    return [s for s in l if s in x]

def removeDuplicatesByRowLength(df, x):
    """
    Remove duplicates from an input frame by retaining per grouping only 
    the row with the largest concatenated string length

    Args:
        df: input data frame
        x: grouping column name

    Returns:
        Copy of input data frame with per unique grouping value the row 
        with the largest concatenated string length + no. duplicates removed
    """
    # initialize result by copying original data frame
    res = df.copy()
    # calculate concatenated string length
    res["row_len"] = res.fillna("").astype(str).values.sum(axis = 1)
    res["row_len"] = res["row_len"].apply(len)
    # calculate unique ranking and only keep first rank
    res["rank"] = res.groupby(x)["row_len"].rank(method = "first", 
        ascending = False)
    res = res[res["rank"] == 1][df.columns].reset_index(drop = True)
    nDupl = df.shape[0] - res.shape[0]
    return res, nDupl

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

def fieldCategory(s, c):
    """
    Returns the category of a source field 

    Args:
        s: Source field label
        c: Source field cleaned calculation

    Returns: 
        Category of the source field: parameter, field, calculated field (LOD)
    """
    if s.startswith("[Parameters]."): return "Parameter"
    # LOD matching: anything between curly brackets (including line breaks)
    if re.search(r"{([^}]*)}", c, re.DOTALL): return "Calculated Field (LOD)"
    if c != "": return "Calculated Field"
    else: return "Field"

def backwardDependencies(df, f, level = 0, c = None):
    """
    Recursively get all backward dependencies of a field

    Args:
        df: Input data frame
        f: Source field replacement ID
        level: Dependency level (0 = root, -1 = level 1 backwards, etc.)
        c: Originating child source field replacement ID

    Returns: 
        List of all backward dependencies of the input source field
    """
    x = df.loc[df.source_field_repl_id == f]
    depList = list(x.field_calculation_dependencies)
    cat = list(x.field_category)[0]
    lst = []

    # add dependency
    if level > 0: lst += [{"parent": f, "child": c, \
        "level": "-{0}".format(level), "category": cat}]
    
    # add dependencies of dependency
    if len(depList) > 0:
        # remove reference by copying the list
        for y in depList[0].copy():
            lst += backwardDependencies(df, y, level + 1, f)
    return lst

def forwardDependencies(df, f, w, level = 0, p = None, ):
    """
    Recursively get all forward dependencies of a field

    Args:
        df: Input data frame
        f: Source field replacement ID
        w: List of root source field worksheet ID dependencies
        rs: Root source field source name
        level: Dependency level (0 = root, -1 = level 1 backwards, etc.)
        p: Originating parent source field replacement ID

    Returns: 
        List of all forward dependencies of the input source field
    """
    x = df.loc[df.id == f][["category", "worksheets"]]
    cat, ws = x.head(1).values.flatten()
    depList = list(df.loc[df.dependency == f]["id"])
    lst = []

    # get overlap of worksheets with root list
    nSheet = len([x for x in w if x in ws])

    if level > 0: 
        # add field dependencies
        lst += [{"parent": p, "child": f, \
            "level": "+{0}".format(level), "category": cat, 
            "sheets": nSheet}]
    else:
        # add root sheet dependencies (already is full list)
        for sh in ws:
            lst += [{"parent": f, "child": sh, \
                "level": "0", "category": "Sheet", 
            "sheets": 1}]
    
    # add dependencies of dependency
    if len(depList) > 0:
        # remove reference by copying the list
        for y in depList.copy(): 
            lst += forwardDependencies(df, y, w, level + 1, f)

    return lst

def uniqueDependencies(d, g, f):
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

def maxDependencyLevel(l):
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

def fieldsFromCategory(l, c, f):
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

def addFieldNode(sf, l, cat, shapes, colors, calc):
    """
    Creates graph node objects for an input source field

    Args:
        sf: Input source field replacement ID
        l: Input source field label
        cat: Input source field category
        shapes: List of shapes per source field category
        colors: List of colors per source field category
        calc: Input source field calculation expression

    Returns: 
        List of 2 node objects with name equal to the replacement ID, 
        label equal to the source field label and shape/color/tooltip based on 
        field type
    """
    if calc == "": c = " "
    else: c = calc
    node = pydot.Node(name = sf, label = l, shape = shapes[cat],
        fillcolor = colors[cat], style = "filled", tooltip = c)
    return [node]

def fieldIDMapping(x, s, d):
    """
    Replace IDs by labels for an input string or dict list

    Args:
        x: Input string or dict list
        s: Source name
        d: Dictionary of (field/sheet) label -> ID mappings

    Returns: 
        String or dict list with all field IDs replaced by labels 
        and references to internal source fields removed
    """
    # temporarily convert the input to a string
    res = str(x)
    # replace source field ID by source field name
    for key in d: res = res.replace(d.get(key), key)
    # internal source field references: only use field name
    res = res.replace(s + ".", "")

    # restore original structure if needed
    if x.__class__.__name__ == 'list':
        res = [json.loads(idx.replace("'", '"')) for idx in [res]][0]
    return res

def visualizeFieldDependencies(df, sf, l, g, din, svg = False):
    """
    Creates output PNG/SVG files containing all dependencies for a 
    given source field

    Args:
        df: Input data frame containing backward and forward dependencies
        sf: Input source field replacement ID
        l: Input source field label
        g: Master graph containing all source field and field node objects
        din: Full path to root directory where graphs will be saved
        svg: Indicator (T/F) whether or not to generate SVG as well

    Returns: 
        PNG file in "<workbook path> Files\Graphs\<source field name>.png" and 
        additional SVG file (with extra attributes) if svg == True
    """
    s = l.split(".")[0]
    f = l.split(".")[1]

    dictBackward = \
        list(df[df.source_field_repl_id == sf]\
            ["field_backward_dependencies"])[0]
    dictForward = \
        list(df[df.source_field_repl_id == sf]\
            ["field_forward_dependencies"])[0]
    dictDependency = copy.deepcopy(dictBackward + dictForward)

    # create a copy of the master node list in order to not modify it
    MGCopy = copy.deepcopy(g)

    # set properties for main node
    G = pydot.Dot(graph_type = "digraph", tooltip = " ")
    subject = '"' + sf + '"'
    root = MGCopy.get_node(subject)[0]
    root.set("fillcolor", "lightblue")
    root.set("label", f)
    G.add_node(root)

    # add (parent -> child) edges to graph
    for d in dictDependency:
        # don't visualize sheet dependencies
        if d["category"] != "Sheet":
            parent = '"' + d["parent"] + '"'
            child = '"' + d["child"] + '"'
            nodeParent = MGCopy.get_node(parent)[0]
            nodeChild = MGCopy.get_node(child)[0]
            sourceParent = nodeParent.get("label").split(".")
            # replace [s].[f] label by [f] if internal reference
            if (sourceParent[0] in [s, "[Parameters]"]) & \
                (len(sourceParent) == 2):
                nodeParent.set("label", sourceParent[1])
            sourceChild = nodeChild.get("label").split(".")
            if (sourceChild[0] in [s, "[Parameters]"]) & \
                (len(sourceChild) == 2):
                nodeChild.set("label", sourceChild[1])
            G.add_node(nodeParent)
            G.add_node(nodeChild)
            edge = pydot.Edge(nodeParent, nodeChild, tooltip = " ")
            G.add_edge(edge)

    # create output graphs folder if it doesn't exist yet
    specialChar = "[^A-Za-z0-9]+"
    sout = re.sub(specialChar, '', s)
    fout = re.sub(specialChar, '', f)
    dout = "{0}{1}\\".format(din, sout)
    if not os.path.isdir(dout):
        os.makedirs(dout)
    
    # write output files with forced UTF-8 encoding to avoid errors
    # see https://github.com/pydot/pydot/issues/142
    outFile = "{0}{1}.png".format(dout, fout)
    if len(outFile) > MAXPATHSIZE:
        raise Exception(("Output graph path size for source {0} and " + 
        "field {1} ({2}) exceeds the path size " +
        "limit ({3}). Try shortening the path to the workbook, " + 
        "workbook name and/or field/parameter names. \n" + 
        "Output graph path: {4}")
            .format(s, f, len(outFile), MAXPATHSIZE, outFile))
    G.write_png(outFile, encoding = "utf-8")
    if svg:
        outFile = "{0}{1}.svg".format(dout, fout)
        G.write_svg(outFile, encoding = "utf-8")

def appendFieldsToDicts(l, k, v):
    """
    Append fixed list of (key, value) to list of dictionaries

    Args:
        l: Input dict list
        k: List of fixed key names
        v: List of fixed values

    Returns: 
        Updated version of input dict with new (key, value) pairs appended
    """
    if len(l) > 0: 
        for d in l:
            for i in range(len(k)): d[k[i]] = v[i]
    return l

def visualizeSheetDependencies(df, sh, g, din, svg = False):
    """
    Creates output PNG/SVG files containing all dependencies for a 
    given source field

    Args:
        df: Input data frame containing backward and forward dependencies
        sh: Input sheet ID
        g: Master graph containing all source field and field node objects
        din: Full path to root directory where graphs will be saved
        svg: Indicator (T/F) whether or not to generate SVG as well

    Returns: 
        PNG file in "<workbook path> Files\Graphs\Sheets\<sheet name>.png" and 
        additional SVG file (with extra attributes) if svg == True
    """
    # get field -> sheet edges
    depSheet = df[(df.dependency_category == "Sheet") & 
        (df.dependency_to == sh)][["dependency_from", "dependency_to", 
        "dependency_category", "source_field_label", "source_field_repl_id"]]

    # get field -> field edges
    lstFields = list(depSheet["source_field_repl_id"])
    depField = df[(df.dependency_category != "Sheet")]
    flag = depField.apply(lambda x: 
         (x.dependency_from in lstFields) & (x.dependency_to in lstFields), 
         axis = 1)
    depField = depField.loc[flag]
    depField["dependency_category"] = "Field"
    # remove field -> field edge duplicates
    depField = depField.drop_duplicates(subset = ["dependency_from", "dependency_to"])

    # prune all fields that are parents of other fields
    lstParents = list(depField["dependency_from"].unique())
    flag = depSheet["dependency_from"].apply(lambda x: x not in lstParents)
    depSheet = depSheet.loc[flag]

    depSheet = depSheet[["dependency_from", "dependency_to", 
        "dependency_category", "source_field_label"]]
    depSheet = depSheet.append(depField)
    
    MGCopy = copy.deepcopy(g)

    # set properties for main node
    G = pydot.Dot(graph_type = "digraph", tooltip = " ")
    subject = '"' + sh + '"'
    root = MGCopy.get_node(subject)[0]
    l = root.get("label")
    G.add_node(root)
    
    # add (parent -> child) edges to graph
    for index, row in depSheet.iterrows():
        parent = '"' + row.dependency_from + '"'
        child = '"' + row.dependency_to + '"'
        nodeParent = MGCopy.get_node(parent)[0]
        nodeChild = MGCopy.get_node(child)[0]
        sourceParent = nodeParent.get("label").split(".")
        # replace [s].[f] label by [f] if internal reference
        if len(sourceParent) == 2: nodeParent.set("label", sourceParent[1])
        sourceChild = nodeChild.get("label").split(".")
        if len(sourceChild) == 2: nodeChild.set("label", sourceChild[1])
        G.add_node(nodeParent)
        G.add_node(nodeChild)
        edge = pydot.Edge(nodeParent, nodeChild, tooltip = " ")
        G.add_edge(edge)

    # write output files with forced UTF-8 encoding to avoid errors
    # see https://github.com/pydot/pydot/issues/142
    specialChar = "[^A-Za-z0-9]+"
    fout = re.sub(specialChar, '', l)
    outFile = "{0}{1}.png".format(din, fout)
    if len(outFile) > MAXPATHSIZE:
        raise Exception(("Output graph path size for sheet {0} " + 
        "({1}) exceeds the path size " +
        "limit ({2}). Try shortening the path to the workbook, " + 
        "workbook name and/or field/parameter names. \n" + 
        "Output graph path: {3}")
            .format(l, len(outFile), MAXPATHSIZE, outFile))
    G.write_png(outFile, encoding = "utf-8")
    if svg:
        outFile = "{0}{1}.svg".format(din, fout)
        G.write_svg(outFile, encoding = "utf-8")