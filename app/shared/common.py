"""
common.py

This module contains shared variables and utility functions
used across the Flask application for processing uploaded files.

Usage:

Import this module in both `app.py` and `processing.py` to access and modify 
the shared `progress_data`.
"""

import os
import sys
import numpy as np
import pandas as pd
import re
import json
import copy
import pydot
import random
import string
import zipfile
from functools import lru_cache

# Script parameters
fDepFields = True # create field dependency graphs?
fDepSheets = True # create sheet dependency graphs?
fSVG = True # create SVG versions of dependency graphs next to PNG?

# Keep track of progress and filename
progress_data = {'progress': 0, 'filename': None}

# Constants
MAXPATHSIZE = 260

def show_exception_and_exit(exc_type, exc_value, tb):
    """
    Keeps the application alive when an unhandled exception occurs
    Source: https://stackoverflow.com/questions/779675/stop-python-from-closing-on-error
    """
    import traceback
    traceback.print_exception(exc_type, exc_value, tb)
    input("Error encountered. Press Enter to exit...")
    sys.exit(-1)

def getRandomReplacementBaseID(df, c, suffix = ""):
    """
    Generate a random ID of 10 lowercase letters combined with the 
    dataframe index.

    The generated ID is used as a base for a field identifier. It ensures that 
    the new ID does not match any values already present in the specified column.

    Args:
        df (pandas.DataFrame): The input dataframe from which unique values 
            are checked.
        c (str): The column name in the dataframe to ensure none of 
            the generated IDs conflict with existing values.
        suffix (str, optional): An optional fixed suffix to append to the 
            randomly generated ID. Defaults to an empty string.
    
    Returns:
        str: A random ID consisting of 10 lowercase letters combined with the optional 
        suffix. The ID is guaranteed not to match any existing values in the 
        specified column.
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
        df (pandas.DataFrame): The input dataframe containing the 
            field references.
        colFrom: The name of the column containing the original values.
        colTo: The name of the column containing the mapped values.

    Returns:
        dict: A dictionary containing mappings from original values to 
            mapped values, where each key is an original value and each value 
            is its corresponding mapped value.
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
    Create a dictionary mapping sheet names to sheet IDs.

    Args:
        df (pandas.DataFrame): The input dataframe containing the sheet lists.
        colFrom (str): The name of the column containing the sheet names.

    Returns:
        dict: A dictionary mapping each unique sheet name to its corresponding
              sheet ID, where each key is a sheet name and each value is a 
              generated sheet ID.
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
        c (str): The source field calculation string.
        s (str): The source field name.
        d (dict): A dictionary mapping source fields to their replacement 
                  IDs.
        l (list): A list of unique field names.

    Returns:
        str: The calculation string without comments and with all field 
             ID references replaced by their corresponding unique 
             replacement ID references.

    Notes:
        This function assumes that external fields are referenced as 
        [source ID].[field ID] and internal fields as [field ID]. If this 
        is not the case, the function may return incorrect results.
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
    Replace all sheet names with sequential sheet IDs.

    Args:
        s (list): A list of sheet names.
        d (dict): A dictionary mapping sheet names to their corresponding 
                  sheet IDs.

    Returns:
        list: A list of mapped sheet IDs corresponding to the input sheet 
              names.
    """
    return list(map(d.get, s.copy()))

