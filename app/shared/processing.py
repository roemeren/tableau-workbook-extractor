"""
processing.py

This module provides functions to process Tableau Workbook (TWB/TWBX) files, extracting 
and analyzing data sources, fields, and their dependencies. It includes context managers 
for suppressing console output and functionality for visualizing field dependencies.

Key Functionalities:

This application processes Tableau workbooks to extract data sources and fields,
generates visual representations of field dependencies, and manages 
output file organization and logging.

Usage:

The `process_twb` function serves as the main entry point, taking a 
file path and optional parameters for output handling and execution context.
"""
import warnings
from tqdm import tqdm
from shared.logging import setup_logging, stepLog, logger
from shared.common import *
from contextlib import contextmanager
from tableaudocumentapi import Workbook

@contextmanager
def suppress_stdout():
    """
    Temporarily suppress console output.

    Yields:
        None: Suppresses console output for the following commands 
        (e.g., when opening a workbook).

    Notes:
        Source: http://thesmithfam.org/blog/2012/10/25/temporarily-suppress-console-output-in-python/
    """
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:  
            yield
        finally:
            sys.stdout = old_stdout

def process_twb(filepath, output_folder=None, is_executable=True, fPNG=True):
    """
    Process a Tableau Workbook (TWB/TWBX) file to extract and analyze data sources,
    fields, and their dependencies.

    This function reads a TWB file, extracts data sources and field information,
    processes field attributes, and computes dependencies among fields and sheets.
    It generates visual representations of field dependencies if specified and saves
    output files to the specified upload folder.

    Args:
        filepath (str): The path to the Tableau workbook (TWB*) file to be processed.
        output_folder (str, optional): The directory where output files will be saved
            if not running as an executable. Defaults to None.
        is_executable (bool, optional): Flag indicating if the function is being run
            as an executable script. Defaults to True.
        fPNG (bool, optional): Flag indicating if the function also has to 
            generate PNG images next to SVG images

    Returns:
        None: This function does not return a value but generates output files
    """
    try:
        # Extract file/directory names from twb file
        inpFileName = os.path.splitext(os.path.basename(filepath))[0]

        if is_executable:
            outFileDirectory =f"{filepath} Files"
        else:
            outFileDirectory = os.path.join(output_folder, f"{inpFileName} Files")

        # Initialize logging for app
        if not is_executable: setup_logging(is_executable, outFileDirectory)

        # Ignore future warnings when reading field attributes (not applicable)
        warnings.simplefilter(action='ignore', category=FutureWarning)

        # Get initial data frame with nested data source and field objects
        progress_data["progress"] = 3
        progress_data['task'] = stepLog("Extract data sources and fields from workbook")

        with suppress_stdout():
            inpTwb = Workbook(filepath)
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

        # Unpivot fields per data source
        colId = ["data_source", "fields", "data_source_name", "data_source_caption"]
        colVal = [x for x in df.columns if x not in colId]
        df = pd.melt(df, id_vars = colId, value_vars = colVal)
        df = df[df["value"].notnull()]

        # Extract field attributes
        fieldAttr = ["id", "caption", "datatype", "role", "type", "alias", "aliases", \
            "calculation", "description", "hidden", "worksheets"]
        for attr in fieldAttr:
            df["field_" + attr] = df.apply(lambda x: getattr(x.value, attr), axis = 1)

        progress_data["progress"] = 6
        progress_data["current-task"] = stepLog("Processing fields")

        # Additional transformations
        df["field_hidden"] = df["field_hidden"].apply(lambda x: \
            np.where(x == "true", 1, 0))
        df[["data_source_caption", "field_caption", "field_calculation"]] = \
            df[["data_source_caption", "field_caption",
            "field_calculation"]].fillna('')
        
        # Add brackets to data source and field IDs if needed
        df["data_source_name"] = "[" + df["data_source_name"]+ "]"
        df["field_id"] = df["field_id"].apply(lambda x: 
            np.where(re.search(r"\[.*\]", x), x, "[{0}]".format(x)))
        df["source_field_id"] = df["data_source_name"] + "." + df["field_id"]

        # Process data source, field and sheet labels
        df[["field_label_orig", "field_label"]] = df.apply(lambda x: \
            processCaptions(x.field_id, x.field_caption), axis = 1, 
            result_type = "expand")
        df[["source_label_orig", "source_label"]] = df.apply(lambda x: \
            processCaptions(x.data_source_name, x.data_source_caption), axis = 1, 
            result_type = "expand")
        df["source_field_label"] = df["source_label"] + "." + df["field_label"]
        df["field_worksheets_orig"] = df["field_worksheets"]
        df["field_worksheets"] = df["field_worksheets_orig"].apply(lambda x: \
            processSheetNames(x))

        # Print out unique field renamings
        df["f_field"] = df["field_label_orig"] != df["field_label"]
        df["d_field"] = df["field_label_orig"].astype(str) + " -> " + \
            df["field_label"].astype(str)
        fldModified = df[df["f_field"]]["d_field"]
        for fld in fldModified: logger.info("\tRenamed field: {}".format(fld))

        # Print out unique source renamings
        df["f_source"] = df["source_label_orig"] != df["source_label"]
        df["d_source"] = df["source_label_orig"].astype(str) + " -> " + \
            df["source_label"].astype(str)
        fldModified = set(df[df["f_source"]]["d_source"])
        for fld in fldModified: logger.info("\tRenamed source: {}".format(fld))

        # Remove duplicate rows based on source field ID
        df, nDupl = removeDuplicatesByRowLength(df, "source_field_id")
        logger.info("\t{0} duplicate fields removed".format(nDupl))

        # Filter out duplicate parameter rows and [:Measure Names] field
        lstParam = list(df[df["data_source_name"] == "[Parameters]"]["field_id"])
        df["field_is_param_duplicate"] = df.apply(lambda x: \
            isParamDuplicate(lstParam, x.data_source_name, x.field_id), axis = 1)
        nDupl2 = df.shape[0]
        df = df[(df["field_is_param_duplicate"] == 0) & 
            (df["field_id"] != "[:Measure Names]")]
        nDupl2 -= df.shape[0]
        logger.info("\t{0} duplicate parameters and/or measure names removed".format(nDupl2))

        # Add a randomly generated ID field for each unique field
        baseID = getRandomReplacementBaseID(df, "field_calculation")
        df["source_field_repl_id"] = "[" + baseID + df.index.astype(str) + "]"

        # Create source fields to ID mapping dictionary as well as the reverse
        dictFieldIDToID = \
            fieldMappingTable(df, "source_field_id", "source_field_repl_id")

        # Clean up field calculations and aliases
        lstFieldID = list(df["field_id"].unique())
        df["field_calculation_cleaned"] = \
            df.apply(lambda x: \
            fieldCalculationMapping(x.field_calculation, x.data_source_name, 
            dictFieldIDToID, lstFieldID), axis = 1)

        # Map standardized sheet names (including square brackets) to sheet IDs
        df["field_worksheets"] = df["field_worksheets"].apply(
            lambda lst: [f"[{x}]" for x in lst] \
                if isinstance(lst, list) and lst else lst
        )
        dictSheetToID = sheetMappingTable(df, "field_worksheets")
        df["field_worksheets_id"] = df["field_worksheets"].apply(lambda x: 
            sheetMapping(x, dictSheetToID))

        # Get list of field dependencies
        lstSourceFields = list(df["source_field_repl_id"].unique())
        df["field_calculation_dependencies"] = \
            df["field_calculation_cleaned"].apply(lambda x: \
                fieldCalculationDependencies(lstSourceFields, x))

        # Calculate type of field
        df["field_category"] = df.apply(lambda x: \
            fieldCategory(x.source_field_label, x.field_calculation_cleaned), axis = 1)

        progress_data["progress"] = 9
        progress_data["current-task"] = stepLog("Processing dependencies")

        # Get full list of backward dependencies
        shared_cache = {}
        df["field_backward_dependencies"] = df["source_field_repl_id"].apply(
            lambda x: backwardDependencies(df, x, _cache=shared_cache)
        )

        # Get full list of forward dependencies using exploded version of df (faster)
        dfExplode = df[["source_field_repl_id", "field_category", \
            "field_worksheets_id", "field_calculation_dependencies"]]
        dfExplode = dfExplode.explode("field_calculation_dependencies")
        dfExplode.columns = ["id", "category", "worksheets", "dependency"]
        shared_cache = {}
        df["field_forward_dependencies"] = \
            df.apply(lambda x: \
                forwardDependencies(dfExplode, x.source_field_repl_id, 
                x.field_worksheets_id, _cache=shared_cache), axis = 1)

        # Only keep unique dependencies with their max level
        df["field_backward_dependencies"] = \
            df.apply(lambda x: \
                uniqueDependencies(x.field_backward_dependencies, 
                ["child", "parent", "category"], "level"), axis = 1)
        df["field_forward_dependencies"] = \
            df.apply(lambda x: \
                uniqueDependencies(x.field_forward_dependencies, 
                ["child", "parent", "category", "sheets"], 
                "level"), axis = 1)

        # Get some dependency aggregates (INCORRECT)
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
        df[["n_backward_dependencies", "n_worksheet_dependencies", 
            "n_forward_dependencies", "n_backward_dependencies_field", 
            "n_backward_dependencies_lod"]] = \
            df[["field_backward_dependencies", "field_worksheets", 
            "field_forward_dependencies", "source_field_dependencies", 
            "lod_backward_dependencies"]].apply(lambda x: x.str.len(), axis = 1)
        df["n_forward_dependencies"] = df["n_forward_dependencies"] - \
            df["n_worksheet_dependencies"] 

        # Flag unused fields (field and its forward dependencies not used in sheets)
        df["flag_unused"] = (df["n_worksheet_dependencies"] == 0).astype(int)

        # Finalize calculated field expressions
        dictFieldToID = fieldMappingTable(df, "source_field_label", 
            "source_field_repl_id")
        dictLabelToID = {**dictFieldToID, **dictSheetToID}

        if fDepFields or fDepSheets:
            df["field_calculation_cleaned"] = df.apply(lambda x: 
                fieldIDMapping(x.field_calculation_cleaned, x.source_label, 
                    dictLabelToID), axis = 1)
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

            # Add sheet nodes
            for x in dictSheetToID:
                node = pydot.Node(name=dictSheetToID[x], label=x, shape="box",
                    fillcolor="grey", style="filled", tooltip=" ")
                gMaster.add_node(node)

        # Create new data frame with flattened dependencies
        df["field_backward_dependencies"] = \
            df.apply(lambda x: appendFieldsToDicts(x.field_backward_dependencies, 
            ["source_field_repl_id"], [x.source_field_repl_id]), axis = 1)
        df["field_forward_dependencies"] = \
            df.apply(lambda x: appendFieldsToDicts(x.field_forward_dependencies, 
            ["source_field_repl_id"], [x.source_field_repl_id]), axis = 1)
        lstBw = [item for x in list(df.field_backward_dependencies) for item in x]
        lstFw = [item for x in list(df.field_forward_dependencies) for item in x]
        df2 = pd.DataFrame(lstBw + lstFw)

        # Join with other field attributes
        dfSel = df[["source_field_repl_id", "source_label", "field_label", 
            "source_field_label", "field_category"]]
        df2 = pd.merge(left = df2, right = dfSel, on = "source_field_repl_id")
        # Reorder and rename columns
        df2 = df2[["source_label", "field_label", "source_field_label", 
            "source_field_repl_id", "field_category", "parent", "child", 
            "level", "category", "sheets"]]
        df2.columns = ["source_label", "field_label", "source_field_label",  
                        "source_field_repl_id", "field_category", "dependency_from",
                            "dependency_to", "dependency_level", "dependency_category",
                            "dependency_worksheets_overlap"]
        
        outSheetDirectory = os.path.join(outFileDirectory, 'Fields')
        outFilePath = os.path.join(outSheetDirectory, inpFileName + '.xlsx')

        progress_data["progress"] = 12
        progress_data["current-task"] = stepLog("Saving table results")

        if not os.path.isdir(outSheetDirectory):
            os.makedirs(outSheetDirectory)
        df_original = df.copy()
        df2_original = df2.copy()

        # Output 1: field info
        lstClean = ["field_calculation_dependencies", 
        "field_backward_dependencies", "field_forward_dependencies", 
        "source_field_dependencies"]
        for col in lstClean:
            df[col] = df.apply(lambda x: fieldIDMapping(x[col], x.source_label, 
                dictLabelToID), axis = 1)

        colKeep = ["source_field_repl_id", "source_label", "field_label", "source_field_label",
            "field_datatype", "field_role", 
            "field_type", "field_aliases", "field_description", 
            "field_hidden", "field_worksheets", "field_category", 
            "field_calculation_cleaned", "source_field_dependencies", 
            "field_backward_dependencies_max_level", 
            "field_forward_dependencies_max_level", 
            "n_backward_dependencies", "n_forward_dependencies",
            "n_backward_dependencies_field", "n_backward_dependencies_lod",
            "n_worksheet_dependencies", "flag_unused"]
        df = df[colKeep]

        # Output 2: dependencies info
        lstClean = ["dependency_from", "dependency_to"]
        for col in lstClean:
            df2[col] = df2.apply(lambda x: fieldIDMapping(x[col], x.source_label, 
                dictLabelToID), axis = 1)
        # Move "source_field_repl_id" to first position
        df2.insert(0, "source_field_repl_id", df2.pop("source_field_repl_id"))

        # Store results and finish
        if not os.path.isdir(outFileDirectory):
            os.makedirs(outFileDirectory)

        with pd.ExcelWriter(outFilePath) as writer:
            df.to_excel(writer, sheet_name = "fields", index = False)
            df2.to_excel(writer, sheet_name = "dependencies", index = False)

        outParquetPath = os.path.join(outSheetDirectory, 'fields.parquet')
        df["field_aliases"] = df["field_aliases"].astype(str) # to avoid errors
        df.to_parquet(outParquetPath, engine="pyarrow", index=False)
        outParquetPath = os.path.join(outSheetDirectory, 'dependencies.parquet')
        df2["dependency_level"] = df2["dependency_level"].astype(int)
        df2.to_parquet(outParquetPath, engine="pyarrow", index=False)

        # Get list of unique sheets
        lstSheets = list(df2_original[df2_original.dependency_category == "Sheet"]
                    ["dependency_to"].unique())

        # Progress bar: calculate total length
        nField = df_original.shape[0] if fDepFields else 0
        nSheet = len(lstSheets) if fDepSheets else 0
        nTot = nField + nSheet
        # counter within graph creation
        current_progress = 0

        # progress bar bounds
        start_progress = 15
        end_progress = 90
        progress_range = end_progress - start_progress

        if fDepFields:
            outPath = os.path.join(outFileDirectory, 'Graphs')

            progress_data["progress"] = start_progress
            progress_data["current-task"] = \
                stepLog(f"Creating field dependency graphs per source")

            # Use tqdm for progress bar if executable, else simple progress
            iterator = tqdm(df_original.iterrows(), total=nField) if is_executable else df_original.iterrows()

            # Create dependency graphs per field
            
            for _, row in iterator:
                # Only generate graph if there are dependencies
                nDependency = row.n_backward_dependencies + row.n_forward_dependencies
                if nDependency > 0:
                    visualizeFieldDependencies(df_original, row.source_field_repl_id, 
                        row.source_field_label, gMaster, outPath, fPNG)

                if not is_executable:
                    current_progress += 1
                    progress_data["progress"] = \
                        int(start_progress + (current_progress / nTot) * progress_range)

        if fDepSheets:
            # Create output folder if it doesn't exist yet
            outPath = os.path.join(outFileDirectory, 'Graphs', 'Sheets')
            if not os.path.isdir(outPath): os.makedirs(outPath)

            progress_data["current-task"] = \
                stepLog(f"Creating sheet dependency graphs")

            # Use tqdm for progress bar if executable, else simple progress
            iterator = tqdm(lstSheets, total=nSheet) if is_executable else lstSheets

            # Create dependency graphs per sheet
            for sh in iterator:
                visualizeSheetDependencies(df2_original, sh, gMaster, outPath, fPNG)
                if not is_executable:
                    current_progress += 1
                    progress_data["progress"] = \
                        int(start_progress + (current_progress / nTot) * progress_range)
        
        zip_filename = inpFileName + ' Files.zip'
        # Set the filename for download once processing is complete
        progress_data['foldername'] = outFileDirectory
        progress_data['filename'] = zip_filename
        progress_data['progress'] = 90

        if is_executable: 
            input("Done! Press Enter to exit...")
        else:
            # Zip the output files
            zip_path = os.path.join(output_folder, zip_filename)
            zip_folder(folder_path=outFileDirectory, output_zip_path=zip_path)

            # Clean up and close the logger
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

            # Ensure progress is 100%
            progress_data['progress'] = 100

        # Return success indicator
        return None
    
    except Exception as e:
        logger.exception("An error occurred during workbook processing")
        error_msg = f"{type(e).__name__}: {e}"
        return error_msg