def processCaptions(i, c):
    """
    Process captions into a format suitable for calculations, removing 
    invalid characters for JSON parsing.

    Args:
        i (str): The source or field ID value.
        c (str): The source or field caption value.

    Returns:
        tuple: A tuple containing:
            - str: The original field name enclosed in brackets.
            - str: The processed caption enclosed in square brackets, with 
                   any additional right square brackets doubled. Single and 
                   double quotes are replaced by HTML codes (&apos; and 
                   &quot;), while a backslash (\) is replaced by two 
                   backslashes (\\).
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

def processSheetNames(s):
    """
    Remove invalid characters from sheet names for JSON parsing.

    Args:
        s (list): A list of input sheet names.

    Returns:
        list: A processed list of sheet names with single quotes replaced 
              by &apos;, double quotes replaced by &quot;, and backslashes 
              replaced by two backslashes (\\\\).
    """
    res = [x.replace("'", "&apos") for x in s]
    res = [x.replace('"', "&quot") for x in res]
    res = [x.replace("\\", '\\\\') for x in res]
    return res

def fieldCalculationDependencies(l, x):
    """
    List direct dependencies in a calculation based on a list of possible 
    values.

    Args:
        l (list): A list of all possible values that can be matched.
        x (str): An input calculation string.

    Returns:
        list: A list of values from the list `l` that were matched in the 
              string `x`.
    """
    return [s for s in l if s in x]

def removeDuplicatesByRowLength(df, x):
    """
    Remove duplicates from a DataFrame by retaining the row with the largest 
    concatenated string length per grouping.

    Args:
        df (pandas.DataFrame): The input DataFrame.
        x (str): The name of the column to group by.

    Returns:
        tuple: A tuple containing:
            - pandas.DataFrame: A copy of the input DataFrame with, for each 
              unique grouping value, the row with the largest concatenated 
              string length.
            - int: The number of duplicates removed.
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
    Checks if a field is a parameter duplicate.

    Args:
        p (list): List of parameter fields.
        s (str): Source name.
        x (str): Field name.

    Returns:
        bool: True if the field is a parameter duplicate and should be 
        removed; False otherwise.
    """
    return x in p and s != "[Parameters]"

def fieldCategory(s, c):
    """
    Returns the category of a source field.

    Args:
        s (str): Source field label.
        c (str): Source field cleaned calculation.

    Returns:
        str: Category of the source field, which can be:
            - "Parameter"
            - "Calculated Field (LOD)"
            - "Calculated Field"
            - "Field"
    """
    if s.startswith("[Parameters]."): return "Parameter"
    # LOD matching: anything between curly brackets (including line breaks)
    if re.search(r"{([^}]*)}", c, re.DOTALL): return "Calculated Field (LOD)"
    if c != "": return "Calculated Field"
    else: return "Field"

def backwardDependencies(df, f, level=0, c=None, _cache=None):
    """
    Recursively get all backward dependencies of a field with memoization and
    canonical caching (cache stores subtree as if called with level=0).

    Args:
        df (pandas.DataFrame): Input data frame.
        f (str): Source field replacement ID.
        level (int): Depth from the original root (0=root, 1=first dep, ...).
        c (str|None): Parent (the child in your naming) at previous step.
        _cache (dict|None): Internal memoization cache mapping node -> canonical list.

    Returns:
        list[dict]: Items like {"parent", "child", "level", "category"} with string levels (e.g. "-1").
    """
    if _cache is None:
        _cache = {}

    # If we have a canonical subtree for f, adapt it to the current depth
    if f in _cache:
        adapted = []
        for item in _cache[f]:
            adapted.append({
                "parent": item["parent"],
                "child":  item["child"],
                "level":  str(int(item["level"]) - level),  # shift down and convert to string
                "category": item["category"],
            })
        # Add the direct link from f -> c at this depth (if not root)
        if level > 0:
            cat = df.loc[df.source_field_repl_id == f, "field_category"].iloc[0]
            adapted.append({
                "parent": f,
                "child":  c,
                "level":  str(-level),  # always string
                "category": cat,
            })
        return adapted

    # --- Build subtree for f (possibly using cached children) ---
    x = df.loc[df.source_field_repl_id == f]
    if x.empty:
        return []

    # Get deps list robustly (empty if NaN/None)
    raw_deps = x.field_calculation_dependencies.iloc[0]
    depList = list(raw_deps) if isinstance(raw_deps, (list, tuple)) and raw_deps else []
    cat = x.field_category.iloc[0]

    lst = []
    # At non-root, add the direct edge (dependency -> current root chain)
    if level > 0:
        lst.append({
            "parent": f,
            "child":  c,
            "level":  str(-level),
            "category": cat,
        })

    # Recurse into dependencies
    for y in depList:
        lst.extend(backwardDependencies(df, y, level + 1, f, _cache))

    # --- Store canonical subtree in cache ---
    if level == 0:
        canonical = []
        for item in lst:
            # ensure level is string
            canonical.append({
                "parent": item["parent"],
                "child":  item["child"],
                "category": item["category"],
                "level":  str(item["level"]),
            })
    else:
        canonical = []
        for item in lst:
            # drop the direct link from this call
            if item["parent"] == f and item["child"] == c and str(item["level"]) == str(-level):
                continue
            canonical.append({
                "parent": item["parent"],
                "child":  item["child"],
                "category": item["category"],
                # normalize and convert to string
                "level":  str(int(item["level"]) + level),
            })

    _cache[f] = canonical
    return lst

def forwardDependencies(df, f, w, level=0, p=None, _cache=None):
    """
    Recursively get all forward dependencies of a field with memoization
    and canonical caching (cache stores subtree as if called with level=0).

    Returns:
        list[dict]: Each item has keys
            {"parent","child","level","category","sheets"}
        where "level" is always a string.
    """
    if _cache is None:
        _cache = {}

    # --- Reuse cached canonical subtree if available ---
    if f in _cache:
        adapted = []
        for item in _cache[f]:
            adapted.append({
                "parent":   item["parent"],
                "child":    item["child"],
                "level":    str(int(item["level"]) + level),
                "category": item["category"],
                "sheets":   item["sheets"],
            })
        # Add direct link from parent -> f (if not root)
        if level > 0:
            cat = df.loc[df.id == f, "category"].iloc[0]
            ws  = df.loc[df.id == f, "worksheets"].iloc[0]
            ws  = ws if isinstance(ws, (list, tuple)) else []
            nSheet = len([x for x in w if x in ws])
            adapted.append({
                "parent":   p,
                "child":    f,
                "level":    str(level),
                "category": cat,
                "sheets":   nSheet,
            })
        return adapted

    # --- Build subtree for f (fresh computation) ---
    x = df.loc[df.id == f, ["category", "worksheets"]]
    if x.empty:
        return []

    cat, ws = x.head(1).values.flatten()
    ws = ws if isinstance(ws, (list, tuple)) else []
    depList = list(df.loc[df.dependency == f, "id"])

    lst = []

    # Add all sheet dependencies just like any other (leveled)
    nSheet = len([x for x in w if x in ws])
    for sh in ws:
        lst.append({
            "parent":   f,
            "child":    sh,
            "level":    str(level),
            "category": "Sheet",
            "sheets":   nSheet,
        })

    # For non-root calls, add the direct parent->field link at current level
    if level > 0:
        lst.append({
            "parent":   p,
            "child":    f,
            "level":    str(level),
            "category": cat,
            "sheets":   nSheet,
        })

    # Recurse into forward dependencies
    for y in depList:
        lst.extend(forwardDependencies(df, y, w, level + 1, f, _cache))

    # --- Store canonical subtree (as-if level == 0) ---
    canonical = []
    for item in lst:
        # Drop the direct parent->f link when normalizing to level 0
        if level > 0 and item["parent"] == p and item["child"] == f and item["level"] == str(level):
            continue
        canonical.append({
            "parent":   item["parent"],
            "child":    item["child"],
            "level":    str(int(item["level"]) - level),
            "category": item["category"],
            "sheets":   item["sheets"],
        })

    _cache[f] = canonical
    return lst

def uniqueDependencies(d, g, f):
    """
    Keep unique dependencies from a list of dependencies with their minimum
    dependency level.

    Args:
        d (list): Input list of dependency dictionaries.
        g (list): Grouping list used to determine unique dependencies.
        f (str): Field name representing the dependency level.

    Returns:
        list: Dependency dictionaries that only contain unique dependencies 
        with their minimum dependency level.
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
    Return maximum forward or backward dependency level of a given input list.

    Args:
        l (list): Input list of dependency dictionaries.

    Returns:
        int: Maximum dependency level for the given dictionary list.
    """
    res = 0
    # note: values are formatted as text -> max('-1', '-4') = -4
    if len(l) > 0: res = max([d.get("level") for d in l])
    return res

def fieldsFromCategory(l, c, f):
    """
    Return a list of fields of a given category from a list of 
    dependency dictionaries.

    Args:
        l (list): Input list of dependency dictionaries.
        c (str): Category type to filter fields.
        f (bool): Flag indicating backward (True) or forward (False) 
        dependencies.

    Returns: 
        list: List of unique field names corresponding to the specified 
            category.
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
    Creates graph node objects for an input source field.

    Args:
        sf (str): Input source field replacement ID.
        l (str): Input source field label.
        cat (str): Input source field category.
        shapes (dict): List of shapes per source field category.
        colors (dict): List of colors per source field category.
        calc (str): Input source field calculation expression.

    Returns:
        list: List of 2 node objects with:
            - name equal to the replacement ID,
            - label equal to the source field label,
            - shape/color/tooltip based on field type.
    """
    if calc == "": c = " "
    else: c = calc
    node = pydot.Node(name = sf, label = l, shape = shapes[cat],
        fillcolor = colors[cat], style = "filled", tooltip = c)
    return [node]

def fieldIDMapping(x, s, d):
    """
    Replace IDs by labels for an input string or dict list.

    Args:
        x (str or list): Input string or dict list.
        s (str): Source name.
        d (dict): Dictionary of (field/sheet) label -> ID mappings.

    Returns:
        str or list: String or dict list with all field IDs replaced by labels 
        and references to internal source fields removed.
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
    given source field.

    Args:
        df (DataFrame): Input data frame containing backward and forward 
        dependencies.
        sf (str): Input source field replacement ID.
        l (str): Input source field label.
        g (Graph): Master graph containing all source field and field node 
        objects.
        din (str): Full path to root directory where graphs will be saved.
        svg (bool, optional): Indicator (True/False) whether or not to 
        generate SVG as well. Defaults to False.

    Returns:
        None: PNG file is saved in 
        "<workbook path> Files\Graphs\<source field name>.png" and 
        additional SVG file (with extra attributes) if svg is True.
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
    dout = os.path.join(din, sout)
    if not os.path.isdir(dout):
        os.makedirs(dout)
    
    # write output files with forced UTF-8 encoding to avoid errors
    # see https://github.com/pydot/pydot/issues/142
    outFile = os.path.join(dout, f"{fout}.png")
    if len(outFile) > MAXPATHSIZE:
        raise Exception(("Output graph path size for source {0} and " + 
        "field {1} ({2}) exceeds the path size " +
        "limit ({3}). Try shortening the path to the workbook, " + 
        "workbook name and/or field/parameter names. \n" + 
        "Output graph path: {4}")
            .format(s, f, len(outFile), MAXPATHSIZE, outFile))
    G.write_png(outFile, encoding = "utf-8")
    if svg:
        outFile = os.path.join(dout, f"{fout}.svg")
        G.write_svg(outFile, encoding = "utf-8")

def appendFieldsToDicts(l, k, v):
    """
    Append a fixed list of (key, value) to a list of dictionaries.

    Args:
        l (list): Input list of dictionaries to update.
        k (list): List of fixed key names to append.
        v (list): List of fixed values to append corresponding to keys.

    Returns:
        list: Updated version of input list with new (key, value) pairs 
        appended to each dictionary.
    """
    if len(l) > 0: 
        for d in l:
            for i in range(len(k)): d[k[i]] = v[i]
    return l

def visualizeSheetDependencies(df, sh, g, din, svg = False):
    """
    Create output PNG/SVG files containing all dependencies for a given 
    source field.

    Args:
        df (pandas.DataFrame): Input data frame containing backward and forward 
        dependencies.
        sh (str): Input sheet ID for which dependencies are visualized.
        g (Graph): Master graph containing all source field and field node 
        objects.
        din (str): Full path to the root directory where graphs will be saved.
        svg (bool, optional): Indicator (True/False) to generate SVG as well. 
        Defaults to False.

    Returns:
        None: PNG file is saved in 
        "<workbook path> Files\Graphs\Sheets\<sheet name>.png" and an 
        additional SVG file (with extra attributes) if svg is True.
    """
    # --- get field -> sheet edges (only level == "0") ---
    depSheet = df[
        (df.dependency_category == "Sheet")
        & (df.dependency_to == sh)
        & (df.dependency_level.astype(str) == "0")
    ][[
        "dependency_from",
        "dependency_to",
        "dependency_category",
        "source_field_label",
        "source_field_repl_id",
    ]]

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
    outFile = os.path.join(din, f"{fout}.png")
    if len(outFile) > MAXPATHSIZE:
        raise Exception(("Output graph path size for sheet {0} " + 
        "({1}) exceeds the path size " +
        "limit ({2}). Try shortening the path to the workbook, " + 
        "workbook name and/or field/parameter names. \n" + 
        "Output graph path: {3}")
            .format(l, len(outFile), MAXPATHSIZE, outFile))
    G.write_png(outFile, encoding = "utf-8")
    if svg:
        outFile = os.path.join(din, f"{fout}.svg")
        G.write_svg(outFile, encoding = "utf-8")

def zip_folder(folder_path, output_zip_path):
    """
    Zip the contents of a folder, preserving the folder structure.

    Args:
        folder_path (str): The path to the folder to zip.
        output_zip_path (str): The path where the output zip file will be 
            created.

    Returns:
        None: The function creates a zip file at the specified output path.
    """
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through the folder
        for root, _, files in os.walk(folder_path):
            for file in files:
                # Create the full path to the file
                file_path = os.path.join(root, file)
                # Add the file to the zip file with the correct folder structure
                zipf.write(file_path, os.path.relpath(file_path, folder_path))