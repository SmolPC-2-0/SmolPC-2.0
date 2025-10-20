import json
import time
import sys
import os
import traceback
import socket

from helper_utils import (
    managed_document,
    normalize_path,
    ensure_directory_exists,
    get_uno_desktop,
    create_property_value,
    HelperError,
)

from helper_test_functions import (
    get_text_formatting,
    get_table_info,
    has_image,
    get_page_break_info,
    get_presentation_template_info,
    get_presentation_text_formatting,
    get_slide_image_info,
)

import logging

print("Starting LibreOffice Helper Script...")
logging.info("Starting LibreOffice Helper Script...")

try:
    print("Importing UNO...")
    logging.info("Importing UNO...")
    import uno
    from com.sun.star.beans import PropertyValue
    from com.sun.star.text import ControlCharacter
    from com.sun.star.text.TextContentAnchorType import AS_CHARACTER
    from com.sun.star.awt import Size
    from com.sun.star.awt.FontSlant import ITALIC
    from com.sun.star.lang import Locale
    from com.sun.star.style.ParagraphAdjust import CENTER, LEFT, RIGHT, BLOCK
    from com.sun.star.style.BreakType import PAGE_BEFORE
    from com.sun.star.table import BorderLine2, TableBorder2
    from com.sun.star.table.BorderLineStyle import SOLID
    from com.sun.star.text.ControlCharacter import PARAGRAPH_BREAK
    from com.sun.star.connection import NoConnectException

    print("UNO imported successfully!")
    logging.info("UNO imported successfully!")
except ImportError as e:
    print(f"UNO Import Error: {e}")
    logging.error(f"UNO Import Error: {e}")
    print("This script must be run with LibreOffice's Python.")
    logging.error("This script must be run with LibreOffice's Python.")
    sys.exit(1)

# Create a server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(("localhost", 8765))
server_socket.listen(1)

print("LibreOffice helper listening on port 8765")
logging.info("LibreOffice helper listening on port 8765")

print("Socket bound to localhost:8765")
logging.info("Socket bound to localhost:8765")

# General functions


def create_document(doc_type, file_path, metadata=None):
    """Create a new LibreOffice document with optional metadata."""
    logging.info(f"Creating {doc_type} document at {file_path}")

    # Normalize path and ensure directory exists
    file_path = normalize_path(file_path)
    if not ensure_directory_exists(file_path):
        raise HelperError(f"Failed to create directory for {file_path}")

    # Get desktop
    desktop = get_uno_desktop()
    if not desktop:
        raise HelperError("Failed to connect to LibreOffice desktop")

    # Map document types
    type_map = {
        "text": "private:factory/swriter",
        "calc": "private:factory/scalc",
        "impress": "private:factory/simpress",
    }

    if doc_type not in type_map:
        raise HelperError(
            f"Invalid document type. Choose from: {list(type_map.keys())}"
        )

    try:
        # Create document
        doc = desktop.loadComponentFromURL(type_map[doc_type], "_blank", 0, ())
        if not doc:
            raise HelperError(f"Failed to create {doc_type} document")

        # Add metadata if provided
        if metadata and hasattr(doc, "DocumentProperties"):
            doc_info = doc.DocumentProperties
            logging.info(doc_info)
            for key, value in metadata.items():
                logging.info(f"{key} {value} {type(value)}")
                if hasattr(doc_info, key):
                    setattr(doc_info, key, value)

        # Save document
        file_url = uno.systemPathToFileUrl(file_path)
        logging.info(f"Saving to URL: {file_url}")

        props = [create_property_value("Overwrite", True)]
        doc.storeToURL(file_url, tuple(props))
        doc.close(True)

        # Verify file was created
        time.sleep(1)  # Wait for filesystem sync
        if os.path.exists(file_path):
            return f"Successfully created {doc_type} document at: {file_path}"
        else:
            raise HelperError(
                f"Document creation attempted, but file not found at: {file_path}"
            )

    except Exception as e:
        logging.error(f"Error creating document: {str(e)}")
        logging.error(traceback.format_exc())
        raise


def list_documents(directory):
    """List all documents in a directory."""
    dir_path = normalize_path(directory)
    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        raise HelperError(f"Directory not found: {dir_path}")

    docs = []
    # Extensions for LibreOffice and MS Office documents
    extensions = [
        ".odt",
        ".ods",
        ".odp",
        ".odg",  # LibreOffice/OpenOffice
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",  # MS Office
        ".rtf",
        ".txt",
        ".csv",
        ".pdf",  # Other common document types
    ]

    for file in os.listdir(dir_path):
        file_path = os.path.join(dir_path, file)
        if os.path.isfile(file_path):
            ext = os.path.splitext(file)[1].lower()
            if ext in extensions:
                # Get file stats
                stats = os.stat(file_path)
                size = stats.st_size

                # Format last modified time
                mod_time = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(stats.st_mtime)
                )

                # Map extension to document type
                doc_type = "unknown"
                if ext in [".odt", ".doc", ".docx", ".rtf", ".txt"]:
                    doc_type = "text"
                elif ext in [".ods", ".xls", ".xlsx", ".csv"]:
                    doc_type = "spreadsheet"
                elif ext in [".odp", ".ppt", ".pptx"]:
                    doc_type = "presentation"
                elif ext in [".odg"]:
                    doc_type = "drawing"
                elif ext in [".pdf"]:
                    doc_type = "pdf"

                docs.append(
                    {
                        "name": file,
                        "path": file_path,
                        "size": size,
                        "modified": mod_time,
                        "type": doc_type,
                        "extension": ext[1:],  # Remove leading dot
                    }
                )

    # Sort by name
    docs = sorted(docs, key=lambda x: x["name"])

    # Format as a readable string
    if not docs:
        return "No documents found in the directory."

    result = f"Found {len(docs)} documents in {dir_path}:\n\n"
    for doc in docs:
        size_kb = doc["size"] / 1024
        size_display = (
            f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"
        )
        result += f"Name: {doc['name']}\n"
        result += f"Type: {doc['type']} ({doc['extension']})\n"
        result += f"Size: {size_display}\n"
        result += f"Modified: {doc['modified']}\n"
        result += f"Path: {doc['path']}\n"
        result += "---\n"

    return result


def copy_document(source_path, target_path):
    """Create a copy of an existing document."""
    source_path = normalize_path(source_path)
    target_path = normalize_path(target_path)

    if not os.path.exists(source_path):
        raise HelperError(f"Source document not found: {source_path}")

    if not ensure_directory_exists(target_path):
        raise HelperError(f"Failed to create directory for target: {target_path}")

    # First try to open and save through LibreOffice
    with managed_document(source_path) as doc:
        # Save to new location
        target_url = uno.systemPathToFileUrl(target_path)
        props = [create_property_value("Overwrite", True)]
        doc.storeToURL(target_url, tuple(props))

    if os.path.exists(target_path):
        return f"Successfully copied document to: {target_path}"
    else:
        # If LibreOffice method failed, try direct file copy
        import shutil

        shutil.copy2(source_path, target_path)
        return f"Successfully copied document to: {target_path}"


def get_document_properties(file_path):
    """Extract document properties and statistics."""
    with managed_document(file_path) as doc:
        props = {}

        # Get basic document properties
        if hasattr(doc, "DocumentProperties"):
            doc_props = doc.DocumentProperties
            for prop in [
                "Title",
                "Subject",
                "Author",
                "Description",
                "Keywords",
                "ModifiedBy",
            ]:
                if hasattr(doc_props, prop):
                    props[prop] = getattr(doc_props, prop)

            # Get dates
            for date_prop in ["CreationDate", "ModificationDate"]:
                if hasattr(doc_props, date_prop):
                    date_val = getattr(doc_props, date_prop)
                    if date_val:
                        props[date_prop] = (
                            date_val.isoformat()
                            if hasattr(date_val, "isoformat")
                            else str(date_val)
                        )

        # Get document statistics
        if hasattr(doc, "WordCount") and hasattr(doc.WordCount, "getWordCount"):
            props["WordCount"] = doc.WordCount.getWordCount()

        if hasattr(doc, "getText"):
            text = doc.getText()
            props["CharacterCount"] = len(text.getString())

            # Count paragraphs
            paragraph_count = 0
            enum = text.createEnumeration()
            while enum.hasMoreElements():
                paragraph_count += 1
                enum.nextElement()
            props["ParagraphCount"] = paragraph_count

        return json.dumps(props, indent=2)


# Writer functions


def extract_text(file_path):
    """Extract text from a document."""
    with managed_document(file_path, read_only=True) as doc:
        if hasattr(doc, "getText"):
            return doc.getText().getString()
        else:
            raise HelperError("Document does not support text extraction")


def add_text(file_path, text, position="end"):
    """Add text to a document."""
    with managed_document(file_path) as doc:
        if hasattr(doc, "getText"):
            text_obj = doc.getText()

            if position == "start":
                text_obj.insertString(text_obj.getStart(), text, False)
            elif position == "cursor":
                cursor = text_obj.createTextCursor()
                text_obj.insertString(cursor, text, False)
            else:  # default to end
                text_obj.insertString(text_obj.getEnd(), text, False)

            # Save document
            doc.store()
            return f"Text added to {file_path}"
        else:
            raise HelperError("Document does not support text insertion")


def add_heading(file_path, text, level=1):
    """Add a heading to a document."""
    with managed_document(file_path) as doc:
        if hasattr(doc, "getText"):
            text_obj = doc.getText()
            cursor = text_obj.createTextCursor()

            # Add paragraph break
            text_obj.insertControlCharacter(text_obj.getEnd(), PARAGRAPH_BREAK, False)

            text_obj.insertString(text_obj.getEnd(), text, False)

            # Move cursor to the added text
            cursor.gotoEnd(False)
            cursor.goLeft(len(text), True)  # Select the text

            # Apply heading style
            heading_style = f"Heading {level}"
            if cursor.ParaStyleName != heading_style:
                cursor.ParaStyleName = heading_style

            # Add paragraph break
            text_obj.insertControlCharacter(text_obj.getEnd(), PARAGRAPH_BREAK, False)

            # Save document
            doc.store()
            return f"Heading added to {file_path}"
        else:
            raise HelperError("Document does not support headings")


def add_paragraph(file_path, text, style=None, alignment=None):
    """Add a paragraph with optional styling."""
    with managed_document(file_path) as doc:
        if hasattr(doc, "getText"):
            text_obj = doc.getText()
            cursor = text_obj.createTextCursor()

            # Go to the end of the document
            cursor.gotoEnd(False)

            # Insert the paragraph text
            text_obj.insertString(cursor, text, False)

            # Select the inserted text
            cursor.gotoEnd(False)
            cursor.goLeft(len(text), True)

            # Apply style if specified
            if style:
                try:
                    cursor.ParaStyleName = style
                except Exception as style_error:
                    raise HelperError(f"Error applying style: {style_error}")

            # Apply alignment if specified
            alignment_map = {
                "left": LEFT,
                "center": CENTER,
                "right": RIGHT,
                "justify": BLOCK,
            }

            if alignment and alignment.lower() in alignment_map:
                cursor.ParaAdjust = alignment_map[alignment.lower()]

            # Add paragraph break
            text_obj.insertControlCharacter(text_obj.getEnd(), PARAGRAPH_BREAK, False)

            # Save document
            doc.store()
            return f"Paragraph added to {file_path}"
        else:
            raise HelperError("Document does not support paragraphs")


def format_text(file_path, text_to_find, format_options):
    """Format specific text in a document."""
    with managed_document(file_path) as doc:
        if hasattr(doc, "getText"):
            search = doc.createSearchDescriptor()
            search.SearchString = text_to_find
            search.SearchCaseSensitive = False

            found = doc.findFirst(search)
            found_count = 0

            while found:
                found_count += 1
                # Apply formatting
                if format_options.get("bold"):
                    found.CharWeight = 150
                if format_options.get("italic"):
                    # Try to use the proper UNO constant first
                    try:
                        found.CharPosture = ITALIC
                        logging.info(f"Set CharPosture to ITALIC constant: {ITALIC}")
                    except ImportError:
                        # Fallback to numeric value
                        found.CharPosture = 2
                        logging.info("Set CharPosture to numeric value 2")

                    # Log what was actually set
                    actual_posture = getattr(found, "CharPosture", "unknown")
                    logging.info(
                        f"Actual CharPosture value after setting: {actual_posture} (type: {type(actual_posture)})"
                    )

                if format_options.get("underline"):
                    found.CharUnderline = 1
                if format_options.get("color"):
                    color = format_options["color"]
                    if isinstance(color, str) and color.startswith("#"):
                        color = int(color[1:], 16)
                    found.CharColor = color
                if format_options.get("font"):
                    found.CharFontName = format_options["font"]
                if format_options.get("size"):
                    found.CharHeight = float(format_options["size"])

                # Find next occurrence
                found = doc.findNext(found.End, search)

            doc.store()
            return f"Formatted {found_count} occurrences of '{text_to_find}' in {file_path}"
        else:
            raise HelperError("Document does not support text formatting")


def search_replace_text(file_path, search_text, replace_text):
    """Search and replace text throughout the document."""
    with managed_document(file_path) as doc:
        if hasattr(doc, "getText"):
            text_obj = doc.getText()
            document_text = text_obj.getString()

            # Check if text exists in document
            if search_text not in document_text:
                raise HelperError(f"Text '{search_text}' not found in document")

            # Create replace descriptor
            replace_desc = doc.createReplaceDescriptor()
            replace_desc.SearchString = search_text
            replace_desc.ReplaceString = replace_text
            replace_desc.SearchCaseSensitive = False
            replace_desc.SearchWords = False

            # Perform replacement
            count = doc.replaceAll(replace_desc)

            # Save document
            doc.store()
            return f"Replaced {count} occurrences of '{search_text}' with '{replace_text}' in {file_path}"
        else:
            raise HelperError("Document does not support search and replace")


def delete_text(file_path, text_to_delete):
    """Delete specific text from the document."""
    return search_replace_text(file_path, text_to_delete, "")


def add_table(file_path, rows, columns, data=None, header_row=False):
    """Add a table to a document."""
    with managed_document(file_path) as doc:
        if hasattr(doc, "getText"):
            text = doc.getText()
            cursor = text.createTextCursor()
            cursor.gotoEnd(False)  # Move to end of document

            # Create table
            table = doc.createInstance("com.sun.star.text.TextTable")
            table.initialize(rows, columns)
            text.insertTextContent(cursor, table, False)

            # Populate table if data is provided
            if data:
                try:
                    for row_idx, row_data in enumerate(data):
                        if row_idx >= rows:
                            break
                        for col_idx, cell_value in enumerate(row_data):
                            if col_idx >= columns:
                                break
                            cell_name = chr(65 + col_idx) + str(
                                row_idx + 1
                            )  # A1, B1, etc.
                            cell = table.getCellByName(cell_name)
                            cell_text = cell.getText()
                            cell_text.setString(str(cell_value))
                except Exception as table_error:
                    raise HelperError(f"Error populating table: {str(table_error)}")

            # Format header row if requested
            if header_row and rows > 0:
                try:
                    # Format cells in first row as bold
                    for col_idx in range(columns):
                        cell_name = chr(65 + col_idx) + "1"  # A1, B1, etc.
                        cell = table.getCellByName(cell_name)
                        cursor = cell.getText().createTextCursor()
                        cursor.gotoStart(False)
                        cursor.gotoEnd(True)
                        cursor.CharWeight = 150  # Bold
                except Exception as header_error:
                    raise HelperError(f"Error formatting header row: {header_error}")

            # Save document
            doc.store()
            return f"Table added to {file_path}"


def format_table(file_path, table_index, format_options):
    """Format a table with borders, shading, etc."""
    with managed_document(file_path) as doc:
        if not hasattr(doc, "getTextTables"):
            raise HelperError("Document does not support table formatting")

        tables = doc.getTextTables()
        if tables.getCount() <= table_index:
            raise HelperError(
                f"Table index {table_index} is out of range (document has {tables.getCount()} tables)"
            )

        table = tables.getByIndex(table_index)

        # Apply table formatting options
        if "border_width" in format_options:
            try:
                width = int(format_options["border_width"])
                width_in_hundredths_mm = int(width * 35.28)

                logging.info(
                    f"Setting border width: {width} points = {width_in_hundredths_mm} 1/100mm"
                )

                # Create border line
                border_line = BorderLine2()
                border_line.LineWidth = width_in_hundredths_mm
                border_line.LineStyle = SOLID
                border_line.Color = 0  # Black color

                table_border_2 = table.getPropertyValue("TableBorder2")
                table_border_2.TopLine = border_line
                table_border_2.BottomLine = border_line
                table_border_2.LeftLine = border_line
                table_border_2.RightLine = border_line
                table_border_2.HorizontalLine = border_line
                table_border_2.VerticalLine = border_line
                table.setPropertyValue("TableBorder2", table_border_2)

            except Exception as border_error:
                logging.error(f"Border formatting error: {border_error}")
                raise HelperError(f"Error applying table borders: {border_error}")

        if "background_color" in format_options:
            try:
                color = format_options["background_color"]
                if isinstance(color, str) and color.startswith("#"):
                    color = int(color[1:], 16)
                table.BackColor = color
            except Exception as color_error:
                raise HelperError(
                    f"Error applying table background color: {color_error}"
                )

        # Format specific rows if requested
        if "header_row" in format_options:
            try:
                if format_options["header_row"]:
                    row = table.getRows().getByIndex(0)
                    row.BackColor = 13421772  # Light gray

                    # Format header cells
                    for col_idx in range(table.getColumns().getCount()):
                        cell = table.getCellByPosition(col_idx, 0)
                        cursor = cell.getText().createTextCursor()
                        cursor.gotoStart(False)
                        cursor.gotoEnd(True)
                        cursor.CharWeight = 150  # Bold
                else:
                    row = table.getRows().getByIndex(0)
                    row.BackColor = 16777215  # White

                    # Format header cells
                    for col_idx in range(table.getColumns().getCount()):
                        cell = table.getCellByPosition(col_idx, 0)
                        cursor = cell.getText().createTextCursor()
                        cursor.gotoStart(False)
                        cursor.gotoEnd(True)
                        cursor.CharWeight = 100  # Normal
            except Exception as header_error:
                raise HelperError(f"Error formatting header row: {header_error}")

        # Save document
        doc.store()
        return f"Table formatted in {file_path}"


def insert_image(file_path, image_path, width=None, height=None):
    """Insert an image into a document using dispatch."""
    with managed_document(file_path) as doc:
        # Normalize image path
        image_path = normalize_path(image_path)
        if not image_path:
            raise HelperError("Invalid image path provided")

        if not os.path.exists(image_path):
            raise HelperError(f"Image not found: {image_path}")

        # Get component context and necessary services
        ctx = uno.getComponentContext()
        smgr = ctx.ServiceManager

        # Create dispatch helper for UNO commands
        dispatcher = smgr.createInstanceWithContext(
            "com.sun.star.frame.DispatchHelper", ctx
        )

        # Get frame from document controller
        frame = doc.getCurrentController().getFrame()

        # Create properties for InsertGraphic command
        props = []

        # Add filename property - convert to URL format
        filename_prop = PropertyValue()
        filename_prop.Name = "FileName"
        filename_prop.Value = uno.systemPathToFileUrl(image_path)
        props.append(filename_prop)

        # Add AsLink property
        aslink_prop = PropertyValue()
        aslink_prop.Name = "AsLink"
        aslink_prop.Value = False  # Set to True if you want to link instead of embed
        props.append(aslink_prop)

        # Execute the InsertGraphic command
        dispatcher.executeDispatch(frame, ".uno:InsertGraphic", "", 0, tuple(props))

        # Optional: Resize the image if width/height provided
        if width is not None or height is not None:
            # Try to get the inserted image as the current selection
            current_selection = doc.getCurrentController().getSelection()
            if (
                current_selection
                and hasattr(current_selection, "getCount")
                and current_selection.getCount() > 0
            ):
                shape = current_selection.getByIndex(0)

                # Calculate new size preserving aspect ratio
                if width is not None and height is not None:
                    # Use both dimensions as provided
                    size = Size(width, height)
                    shape.setSize(size)
                elif width is not None:
                    # Maintain aspect ratio based on width
                    ratio = shape.Size.Height / shape.Size.Width
                    new_height = int(width * ratio)
                    shape.setSize(Size(width, new_height))
                elif height is not None:
                    # Maintain aspect ratio based on height
                    ratio = shape.Size.Width / shape.Size.Height
                    new_width = int(height * ratio)
                    shape.setSize(Size(new_width, height))
            elif current_selection:
                # Try alternative approach for Writer documents
                try:
                    # For Writer, the selection might be a TextGraphicObject
                    if hasattr(current_selection, "getImplementationName"):
                        impl_name = current_selection.getImplementationName()
                        if (
                            "TextGraphicObject" in impl_name
                            or "GraphicObject" in impl_name
                        ):
                            shape = current_selection

                            # Calculate new size preserving aspect ratio
                            if width is not None and height is not None:
                                size = Size(width, height)
                                shape.setSize(size)
                            elif width is not None:
                                ratio = shape.Size.Height / shape.Size.Width
                                new_height = int(width * ratio)
                                shape.setSize(Size(width, new_height))
                            elif height is not None:
                                ratio = shape.Size.Width / shape.Size.Height
                                new_width = int(height * ratio)
                                shape.setSize(Size(new_width, height))
                except Exception as resize_error:
                    logging.warning(f"Could not resize image: {resize_error}")

        # Save document
        doc.store()
        return f"Image inserted into {file_path}"


def insert_page_break(file_path):
    """Insert a page break at the end of the document."""
    with managed_document(file_path) as doc:
        if hasattr(doc, "getText"):
            text_obj = doc.getText()

            # Insert page break at the end of the document
            text_obj.insertControlCharacter(
                text_obj.getEnd(), ControlCharacter.PARAGRAPH_BREAK, False
            )
            cursor = text_obj.createTextCursor()
            cursor.gotoEnd(False)
            cursor.BreakType = PAGE_BEFORE

            # Save document
            doc.store()
            return f"Page break inserted in {file_path}"


# DISABLED - not currently functioning
# def create_custom_style(file_path, style_name, style_properties):
#     """Create a custom paragraph style."""
#     with managed_document(file_path) as doc:
#         # Check if document supports styles
#         if not hasattr(doc, "StyleFamilies"):
#             raise HelperError("Document does not support custom styles")

#         # Get paragraph styles
#         para_styles = doc.StyleFamilies.getByName("ParagraphStyles")

#         # Create new style or modify existing style
#         style = None
#         if para_styles.hasByName(style_name):
#             style = para_styles.getByName(style_name)
#         else:
#             style = doc.createInstance("com.sun.star.style.ParagraphStyle")
#             para_styles.insertByName(style_name, style)

#         # Apply style properties
#         for prop, value in style_properties.items():
#             if prop == "font_name":
#                 style.CharFontName = value
#             elif prop == "font_size":
#                 style.CharHeight = float(value)
#             elif prop == "bold":
#                 style.CharWeight = 150 if value else 100
#             elif prop == "italic":
#                 style.CharPosture = uno.getConstantByName("com.sun.star.awt.FontSlant.ITALIC") if value else uno.getConstantByName("com.sun.star.awt.FontSlant.NONE")
#             elif prop == "underline":
#                 style.CharUnderline = 1 if value else 0
#             elif prop == "color":
#                 if isinstance(value, str) and value.startswith("#"):
#                     value = int(value[1:], 16)
#                 style.CharColor = value
#             elif prop == "alignment":
#                 alignment_map = {
#                     "left": LEFT,
#                     "center": CENTER,
#                     "right": RIGHT,
#                     "justify": BLOCK
#                 }
#                 if value.lower() in alignment_map:
#                     style.ParaAdjust = alignment_map[value.lower()]

#         # Save document
#         doc.store()
#         return f"Custom style '{style_name}' created/updated in {file_path}"


def delete_paragraph(file_path, paragraph_index):
    """Delete a paragraph at the given index."""
    with managed_document(file_path) as doc:
        if hasattr(doc, "getText"):
            text = doc.getText()

            # Get all paragraphs
            paragraphs = []
            enum = text.createEnumeration()
            while enum.hasMoreElements():
                paragraphs.append(enum.nextElement())

            # Check if index is valid
            if paragraph_index < 0 or paragraph_index >= len(paragraphs):
                raise HelperError(
                    f"Paragraph index {paragraph_index} is out of range (document has {len(paragraphs)} paragraphs)"
                )

            # Get paragraph cursor
            paragraph = paragraphs[paragraph_index]
            paragraph_cursor = text.createTextCursorByRange(paragraph)

            # Delete paragraph
            text.removeTextContent(paragraph)

            # Save document
            doc.store()
            return f"Paragraph at index {paragraph_index} deleted from {file_path}"
        else:
            raise HelperError("Document does not support paragraph deletion")


def apply_document_style(file_path, style):
    """Apply consistent formatting throughout the document."""
    with managed_document(file_path) as doc:
        if not hasattr(doc, "getText"):
            raise HelperError("Document does not support style application")

        # Apply styles to all paragraphs
        text = doc.getText()
        cursor = text.createTextCursor()
        cursor.gotoStart(False)
        cursor.gotoEnd(True)

        # Apply character formatting
        if "font_name" in style:
            cursor.CharFontName = style["font_name"]

        if "font_size" in style:
            cursor.CharHeight = float(style["font_size"])

        if "color" in style:
            color = style["color"]
            if isinstance(color, str) and color.startswith("#"):
                color = int(color[1:], 16)
            cursor.CharColor = color

        # Apply paragraph formatting
        if "alignment" in style:
            alignment_map = {
                "left": LEFT,
                "center": CENTER,
                "right": RIGHT,
                "justify": BLOCK,
            }
            if style["alignment"].lower() in alignment_map:
                cursor.ParaAdjust = alignment_map[style["alignment"].lower()]

        # Save document
        doc.store()
        return f"Style applied to document {file_path}"


# Impress helper functions


def valid_presentation(doc):
    # Check the presentation has DrawPages
    if not hasattr(doc, "getDrawPages"):
        error_msg = "Document does not support slides/pages"
        logging.error(error_msg)
        raise HelperError(error_msg)
    return doc


def get_validated_slide(draw_pages, slide_index, delete=False):
    num_slides = draw_pages.getCount()

    # Validate slide index
    if slide_index < 0 or slide_index >= num_slides:
        error_msg = f"Slide index {slide_index} is out of range"
        raise HelperError(error_msg)

    # Prevent deletion of the last slide
    if delete and num_slides == 1:
        error_msg = "Cannot delete the only slide in the presentation"
        logging.error(error_msg)
        raise HelperError(error_msg)

    target_slide = draw_pages.getByIndex(slide_index)
    return target_slide


def find_template_files(base_directory, template_name):
    """Recursively search for presentation template files in a directory."""
    found_templates = []

    if not os.path.exists(base_directory) or not os.path.isdir(base_directory):
        logging.info(f"Directory does not exist: {base_directory}")
        return found_templates

    template_extensions = [".otp"]  # Only support .otp initially

    try:
        # Walk through all subdirectories recursively
        for root, dirs, files in os.walk(base_directory):
            logging.info(f"Searching in directory: {root}")

            for file in files:
                file_lower = file.lower()
                template_name_lower = template_name.lower()

                # Check if file matches template name and has a valid extension
                for ext in template_extensions:
                    # Check for exact match with extension
                    if file_lower == f"{template_name_lower}{ext}":
                        full_path = os.path.join(root, file)
                        found_templates.append(full_path)
                        logging.info(f"Found exact match: {full_path}")
                    # Check for partial match (template name contained in filename)
                    elif template_name_lower in file_lower and file_lower.endswith(ext):
                        full_path = os.path.join(root, file)
                        found_templates.append(full_path)
                        logging.info(f"Found partial match: {full_path}")

        # Sort by preference: exact matches first, then by file extension preference
        def sort_key(template_path):
            filename = os.path.basename(template_path).lower()
            template_name_lower = template_name.lower()

            # Exact match gets highest priority
            if filename.startswith(f"{template_name_lower}."):
                return (0, template_path)
            # Partial matches get lower priority
            else:
                return (1, template_path)

        found_templates.sort(key=sort_key)

    except Exception as e:
        logging.error(f"Error searching for templates in {base_directory}: {e}")
        logging.error(traceback.format_exc())

    return found_templates


def add_main_textbox(doc, target_slide):
    """Add a main content textbox to a slide."""
    try:
        # Create a new main content textbox since none exists
        logging.info("Creating new main content textbox")

        try:
            # Try to create an OutlinerShape first (preferred for presentations)
            content_shape = None
            try:
                content_shape = doc.createInstance(
                    "com.sun.star.presentation.OutlinerShape"
                )
                logging.info("Created OutlinerShape")
            except Exception as outliner_error:
                logging.warning(f"Could not create OutlinerShape: {outliner_error}")
                # Fallback to regular TextShape
                content_shape = doc.createInstance("com.sun.star.drawing.TextShape")
                logging.info("Created fallback TextShape")

            if not content_shape:
                raise HelperError("Failed to create content textbox shape")

            # Set size and position for main content area
            # Standard content area positioning (below title area)
            content_shape.setSize(Size(24000, 14000))  # Width: 24cm, Height: 14cm
            content_shape.setPosition(uno.createUnoStruct("com.sun.star.awt.Point"))
            content_shape.Position.X = 2000  # 2cm from left
            content_shape.Position.Y = 6000  # 6cm from top (below title area)

            # Set presentation object type for content if possible
            try:
                if hasattr(content_shape, "PresentationObject"):
                    content_shape.PresentationObject = 2  # Content placeholder type
                    logging.info("Set PresentationObject type to content")
            except Exception as pres_obj_set_error:
                logging.warning(
                    f"Could not set PresentationObject: {pres_obj_set_error}"
                )

            # Add the shape to the slide
            target_slide.add(content_shape)
            logging.info("Added content textbox to slide")

            # Set default placeholder text
            try:
                placeholder_text = "Click to add content"
                content_text = content_shape.getText()
                content_text.setString(placeholder_text)

                # Apply basic formatting
                content_cursor = content_text.createTextCursor()
                content_cursor.gotoStart(False)
                content_cursor.gotoEnd(True)
                content_cursor.CharHeight = 18
                content_cursor.ParaAdjust = LEFT
                content_cursor.CharColor = 8421504  # Gray color for placeholder

                logging.info("Set placeholder text and formatting")
            except Exception as text_error:
                logging.warning(f"Could not set placeholder text: {text_error}")

        except Exception as create_error:
            error_msg = f"Failed to create main content textbox: {create_error}"
            logging.error(error_msg)
            raise HelperError(error_msg)

        success_msg = f"Successfully added main content textbox"
        logging.info(success_msg)
        return content_shape

    except Exception as e:
        error_msg = f"Error in add_main_textbox: {str(e)}"
        logging.error(error_msg)
        logging.error(traceback.format_exc())
        try:
            if "doc" in locals():
                doc.close(True)
        except:
            pass
        raise HelperError(error_msg)


# Impress functions


def extract_impress_text(file_path):
    """Extract all text from an Impress presentation (.odp)."""
    with managed_document(file_path, read_only=True) as doc:
        if valid_presentation(doc):
            draw_pages = doc.getDrawPages()
            slide_count = draw_pages.getCount()
            all_text = []

            for i in range(slide_count):
                slide = draw_pages.getByIndex(i)
                slide_texts = []
                # Iterate over all shapes on the slide
                for shape_idx in range(slide.getCount()):
                    shape = slide.getByIndex(shape_idx)
                    # Some shapes have getString(), some have getText()
                    if hasattr(shape, "getString"):
                        text = shape.getString()
                        if text:
                            slide_texts.append(text)
                    elif hasattr(shape, "getText"):
                        text_obj = shape.getText()
                        if hasattr(text_obj, "getString"):
                            text = text_obj.getString()
                            if text:
                                slide_texts.append(text)
                all_text.append(f"Slide {i + 1}:\n" + "\n".join(slide_texts))

            return (
                "\n\n".join(all_text) if all_text else "No text found in presentation."
            )


def add_slide(file_path, slide_index=None, title=None, content=None):
    """
    Add a new slide to an Impress presentation using a built-in layout.
    Args:
        file_path: Path to the presentation file.
        slide_index: Index to insert the slide (None = append at end).
        title: Optional title text for the slide.
        content: Optional content text for the slide.
    """
    logging.info(
        f"add_slide called with: file_path={file_path}, slide_index={slide_index}, title={title}, content={content}"
    )

    with managed_document(file_path) as doc:
        if valid_presentation(doc):
            draw_pages = doc.getDrawPages()
            num_slides = draw_pages.getCount()
            logging.info(f"Current number of slides: {num_slides}")

            # Determine where to insert the slide
            insert_index = (
                num_slides
                if slide_index is None
                else max(0, min(slide_index, num_slides))
            )
            logging.info(f"Inserting slide at index: {insert_index}")

            # Insert new slide
            draw_pages.insertNewByIndex(insert_index)
            new_slide = draw_pages.getByIndex(insert_index)
            logging.info("New slide created")

            # Apply slide layout first
            layout_applied = False
            try:
                layout_type = 1  # TitleContent layout
                logging.info(f"Applying layout type: {layout_type}")

                # Apply the layout using different methods
                if hasattr(new_slide, "setLayout"):
                    new_slide.setLayout(layout_type)
                    layout_applied = True
                    logging.info("Layout applied using setLayout")
                elif hasattr(new_slide, "Layout"):
                    new_slide.Layout = layout_type
                    layout_applied = True
                    logging.info("Layout applied using Layout property")
                else:
                    logging.warning("No layout method found")

            except Exception as layout_error:
                logging.warning(f"Could not apply layout: {layout_error}")

            # Give LibreOffice time to create the placeholder shapes
            if layout_applied:
                time.sleep(0.5)

            # Now look for the actual placeholder shapes that were created by the layout
            title_shape = None
            content_shape = None

            logging.info(f"Number of shapes on slide: {new_slide.getCount()}")

            # Examine all shapes on the slide
            for i in range(new_slide.getCount()):
                shape = new_slide.getByIndex(i)
                shape_type = shape.getShapeType()
                logging.info(f"Shape {i}: {shape_type}")

                # Check if this shape has text capabilities
                if hasattr(shape, "getText"):
                    try:
                        # Check for LibreOffice presentation shapes by type
                        if shape_type == "com.sun.star.presentation.TitleTextShape":
                            title_shape = shape
                            logging.info(f"  Found title shape at index {i}")
                        elif shape_type == "com.sun.star.presentation.OutlinerShape":
                            # This is a content placeholder - use the first one we find
                            if not content_shape:
                                content_shape = shape
                                logging.info(f"  Found content shape at index {i}")
                            else:
                                logging.info(
                                    f"  Found additional content shape at index {i} (ignoring)"
                                )

                        # Fallback: Try to get presentation object type
                        elif hasattr(shape, "PresentationObject"):
                            pres_obj = shape.PresentationObject
                            logging.info(f"  PresentationObject: {pres_obj}")

                            # Check for title placeholder
                            if (
                                pres_obj in [0, 1] and not title_shape
                            ):  # Title placeholders
                                title_shape = shape
                                logging.info(f"  Found title placeholder at shape {i}")
                            # Check for content placeholder
                            elif (
                                pres_obj in [2, 3, 4, 5] and not content_shape
                            ):  # Content placeholders
                                content_shape = shape
                                logging.info(
                                    f"  Found content placeholder at shape {i}"
                                )

                        # Additional fallback: check shape name or position
                        else:
                            if hasattr(shape, "Name"):
                                shape_name = shape.Name.lower()
                                logging.info(f"  Shape name: '{shape_name}'")
                                if "title" in shape_name and not title_shape:
                                    title_shape = shape
                                    logging.info(
                                        f"  Found title shape by name at shape {i}"
                                    )
                                elif (
                                    any(
                                        keyword in shape_name
                                        for keyword in ["content", "text", "outline"]
                                    )
                                    and not content_shape
                                ):
                                    content_shape = shape
                                    logging.info(
                                        f"  Found content shape by name at shape {i}"
                                    )

                            # Position-based fallback (title usually at top)
                            if (
                                hasattr(shape, "Position")
                                and not title_shape
                                and not content_shape
                            ):
                                y_pos = shape.Position.Y
                                if y_pos < 5000:  # Top area - likely title
                                    title_shape = shape
                                    logging.info(
                                        f"  Assuming title shape by position at shape {i} (Y: {y_pos})"
                                    )
                                elif (
                                    y_pos > 5000 and not content_shape
                                ):  # Lower area - likely content
                                    content_shape = shape
                                    logging.info(
                                        f"  Assuming content shape by position at shape {i} (Y: {y_pos})"
                                    )

                    except Exception as shape_error:
                        logging.warning(f"  Error examining shape {i}: {shape_error}")

            # If we still don't have placeholders and text was requested, create manual shapes
            if title and not title_shape:
                logging.info("Creating manual title shape")
                title_shape = doc.createInstance("com.sun.star.drawing.TextShape")
                title_shape.setSize(Size(24000, 3000))
                title_shape.setPosition(uno.createUnoStruct("com.sun.star.awt.Point"))
                title_shape.Position.X = 2000
                title_shape.Position.Y = 2000
                new_slide.add(title_shape)

            if content and not content_shape:
                logging.info("Creating manual content shape")
                content_shape = doc.createInstance("com.sun.star.drawing.TextShape")
                content_shape.setSize(Size(24000, 14000))
                content_shape.setPosition(uno.createUnoStruct("com.sun.star.awt.Point"))
                content_shape.Position.X = 2000
                content_shape.Position.Y = 6000
                new_slide.add(content_shape)

            # Set title text
            if title and title_shape:
                logging.info(f"Setting title text: {title}")
                try:
                    title_text = title_shape.getText()
                    title_text.setString(title)

                    # Format title
                    title_cursor = title_text.createTextCursor()
                    title_cursor.gotoStart(False)
                    title_cursor.gotoEnd(True)
                    title_cursor.CharHeight = 28
                    title_cursor.CharWeight = 150
                    title_cursor.ParaAdjust = CENTER
                    logging.info("Title text set and formatted")
                except Exception as title_error:
                    logging.error(f"Error setting title: {title_error}")

            # Set content text
            if content and content_shape:
                logging.info(f"Setting content text: {content}")
                try:
                    content_text = content_shape.getText()
                    content_text.setString(content)

                    # Format content
                    content_cursor = content_text.createTextCursor()
                    content_cursor.gotoStart(False)
                    content_cursor.gotoEnd(True)
                    content_cursor.CharHeight = 18
                    content_cursor.ParaAdjust = LEFT
                    logging.info("Content text set and formatted")
                except Exception as content_error:
                    logging.error(f"Error setting content: {content_error}")

            # Save and close
            logging.info("Saving document...")
            doc.store()

            success_msg = f"Slide added at index {insert_index} with TitleContent layout in {file_path}"
            logging.info(success_msg)
            return success_msg


def edit_slide_content(file_path, slide_index, new_content):
    """
    Edit the main text content of a specific slide in an Impress presentation.
    """
    logging.info(
        f"edit_slide_content called with: file_path={file_path}, slide_index={slide_index}"
    )

    with managed_document(file_path) as doc:
        if valid_presentation(doc):
            draw_pages = doc.getDrawPages()

            target_slide = get_validated_slide(draw_pages, slide_index)

            logging.info(f"Editing slide at index: {slide_index}")

            # Enhanced shape detection logic
            main_content_shape = None
            all_text_shapes = []  # Store all potential text shapes for fallback

            logging.info(f"Number of shapes on slide: {target_slide.getCount()}")

            # First pass: Collect all text-capable shapes and categorize them
            for i in range(target_slide.getCount()):
                try:
                    shape = target_slide.getByIndex(i)
                    shape_type = shape.getShapeType()
                    logging.info(f"Shape {i}: {shape_type}")

                    # Check if this shape has text capabilities
                    if hasattr(shape, "getText"):
                        shape_info = {
                            "shape": shape,
                            "index": i,
                            "type": shape_type,
                            "priority": 99,  # Default low priority
                            "reason": "unknown",
                        }

                        # Priority 1: Standard presentation OutlinerShape (highest priority)
                        if shape_type == "com.sun.star.presentation.OutlinerShape":
                            shape_info["priority"] = 1
                            shape_info["reason"] = "OutlinerShape"
                            all_text_shapes.append(shape_info)
                            logging.info(
                                f"  Found OutlinerShape at index {i} (priority 1)"
                            )
                            continue

                        # Skip title shapes explicitly
                        if shape_type == "com.sun.star.presentation.TitleTextShape":
                            logging.info(f"  Skipping title shape at index {i}")
                            continue

                        # Priority 2: Check PresentationObject for content placeholders
                        try:
                            if hasattr(shape, "PresentationObject"):
                                pres_obj = shape.PresentationObject
                                logging.info(f"  PresentationObject: {pres_obj}")

                                # Content placeholders (exclude title placeholders 0,1)
                                if pres_obj in [2, 3, 4, 5]:
                                    shape_info["priority"] = 2
                                    shape_info["reason"] = (
                                        f"PresentationObject-{pres_obj}"
                                    )
                                    all_text_shapes.append(shape_info)
                                    logging.info(
                                        f"  Found content placeholder at index {i} (priority 2)"
                                    )
                                    continue
                        except Exception as pres_obj_error:
                            logging.warning(
                                f"  Error checking PresentationObject: {pres_obj_error}"
                            )

                        # Priority 3: Regular TextShape (common for manual text boxes)
                        if shape_type == "com.sun.star.drawing.TextShape":
                            shape_info["priority"] = 3
                            shape_info["reason"] = "TextShape"
                            all_text_shapes.append(shape_info)
                            logging.info(f"  Found TextShape at index {i} (priority 3)")
                            continue

                        # Priority 4: Check shape name for content indicators
                        if hasattr(shape, "Name"):
                            shape_name = shape.Name.lower()
                            logging.info(f"  Shape name: '{shape_name}'")

                            # Skip if name suggests it's a title
                            if "title" in shape_name:
                                logging.info(f"  Skipping shape with 'title' in name")
                                continue

                            # Prefer shapes with content-related names
                            if any(
                                keyword in shape_name
                                for keyword in ["content", "text", "outline", "body"]
                            ):
                                shape_info["priority"] = 4
                                shape_info["reason"] = f"name-{shape_name}"
                                all_text_shapes.append(shape_info)
                                logging.info(
                                    f"  Found content shape by name at index {i} (priority 4)"
                                )
                                continue

                        # Priority 5: Position and content-based detection
                        if hasattr(shape, "Position"):
                            y_pos = shape.Position.Y

                            # Get existing text content
                            try:
                                text_obj = shape.getText()
                                existing_text = (
                                    text_obj.getString()
                                    if hasattr(text_obj, "getString")
                                    else ""
                                )
                            except:
                                existing_text = ""

                            # Content area detection (below title area)
                            if y_pos > 3000:  # Likely content area
                                priority = 5
                                # Boost priority if shape has existing content
                                if existing_text.strip():
                                    priority = 4
                                    shape_info["reason"] = (
                                        f"position-with-content-Y{y_pos}"
                                    )
                                else:
                                    shape_info["reason"] = f"position-Y{y_pos}"

                                shape_info["priority"] = priority
                                all_text_shapes.append(shape_info)
                                logging.info(
                                    f"  Found text shape by position at index {i} (priority {priority})"
                                )

                        # Priority 6: Any other text-capable shape as final fallback
                        if not any(info["shape"] == shape for info in all_text_shapes):
                            shape_info["priority"] = 6
                            shape_info["reason"] = "fallback-text-capable"
                            all_text_shapes.append(shape_info)
                            logging.info(
                                f"  Added fallback text shape at index {i} (priority 6)"
                            )

                except Exception as shape_error:
                    logging.warning(f"  Error examining shape {i}: {shape_error}")

            # Sort by priority (lower number = higher priority) and select the best match
            if all_text_shapes:
                all_text_shapes.sort(key=lambda x: (x["priority"], x["index"]))
                best_match = all_text_shapes[0]
                main_content_shape = best_match["shape"]
                logging.info(
                    f"Selected shape at index {best_match['index']} with priority {best_match['priority']} (reason: {best_match['reason']})"
                )

                # Log all candidates for debugging
                logging.info("All text shape candidates:")
                for info in all_text_shapes:
                    logging.info(
                        f"  Index {info['index']}: Priority {info['priority']}, Reason: {info['reason']}, Type: {info['type']}"
                    )

            # If still no content shape found, create one
            if not main_content_shape:
                logging.warning(
                    "No suitable text shape found, creating new content textbox"
                )
                main_content_shape = add_main_textbox(doc, target_slide)

            # Edit the selected content shape
            try:
                # Get current text for logging
                current_text = (
                    main_content_shape.getText().getString()
                    if hasattr(main_content_shape, "getText")
                    else ""
                )
                logging.info(
                    f"Editing content shape - current text: '{current_text[:50]}...'"
                )

                # Set new content
                text_obj = main_content_shape.getText()
                text_obj.setString(new_content)

                # Verify the text was set correctly
                verification_text = text_obj.getString()
                if verification_text == new_content:
                    logging.info("Content text updated successfully")
                    edit_result = "Content updated successfully"
                else:
                    error_msg = f"Text verification failed: expected '{new_content}', got '{verification_text}'"
                    logging.error(error_msg)
                    edit_result = "Content update failed - verification error"

                # Apply basic formatting for readability
                try:
                    text_cursor = text_obj.createTextCursor()
                    text_cursor.gotoStart(False)
                    text_cursor.gotoEnd(True)
                    text_cursor.CharHeight = 18
                    text_cursor.ParaAdjust = LEFT
                    logging.info("Applied formatting to content text")
                except Exception as format_error:
                    logging.warning(f"Could not apply formatting: {format_error}")

            except Exception as edit_error:
                error_msg = f"Failed to edit content shape: {edit_error}"
                logging.error(error_msg)
                raise HelperError(error_msg)

            # Save and close
            logging.info("Saving document...")
            doc.store()

            success_msg = f"Successfully edited content of slide {slide_index} in {file_path}. {edit_result}"
            logging.info(success_msg)
            return success_msg


def edit_slide_title(file_path, slide_index, new_title):
    """
    Edit the title of a specific slide in an Impress presentation.
    """
    logging.info(
        f"edit_slide_title called with: file_path={file_path}, slide_index={slide_index}"
    )

    with managed_document(file_path) as doc:
        if valid_presentation(doc):
            draw_pages = doc.getDrawPages()

            target_slide = get_validated_slide(draw_pages, slide_index)
            logging.info(f"Editing title of slide at index: {slide_index}")

            # Enhanced shape detection logic specifically for title shapes
            main_title_shape = None
            all_title_shapes = []  # Store all potential title shapes for fallback

            logging.info(f"Number of shapes on slide: {target_slide.getCount()}")

            # First pass: Collect all text-capable shapes and categorize them for title detection
            for i in range(target_slide.getCount()):
                try:
                    shape = target_slide.getByIndex(i)
                    shape_type = shape.getShapeType()
                    logging.info(f"Shape {i}: {shape_type}")

                    # Check if this shape has text capabilities
                    if hasattr(shape, "getText"):
                        shape_info = {
                            "shape": shape,
                            "index": i,
                            "type": shape_type,
                            "priority": 99,  # Default low priority
                            "reason": "unknown",
                        }

                        # Priority 1: Standard presentation TitleTextShape (highest priority)
                        if shape_type == "com.sun.star.presentation.TitleTextShape":
                            shape_info["priority"] = 1
                            shape_info["reason"] = "TitleTextShape"
                            all_title_shapes.append(shape_info)
                            logging.info(
                                f"  Found TitleTextShape at index {i} (priority 1)"
                            )
                            continue

                        # Skip content shapes explicitly
                        if shape_type == "com.sun.star.presentation.OutlinerShape":
                            logging.info(f"  Skipping content shape at index {i}")
                            continue

                        # Priority 2: Check PresentationObject for title placeholders
                        try:
                            if hasattr(shape, "PresentationObject"):
                                pres_obj = shape.PresentationObject
                                logging.info(f"  PresentationObject: {pres_obj}")

                                # Title placeholders (0 = title, 1 = subtitle)
                                if pres_obj in [0, 1]:
                                    shape_info["priority"] = 2
                                    shape_info["reason"] = (
                                        f"PresentationObject-{pres_obj}"
                                    )
                                    all_title_shapes.append(shape_info)
                                    logging.info(
                                        f"  Found title placeholder at index {i} (priority 2)"
                                    )
                                    continue
                        except Exception as pres_obj_error:
                            logging.warning(
                                f"  Error checking PresentationObject: {pres_obj_error}"
                            )

                        # Priority 3: Regular TextShape that might be a title
                        if shape_type == "com.sun.star.drawing.TextShape":
                            # Check position - titles are usually at the top
                            if hasattr(shape, "Position"):
                                y_pos = shape.Position.Y
                                if y_pos < 3000:  # Top area - likely title
                                    shape_info["priority"] = 3
                                    shape_info["reason"] = f"TextShape-top-Y{y_pos}"
                                    all_title_shapes.append(shape_info)
                                    logging.info(
                                        f"  Found TextShape at top at index {i} (priority 3)"
                                    )
                                    continue

                        # Priority 4: Check shape name for title indicators
                        if hasattr(shape, "Name"):
                            shape_name = shape.Name.lower()
                            logging.info(f"  Shape name: '{shape_name}'")

                            # Skip if name suggests it's content
                            if any(
                                keyword in shape_name
                                for keyword in ["content", "body", "outline"]
                            ):
                                logging.info(
                                    f"  Skipping shape with content-related name"
                                )
                                continue

                            # Prefer shapes with title-related names
                            if any(
                                keyword in shape_name
                                for keyword in ["title", "heading", "header"]
                            ):
                                shape_info["priority"] = 4
                                shape_info["reason"] = f"name-{shape_name}"
                                all_title_shapes.append(shape_info)
                                logging.info(
                                    f"  Found title shape by name at index {i} (priority 4)"
                                )
                                continue

                        # Priority 5: Position-based detection for top area shapes
                        if hasattr(shape, "Position"):
                            y_pos = shape.Position.Y

                            # Get existing text content
                            try:
                                text_obj = shape.getText()
                                existing_text = (
                                    text_obj.getString()
                                    if hasattr(text_obj, "getString")
                                    else ""
                                )
                            except:
                                existing_text = ""

                            # Title area detection (top area of slide)
                            if y_pos < 3000:  # Likely title area
                                priority = 5
                                # Boost priority if shape has existing text that looks like a title
                                if (
                                    existing_text.strip()
                                    and len(existing_text.strip()) < 100
                                ):  # Short text, likely title
                                    priority = 4
                                    shape_info["reason"] = (
                                        f"position-with-title-text-Y{y_pos}"
                                    )
                                else:
                                    shape_info["reason"] = f"position-top-Y{y_pos}"

                                shape_info["priority"] = priority
                                all_title_shapes.append(shape_info)
                                logging.info(
                                    f"  Found title shape by position at index {i} (priority {priority})"
                                )

                        # Priority 6: Any other text-capable shape as final fallback (but only if in top half)
                        if (
                            hasattr(shape, "Position") and shape.Position.Y < 10000
                        ):  # Top half of slide
                            if not any(
                                info["shape"] == shape for info in all_title_shapes
                            ):
                                shape_info["priority"] = 6
                                shape_info["reason"] = "fallback-text-capable-top-half"
                                all_title_shapes.append(shape_info)
                                logging.info(
                                    f"  Added fallback title shape at index {i} (priority 6)"
                                )

                except Exception as shape_error:
                    logging.warning(f"  Error examining shape {i}: {shape_error}")

            # Sort by priority (lower number = higher priority) and select the best match
            if all_title_shapes:
                all_title_shapes.sort(key=lambda x: (x["priority"], x["index"]))
                best_match = all_title_shapes[0]
                main_title_shape = best_match["shape"]
                logging.info(
                    f"Selected title shape at index {best_match['index']} with priority {best_match['priority']} (reason: {best_match['reason']})"
                )

                # Log all candidates for debugging
                logging.info("All title shape candidates:")
                for info in all_title_shapes:
                    logging.info(
                        f"  Index {info['index']}: Priority {info['priority']}, Reason: {info['reason']}, Type: {info['type']}"
                    )

            # If still no title shape found, create one
            if not main_title_shape:
                logging.warning(
                    "No suitable title shape found, creating new title textbox"
                )
                try:
                    # Create a new title textbox
                    title_shape = doc.createInstance("com.sun.star.drawing.TextShape")
                    title_shape.setSize(Size(24000, 3000))  # Width: 24cm, Height: 3cm
                    title_shape.setPosition(
                        uno.createUnoStruct("com.sun.star.awt.Point")
                    )
                    title_shape.Position.X = 2000  # 2cm from left
                    title_shape.Position.Y = 2000  # 2cm from top

                    # Set presentation object type for title if possible
                    try:
                        if hasattr(title_shape, "PresentationObject"):
                            title_shape.PresentationObject = 0  # Title placeholder type
                            logging.info("Set PresentationObject type to title")
                    except Exception as pres_obj_set_error:
                        logging.warning(
                            f"Could not set PresentationObject: {pres_obj_set_error}"
                        )

                    # Add the shape to the slide
                    target_slide.add(title_shape)
                    main_title_shape = title_shape
                    logging.info("Created and added new title textbox to slide")

                except Exception as create_error:
                    error_msg = f"Failed to create title textbox: {create_error}"
                    logging.error(error_msg)
                    raise HelperError(error_msg)

            # Edit the selected title shape
            try:
                # Get current text for logging
                current_text = (
                    main_title_shape.getText().getString()
                    if hasattr(main_title_shape, "getText")
                    else ""
                )
                logging.info(
                    f"Editing title shape - current text: '{current_text[:50]}...'"
                )

                # Set new title
                text_obj = main_title_shape.getText()
                text_obj.setString(new_title)

                # Verify the text was set correctly
                verification_text = text_obj.getString()
                if verification_text == new_title:
                    logging.info("Title text updated successfully")
                    edit_result = "Title updated successfully"
                else:
                    error_msg = f"Text verification failed: expected '{new_title}', got '{verification_text}'"
                    logging.error(error_msg)
                    edit_result = "Title update failed - verification error"

                # Apply basic formatting for title readability
                try:
                    text_cursor = text_obj.createTextCursor()
                    text_cursor.gotoStart(False)
                    text_cursor.gotoEnd(True)
                    text_cursor.CharHeight = 28  # Larger font for title
                    text_cursor.CharWeight = 150  # Bold
                    text_cursor.ParaAdjust = CENTER  # Center alignment for title
                    logging.info("Applied formatting to title text")
                except Exception as format_error:
                    logging.warning(f"Could not apply formatting: {format_error}")

            except Exception as edit_error:
                error_msg = f"Failed to edit title shape: {edit_error}"
                logging.error(error_msg)
                raise HelperError(error_msg)

            # Save and close
            logging.info("Saving document...")
            doc.store()

            success_msg = f"Successfully edited title of slide {slide_index} in {file_path}. {edit_result}"
            logging.info(success_msg)
            return success_msg


def delete_slide(file_path, slide_index):
    """
    Delete a slide from an Impress presentation.
    Args:
        file_path: Path to the presentation file.
        slide_index: Index of the slide to delete (0-based).
    """
    logging.info(
        f"delete_slide called with: file_path={file_path}, slide_index={slide_index}"
    )

    with managed_document(file_path) as doc:
        if valid_presentation(doc):
            draw_pages = doc.getDrawPages()
            num_slides = draw_pages.getCount()

            # Get the slide to delete
            slide_to_delete = get_validated_slide(draw_pages, slide_index, delete=True)
            logging.info(f"Deleting slide at index: {slide_index}")

            # Remove the slide
            draw_pages.remove(slide_to_delete)
            logging.info("Slide removed successfully")

            # Verify the slide was deleted
            new_slide_count = draw_pages.getCount()
            if new_slide_count != num_slides - 1:
                error_msg = f"Slide deletion verification failed: expected {num_slides - 1} slides, got {new_slide_count}"
                logging.error(error_msg)
                raise HelperError(error_msg)

            # Save and close
            logging.info("Saving document...")
            doc.store()

            success_msg = f"Successfully deleted slide at index {slide_index} from {file_path}. Presentation now has {new_slide_count} slides."
            logging.info(success_msg)
            return success_msg


def apply_presentation_template(file_path, template_name):
    """Apply a presentation template to an existing presentation."""
    logging.info(f"Attempting to apply template: {template_name} to {file_path}")

    home_dir = os.path.expanduser("~")

    # Define search directories for templates
    template_search_dirs = [
        "C:/Program Files/LibreOffice/share/template/common/presnt",
        f"{home_dir}/AppData/Roaming/LibreOffice/4/user/template",
    ]

    template_doc = None
    found_template_path = None

    # Search recursively in user directories
    all_found_templates = []
    for search_dir in template_search_dirs:
        logging.info(f"Recursively searching directory: {search_dir}")
        found_templates = find_template_files(search_dir, template_name)
        all_found_templates.extend(found_templates)

    # Try to load each found template until one works
    for template_path in all_found_templates:
        try:
            logging.info(f"Trying user template: {template_path}")
            # Convert to file URL if it's a local path
            if not template_path.startswith(("file://", "http://", "https://")):
                template_url = uno.systemPathToFileUrl(template_path)
            else:
                template_url = template_path

            with managed_document(template_path, read_only=True) as template_doc:
                if template_doc:
                    found_template_path = template_url
                    logging.info(
                        f"Successfully loaded user template from: {template_path}"
                    )
                    break
        except Exception as template_error:
            logging.info(
                f"Failed to load template from {template_path}: {template_error}"
            )
            continue

    if not template_doc:
        # Create a detailed error message with search information
        search_summary = "Searched in the following locations:\n"
        for search_dir in template_search_dirs:
            if os.path.exists(search_dir):
                search_summary += f"  - {search_dir} (exists)\n"
            else:
                search_summary += f"  - {search_dir} (not found)\n"

        error_msg = f"Could not find template '{template_name}' in any location.\n{search_summary}"
        error_msg += f"Template files searched for: {template_name}.otp, {template_name}.ott, etc."
        raise HelperError(error_msg)

    # Load target presentation using the helper
    with managed_document(file_path) as target_doc:
        if valid_presentation(target_doc):
            success = False
            new_doc = None

            # Create new presentation from template and copy content
            try:
                logging.info("Creating new presentation from template...")

                # Get desktop
                desktop = get_uno_desktop()
                if not desktop:
                    raise HelperError("Failed to get UNO desktop")

                # Create new document from template
                props = [
                    create_property_value("AsTemplate", True),
                    create_property_value("Hidden", True),
                ]

                new_doc = desktop.loadComponentFromURL(
                    found_template_path, "_blank", 0, tuple(props)
                )
                if not new_doc:
                    raise HelperError("Failed to create new document from template")

                logging.info("Created new document from template")

                # Get slides from target and new document
                target_slides = target_doc.getDrawPages()
                new_slides = new_doc.getDrawPages()

                logging.info(f"Target has {target_slides.getCount()} slides")
                logging.info(f"New document has {new_slides.getCount()} slides")

                target_slide_count = target_slides.getCount()
                new_slide_count = new_slides.getCount()

                # Validation: Ensure we have slides to work with
                if target_slide_count == 0:
                    raise HelperError("Target presentation has no slides")

                # Analyze what layouts to use based on target slides
                target_slide_layouts = []
                for i in range(target_slide_count):
                    target_slide = target_slides.getByIndex(i)
                    has_title = False
                    has_content = False

                    for j in range(target_slide.getCount()):
                        shape = target_slide.getByIndex(j)
                        shape_type = shape.getShapeType()

                        if shape_type == "com.sun.star.presentation.TitleTextShape":
                            text = (
                                shape.getText().getString()
                                if hasattr(shape, "getText")
                                else ""
                            )
                            if text.strip():
                                has_title = True
                        elif shape_type == "com.sun.star.presentation.OutlinerShape":
                            text = (
                                shape.getText().getString()
                                if hasattr(shape, "getText")
                                else ""
                            )
                            if text.strip():
                                has_content = True

                    # Determine what layout is needed
                    if has_title and has_content:
                        needed_layout = 1  # TitleContent layout
                        logging.info(
                            f"Target slide {i} needs TitleContent layout (has both title and content)"
                        )
                    elif has_title:
                        needed_layout = 0  # Title only layout
                        logging.info(
                            f"Target slide {i} needs Title layout (has title only)"
                        )
                    else:
                        needed_layout = 1  # Default to TitleContent for safety
                        logging.info(
                            f"Target slide {i} needs default TitleContent layout"
                        )

                    target_slide_layouts.append(needed_layout)

                # Determine the template's default layout
                template_layout = None
                if new_slide_count > 0:
                    try:
                        first_template_slide = new_slides.getByIndex(0)
                        if hasattr(first_template_slide, "Layout"):
                            template_layout = first_template_slide.Layout
                            logging.info(
                                f"Template default layout detected: {template_layout}"
                            )
                        else:
                            template_layout = 1  # Default to TitleContent
                            logging.info(
                                "Could not detect template layout, defaulting to TitleContent"
                            )
                    except Exception as layout_detect_error:
                        logging.warning(
                            f"Could not detect template layout: {layout_detect_error}"
                        )
                        template_layout = 1  # Default to TitleContent layout

                # Add more slides to new document if needed, with appropriate layouts
                while new_slide_count < target_slide_count:
                    try:
                        new_slides.insertNewByIndex(new_slide_count)
                        added_slide = new_slides.getByIndex(new_slide_count)

                        # Use the layout needed for this specific slide
                        needed_layout = target_slide_layouts[new_slide_count]

                        try:
                            if hasattr(added_slide, "setLayout"):
                                added_slide.setLayout(needed_layout)
                                logging.info(
                                    f"Applied layout {needed_layout} to added slide {new_slide_count}"
                                )
                            elif hasattr(added_slide, "Layout"):
                                added_slide.Layout = needed_layout
                                logging.info(
                                    f"Set layout {needed_layout} on added slide {new_slide_count}"
                                )

                            # Give LibreOffice time to create the placeholder shapes
                            time.sleep(0.3)

                        except Exception as layout_error:
                            logging.warning(
                                f"Could not apply layout {needed_layout} to slide {new_slide_count}: {layout_error}"
                            )

                        new_slide_count += 1
                        logging.info(
                            f"Added slide {new_slide_count} with layout {needed_layout}"
                        )

                    except Exception as slide_add_error:
                        raise HelperError(
                            f"Failed to add slide {new_slide_count}: {slide_add_error}"
                        )

                # Track copying success for validation
                copy_errors = []
                slides_processed = 0

                # Copy content from target slides to new slides
                for i in range(target_slide_count):
                    try:
                        logging.info(
                            f"Processing slide {i + 1} of {target_slide_count}"
                        )

                        target_slide = target_slides.getByIndex(i)
                        new_slide = new_slides.getByIndex(i)

                        # Find and categorize shapes on both slides
                        target_title_shape = None
                        target_content_shape = None
                        target_other_shapes = []

                        new_title_shape = None
                        new_content_shape = None

                        # Analyze target slide shapes
                        target_shape_count = target_slide.getCount()
                        logging.info(
                            f"Target slide {i} has {target_shape_count} shapes"
                        )

                        for j in range(target_shape_count):
                            try:
                                shape = target_slide.getByIndex(j)
                                shape_type = shape.getShapeType()

                                if (
                                    shape_type
                                    == "com.sun.star.presentation.TitleTextShape"
                                ):
                                    target_title_shape = shape
                                    logging.info(
                                        f"Found target title shape on slide {i}"
                                    )
                                elif (
                                    shape_type
                                    == "com.sun.star.presentation.OutlinerShape"
                                ):
                                    if not target_content_shape:
                                        target_content_shape = shape
                                        logging.info(
                                            f"Found target content shape on slide {i}"
                                        )
                                else:
                                    target_other_shapes.append(shape)
                                    logging.info(
                                        f"Found target other shape: {shape_type}"
                                    )
                            except Exception as shape_error:
                                error_msg = f"Failed to analyze target shape {j} on slide {i}: {shape_error}"
                                logging.error(error_msg)
                                copy_errors.append(error_msg)

                        # Analyze new slide shapes
                        new_shape_count = new_slide.getCount()
                        logging.info(f"New slide {i} has {new_shape_count} shapes")

                        for j in range(new_shape_count):
                            try:
                                shape = new_slide.getByIndex(j)
                                shape_type = shape.getShapeType()

                                if (
                                    shape_type
                                    == "com.sun.star.presentation.TitleTextShape"
                                ):
                                    new_title_shape = shape
                                    logging.info(
                                        f"Found new slide title shape on slide {i}"
                                    )
                                elif (
                                    shape_type
                                    == "com.sun.star.presentation.OutlinerShape"
                                ):
                                    if not new_content_shape:
                                        new_content_shape = shape
                                        logging.info(
                                            f"Found new slide content shape on slide {i}"
                                        )
                            except Exception as shape_error:
                                error_msg = f"Failed to analyze new slide shape {j} on slide {i}: {shape_error}"
                                logging.error(error_msg)
                                copy_errors.append(error_msg)

                        # Copy title text (critical operation)
                        if target_title_shape:
                            target_title_text = (
                                target_title_shape.getText().getString()
                                if hasattr(target_title_shape, "getText")
                                else ""
                            )
                            if (
                                target_title_text.strip()
                            ):  # Only if there's actual text to copy
                                if not new_title_shape:
                                    error_msg = f"Target slide {i} has title text but new slide has no title placeholder"
                                    logging.error(error_msg)
                                    copy_errors.append(error_msg)
                                else:
                                    try:
                                        new_title_shape.getText().setString(
                                            target_title_text
                                        )
                                        logging.info(
                                            f"Copied title text: '{target_title_text[:50]}...'"
                                        )

                                        # Verify the text was actually set
                                        verification_text = (
                                            new_title_shape.getText().getString()
                                        )
                                        if verification_text != target_title_text:
                                            error_msg = f"Title text verification failed on slide {i}: expected '{target_title_text}', got '{verification_text}'"
                                            logging.error(error_msg)
                                            copy_errors.append(error_msg)
                                    except Exception as title_error:
                                        error_msg = f"Failed to copy title text on slide {i}: {title_error}"
                                        logging.error(error_msg)
                                        copy_errors.append(error_msg)
                            else:
                                logging.info(f"No title text to copy on slide {i}")

                        # Copy content text (critical operation)
                        if target_content_shape:
                            target_content_text = (
                                target_content_shape.getText().getString()
                                if hasattr(target_content_shape, "getText")
                                else ""
                            )
                            if (
                                target_content_text.strip()
                            ):  # Only if there's actual text to copy
                                if not new_content_shape:
                                    error_msg = f"Target slide {i} has content text but new slide has no content placeholder"
                                    logging.error(error_msg)
                                    copy_errors.append(error_msg)
                                else:
                                    try:
                                        new_content_shape.getText().setString(
                                            target_content_text
                                        )
                                        logging.info(
                                            f"Copied content text: '{target_content_text[:50]}...'"
                                        )

                                        # Verify the text was actually set
                                        verification_text = (
                                            new_content_shape.getText().getString()
                                        )
                                        if verification_text != target_content_text:
                                            error_msg = f"Content text verification failed on slide {i}: expected '{target_content_text}', got '{verification_text}'"
                                            logging.error(error_msg)
                                            copy_errors.append(error_msg)
                                    except Exception as content_error:
                                        error_msg = f"Failed to copy content text on slide {i}: {content_error}"
                                        logging.error(error_msg)
                                        copy_errors.append(error_msg)
                            else:
                                logging.info(f"No content text to copy on slide {i}")

                        # Copy other shapes (non-critical, but track errors)
                        other_shapes_copied = 0
                        for k, source_shape in enumerate(target_other_shapes):
                            try:
                                # Create a new shape of the same type
                                shape_type = source_shape.getShapeType()
                                cloned_shape = new_doc.createInstance(shape_type)

                                # Copy basic properties
                                if hasattr(source_shape, "Position"):
                                    cloned_shape.Position = source_shape.Position
                                if hasattr(source_shape, "Size"):
                                    cloned_shape.Size = source_shape.Size

                                # Copy style properties
                                style_properties = [
                                    "FillColor",
                                    "FillStyle",
                                    "LineColor",
                                    "LineStyle",
                                    "LineWidth",
                                ]
                                for prop in style_properties:
                                    if hasattr(source_shape, prop) and hasattr(
                                        cloned_shape, prop
                                    ):
                                        try:
                                            setattr(
                                                cloned_shape,
                                                prop,
                                                getattr(source_shape, prop),
                                            )
                                        except:
                                            pass  # Non-critical property copy failure

                                # Copy text content if it's a text shape
                                if hasattr(source_shape, "getText") and hasattr(
                                    cloned_shape, "getText"
                                ):
                                    source_text = source_shape.getText().getString()
                                    if source_text:
                                        cloned_shape.getText().setString(source_text)
                                        logging.info(
                                            f"Copied text to other shape: '{source_text[:30]}...'"
                                        )

                                # Add the cloned shape to the new slide
                                new_slide.add(cloned_shape)
                                other_shapes_copied += 1
                                logging.info(
                                    f"Successfully copied other shape {k}: {shape_type}"
                                )

                            except Exception as clone_error:
                                error_msg = f"Failed to copy other shape {k} on slide {i}: {clone_error}"
                                logging.warning(error_msg)
                                copy_errors.append(error_msg)

                        logging.info(
                            f"Copied {other_shapes_copied} of {len(target_other_shapes)} other shapes on slide {i}"
                        )
                        slides_processed += 1

                    except Exception as slide_error:
                        error_msg = (
                            f"Critical error processing slide {i}: {slide_error}"
                        )
                        logging.error(error_msg)
                        copy_errors.append(error_msg)

                # Remove any extra slides from new document
                extra_slides_removed = 0
                while new_slides.getCount() > target_slide_count:
                    try:
                        last_slide = new_slides.getByIndex(new_slides.getCount() - 1)
                        new_slides.remove(last_slide)
                        extra_slides_removed += 1
                        logging.info(f"Removed extra slide")
                    except Exception as remove_slide_error:
                        error_msg = (
                            f"Failed to remove extra slide: {remove_slide_error}"
                        )
                        logging.error(error_msg)
                        copy_errors.append(error_msg)
                        break

                # CRITICAL VALIDATION: Check if all operations succeeded
                if copy_errors:
                    error_summary = f"Content copying failed with {len(copy_errors)} errors. No changes will be applied to preserve data integrity."
                    logging.error(error_summary)
                    for error in copy_errors:
                        logging.error(f"  - {error}")
                    raise HelperError(f"{error_summary} First error: {copy_errors[0]}")

                if slides_processed != target_slide_count:
                    raise HelperError(
                        f"Only processed {slides_processed} of {target_slide_count} slides. Aborting to prevent data loss."
                    )

                # Verify final slide count matches
                if new_slides.getCount() != target_slide_count:
                    raise HelperError(
                        f"Final slide count mismatch: expected {target_slide_count}, got {new_slides.getCount()}"
                    )

                logging.info(
                    "All content copied successfully. Proceeding with file replacement."
                )

                # Only now that everything is verified, save new document over the target
                file_url = uno.systemPathToFileUrl(normalize_path(file_path))
                save_props = [create_property_value("Overwrite", True)]

                try:
                    new_doc.storeToURL(file_url, tuple(save_props))
                    logging.info("Successfully saved new document over target file")
                except Exception as save_error:
                    raise HelperError(
                        f"Failed to save templated document: {save_error}"
                    )

                success = True
                logging.info("Template applied successfully with all content preserved")

            except Exception as process_error:
                logging.error(f"Template application failed: {process_error}")
                logging.error(traceback.format_exc())
                # Don't set success = True, so no changes are applied
                raise process_error

            finally:
                # Clean up documents
                try:
                    if new_doc:
                        new_doc.close(True)
                        logging.info("Closed new document")
                except:
                    pass

            if success:
                logging.info(
                    f"Successfully applied template '{template_name}' to {file_path}"
                )
                return f"Successfully applied template '{template_name}' to presentation with all content preserved"
            else:
                logging.warning("Template application failed - original file unchanged")
                return f"Failed to apply template '{template_name}' to presentation - original file preserved"


def format_slide_content(file_path, slide_index, format_options):
    """
    Format the content text of a specific slide in an Impress presentation.

    Args:
        file_path: Path to the presentation file.
        slide_index: Index of the slide to format (0-based).
        format_options: Dictionary containing formatting options:
            - font_name: Font family name (e.g., "Arial", "Times New Roman")
            - font_size: Font size in points (e.g., 18, 24)
            - bold: Boolean to apply bold formatting
            - italic: Boolean to apply italic formatting
            - underline: Boolean to apply underline formatting
            - color: Text color as hex string (e.g., "#FF0000") or RGB integer
            - alignment: Text alignment ("left", "center", "right", "justify")
            - line_spacing: Line spacing multiplier (e.g., 1.5, 2.0)
            - background_color: Background color as hex string or RGB integer
    """
    logging.info(
        f"format_slide_content called with: file_path={file_path}, slide_index={slide_index}"
    )

    with managed_document(file_path) as doc:
        if valid_presentation(doc):
            draw_pages = doc.getDrawPages()

            target_slide = get_validated_slide(draw_pages, slide_index)
            logging.info(f"Formatting content of slide at index: {slide_index}")

            # Find the main content shape using similar logic as edit_slide_content
            main_content_shape = None
            all_text_shapes = []

            logging.info(f"Number of shapes on slide: {target_slide.getCount()}")

            # Collect all text-capable shapes and categorize them
            for i in range(target_slide.getCount()):
                try:
                    shape = target_slide.getByIndex(i)
                    shape_type = shape.getShapeType()
                    logging.info(f"Shape {i}: {shape_type}")

                    if hasattr(shape, "getText"):
                        shape_info = {
                            "shape": shape,
                            "index": i,
                            "type": shape_type,
                            "priority": 99,
                            "reason": "unknown",
                        }

                        # Priority 1: Standard presentation OutlinerShape (highest priority)
                        if shape_type == "com.sun.star.presentation.OutlinerShape":
                            shape_info["priority"] = 1
                            shape_info["reason"] = "OutlinerShape"
                            all_text_shapes.append(shape_info)
                            logging.info(
                                f"  Found OutlinerShape at index {i} (priority 1)"
                            )
                            continue

                        # Skip title shapes explicitly
                        if shape_type == "com.sun.star.presentation.TitleTextShape":
                            logging.info(f"  Skipping title shape at index {i}")
                            continue

                        # Priority 2: Check PresentationObject for content placeholders
                        try:
                            if hasattr(shape, "PresentationObject"):
                                pres_obj = shape.PresentationObject
                                if pres_obj in [2, 3, 4, 5]:  # Content placeholders
                                    shape_info["priority"] = 2
                                    shape_info["reason"] = (
                                        f"PresentationObject-{pres_obj}"
                                    )
                                    all_text_shapes.append(shape_info)
                                    logging.info(
                                        f"  Found content placeholder at index {i} (priority 2)"
                                    )
                                    continue
                        except Exception as pres_obj_error:
                            logging.warning(
                                f"  Error checking PresentationObject: {pres_obj_error}"
                            )

                        # Priority 3: Regular TextShape
                        if shape_type == "com.sun.star.drawing.TextShape":
                            shape_info["priority"] = 3
                            shape_info["reason"] = "TextShape"
                            all_text_shapes.append(shape_info)
                            logging.info(f"  Found TextShape at index {i} (priority 3)")
                            continue

                        # Priority 4: Check shape name for content indicators
                        if hasattr(shape, "Name"):
                            shape_name = shape.Name.lower()
                            if "title" not in shape_name and any(
                                keyword in shape_name
                                for keyword in ["content", "text", "outline", "body"]
                            ):
                                shape_info["priority"] = 4
                                shape_info["reason"] = f"name-{shape_name}"
                                all_text_shapes.append(shape_info)
                                logging.info(
                                    f"  Found content shape by name at index {i} (priority 4)"
                                )
                                continue

                        # Priority 5: Position-based detection (below title area)
                        if hasattr(shape, "Position") and shape.Position.Y > 3000:
                            shape_info["priority"] = 5
                            shape_info["reason"] = f"position-Y{shape.Position.Y}"
                            all_text_shapes.append(shape_info)
                            logging.info(
                                f"  Found text shape by position at index {i} (priority 5)"
                            )

                except Exception as shape_error:
                    logging.warning(f"  Error examining shape {i}: {shape_error}")

            # Select the best content shape
            if all_text_shapes:
                all_text_shapes.sort(key=lambda x: (x["priority"], x["index"]))
                best_match = all_text_shapes[0]
                main_content_shape = best_match["shape"]
                logging.info(
                    f"Selected content shape at index {best_match['index']} with priority {best_match['priority']}"
                )

            if not main_content_shape:
                error_msg = f"No content shape found on slide {slide_index}"
                raise HelperError(error_msg)

            # Apply formatting to the content shape
            try:
                text_obj = main_content_shape.getText()

                # Check if there's text to format
                if not text_obj.getString().strip():
                    logging.warning("No text content found to format")

                # Create text cursor to apply formatting
                text_cursor = text_obj.createTextCursor()
                text_cursor.gotoStart(False)
                text_cursor.gotoEnd(True)  # Select all text

                # Apply font formatting
                if format_options.get("font_name"):
                    text_cursor.CharFontName = format_options["font_name"]
                    logging.info(f"Applied font: {format_options['font_name']}")

                if format_options.get("font_size"):
                    text_cursor.CharHeight = float(format_options["font_size"])
                    logging.info(f"Applied font size: {format_options['font_size']}")

                if format_options.get("bold") is not None:
                    text_cursor.CharWeight = 150 if format_options["bold"] else 100
                    logging.info(f"Applied bold: {format_options['bold']}")

                if format_options.get("italic") is not None:
                    text_cursor.CharPosture = 2 if format_options["italic"] else 0
                    logging.info(f"Applied italic: {format_options['italic']}")

                if format_options.get("underline") is not None:
                    text_cursor.CharUnderline = 1 if format_options["underline"] else 0
                    logging.info(f"Applied underline: {format_options['underline']}")

                # Apply color formatting
                if format_options.get("color"):
                    try:
                        color = format_options["color"]
                        if isinstance(color, str) and color.startswith("#"):
                            color = int(color[1:], 16)
                        text_cursor.CharColor = color
                        logging.info(f"Applied text color: {format_options['color']}")
                    except Exception as color_error:
                        logging.error(f"Error applying text color: {color_error}")

                # Apply paragraph formatting
                if format_options.get("alignment"):
                    alignment_map = {
                        "left": LEFT,
                        "center": CENTER,
                        "right": RIGHT,
                        "justify": BLOCK,
                    }
                    alignment = format_options["alignment"].lower()
                    if alignment in alignment_map:
                        text_cursor.ParaAdjust = alignment_map[alignment]
                        logging.info(f"Applied alignment: {alignment}")

                # Apply line spacing
                if format_options.get("line_spacing"):
                    try:
                        line_spacing = float(format_options["line_spacing"])
                        # Set line spacing mode and value
                        text_cursor.ParaLineSpacing = uno.createUnoStruct(
                            "com.sun.star.style.LineSpacing"
                        )
                        text_cursor.ParaLineSpacing.Mode = 1  # PROP mode (proportional)
                        text_cursor.ParaLineSpacing.Height = int(
                            line_spacing * 100
                        )  # Convert to percentage
                        logging.info(f"Applied line spacing: {line_spacing}")
                    except Exception as spacing_error:
                        logging.error(f"Error applying line spacing: {spacing_error}")

                # Apply background color to the shape if specified
                if format_options.get("background_color"):
                    try:
                        bg_color = format_options["background_color"]
                        if isinstance(bg_color, str) and bg_color.startswith("#"):
                            bg_color = int(bg_color[1:], 16)

                        # Set fill style and color for the shape
                        main_content_shape.FillStyle = 1  # SOLID fill
                        main_content_shape.FillColor = bg_color
                        logging.info(
                            f"Applied background color: {format_options['background_color']}"
                        )
                    except Exception as bg_error:
                        logging.error(f"Error applying background color: {bg_error}")

            except Exception as format_error:
                error_msg = (
                    f"Failed to apply formatting to content shape: {format_error}"
                )
                logging.error(error_msg)
                raise HelperError(error_msg)

            # Save document
            logging.info("Saving document...")
            doc.store()

            # Build success message with applied formatting details
            applied_formats = []
            for key, value in format_options.items():
                if value is not None:
                    applied_formats.append(f"{key}: {value}")

            success_msg = f"Successfully formatted content of slide {slide_index} in {file_path}. Applied: {', '.join(applied_formats)}"
            logging.info(success_msg)
            return success_msg


def format_slide_title(file_path, slide_index, format_options):
    """
    Format the title text of a specific slide in an Impress presentation.

    Args:
        file_path: Path to the presentation file.
        slide_index: Index of the slide to format (0-based).
        format_options: Dictionary containing formatting options:
            - font_name: Font family name (e.g., "Arial", "Times New Roman")
            - font_size: Font size in points (e.g., 28, 36)
            - bold: Boolean to apply bold formatting
            - italic: Boolean to apply italic formatting
            - underline: Boolean to apply underline formatting
            - color: Text color as hex string (e.g., "#FF0000") or RGB integer
            - alignment: Text alignment ("left", "center", "right", "justify")
            - line_spacing: Line spacing multiplier (e.g., 1.5, 2.0)
            - background_color: Background color as hex string or RGB integer
    """
    logging.info(
        f"format_slide_title called with: file_path={file_path}, slide_index={slide_index}, format_options={format_options}"
    )

    with managed_document(file_path) as doc:
        if valid_presentation(doc):
            draw_pages = doc.getDrawPages()

            target_slide = get_validated_slide(draw_pages, slide_index)
            logging.info(f"Formatting title of slide at index: {slide_index}")

            # Find the main title shape using similar logic as edit_slide_title
            main_title_shape = None
            all_title_shapes = []

            logging.info(f"Number of shapes on slide: {target_slide.getCount()}")

            # Collect all text-capable shapes and categorize them for title detection
            for i in range(target_slide.getCount()):
                try:
                    shape = target_slide.getByIndex(i)
                    shape_type = shape.getShapeType()
                    logging.info(f"Shape {i}: {shape_type}")

                    if hasattr(shape, "getText"):
                        shape_info = {
                            "shape": shape,
                            "index": i,
                            "type": shape_type,
                            "priority": 99,
                            "reason": "unknown",
                        }

                        # Priority 1: Standard presentation TitleTextShape (highest priority)
                        if shape_type == "com.sun.star.presentation.TitleTextShape":
                            shape_info["priority"] = 1
                            shape_info["reason"] = "TitleTextShape"
                            all_title_shapes.append(shape_info)
                            logging.info(
                                f"  Found TitleTextShape at index {i} (priority 1)"
                            )
                            continue

                        # Skip content shapes explicitly
                        if shape_type == "com.sun.star.presentation.OutlinerShape":
                            logging.info(f"  Skipping content shape at index {i}")
                            continue

                        # Priority 2: Check PresentationObject for title placeholders
                        try:
                            if hasattr(shape, "PresentationObject"):
                                pres_obj = shape.PresentationObject
                                if pres_obj in [0, 1]:  # Title placeholders
                                    shape_info["priority"] = 2
                                    shape_info["reason"] = (
                                        f"PresentationObject-{pres_obj}"
                                    )
                                    all_title_shapes.append(shape_info)
                                    logging.info(
                                        f"  Found title placeholder at index {i} (priority 2)"
                                    )
                                    continue
                        except Exception as pres_obj_error:
                            logging.warning(
                                f"  Error checking PresentationObject: {pres_obj_error}"
                            )

                        # Priority 3: Regular TextShape in top area
                        if shape_type == "com.sun.star.drawing.TextShape":
                            if (
                                hasattr(shape, "Position") and shape.Position.Y < 3000
                            ):  # Top area
                                shape_info["priority"] = 3
                                shape_info["reason"] = (
                                    f"TextShape-top-Y{shape.Position.Y}"
                                )
                                all_title_shapes.append(shape_info)
                                logging.info(
                                    f"  Found TextShape at top at index {i} (priority 3)"
                                )
                                continue

                        # Priority 4: Check shape name for title indicators
                        if hasattr(shape, "Name"):
                            shape_name = shape.Name.lower()
                            if any(
                                keyword in shape_name
                                for keyword in ["title", "heading", "header"]
                            ):
                                shape_info["priority"] = 4
                                shape_info["reason"] = f"name-{shape_name}"
                                all_title_shapes.append(shape_info)
                                logging.info(
                                    f"  Found title shape by name at index {i} (priority 4)"
                                )
                                continue

                        # Priority 5: Position-based detection for top area shapes
                        if hasattr(shape, "Position") and shape.Position.Y < 3000:
                            shape_info["priority"] = 5
                            shape_info["reason"] = f"position-top-Y{shape.Position.Y}"
                            all_title_shapes.append(shape_info)
                            logging.info(
                                f"  Found title shape by position at index {i} (priority 5)"
                            )

                except Exception as shape_error:
                    logging.warning(f"  Error examining shape {i}: {shape_error}")

            # Select the best title shape
            if all_title_shapes:
                all_title_shapes.sort(key=lambda x: (x["priority"], x["index"]))
                best_match = all_title_shapes[0]
                main_title_shape = best_match["shape"]
                logging.info(
                    f"Selected title shape at index {best_match['index']} with priority {best_match['priority']}"
                )

            if not main_title_shape:
                error_msg = f"No title shape found on slide {slide_index}"
                raise HelperError(error_msg)

            # Apply formatting to the title shape
            try:
                text_obj = main_title_shape.getText()

                # Check if there's text to format
                if not text_obj.getString().strip():
                    logging.warning("No title text found to format")

                # Create text cursor to apply formatting
                text_cursor = text_obj.createTextCursor()
                text_cursor.gotoStart(False)
                text_cursor.gotoEnd(True)  # Select all text

                # Apply font formatting
                if format_options.get("font_name"):
                    text_cursor.CharFontName = format_options["font_name"]
                    logging.info(f"Applied font: {format_options['font_name']}")

                if format_options.get("font_size"):
                    text_cursor.CharHeight = float(format_options["font_size"])
                    logging.info(f"Applied font size: {format_options['font_size']}")

                if format_options.get("bold") is not None:
                    text_cursor.CharWeight = 150 if format_options["bold"] else 100
                    logging.info(f"Applied bold: {format_options['bold']}")

                if format_options.get("italic") is not None:
                    text_cursor.CharPosture = 2 if format_options["italic"] else 0
                    logging.info(f"Applied italic: {format_options['italic']}")

                if format_options.get("underline") is not None:
                    text_cursor.CharUnderline = 1 if format_options["underline"] else 0
                    logging.info(f"Applied underline: {format_options['underline']}")

                # Apply color formatting
                if format_options.get("color"):
                    try:
                        color = format_options["color"]
                        if isinstance(color, str) and color.startswith("#"):
                            color = int(color[1:], 16)
                        text_cursor.CharColor = color
                        logging.info(f"Applied text color: {format_options['color']}")
                    except Exception as color_error:
                        logging.error(f"Error applying text color: {color_error}")

                # Apply paragraph formatting
                if format_options.get("alignment"):
                    alignment_map = {
                        "left": LEFT,
                        "center": CENTER,
                        "right": RIGHT,
                        "justify": BLOCK,
                    }
                    alignment = format_options["alignment"].lower()
                    if alignment in alignment_map:
                        text_cursor.ParaAdjust = alignment_map[alignment]
                        logging.info(f"Applied alignment: {alignment}")

                # Apply line spacing
                if format_options.get("line_spacing"):
                    try:
                        line_spacing = float(format_options["line_spacing"])
                        # Set line spacing mode and value
                        text_cursor.ParaLineSpacing = uno.createUnoStruct(
                            "com.sun.star.style.LineSpacing"
                        )
                        text_cursor.ParaLineSpacing.Mode = 1  # PROP mode (proportional)
                        text_cursor.ParaLineSpacing.Height = int(
                            line_spacing * 100
                        )  # Convert to percentage
                        logging.info(f"Applied line spacing: {line_spacing}")
                    except Exception as spacing_error:
                        logging.error(f"Error applying line spacing: {spacing_error}")

                # Apply background color to the shape if specified
                if format_options.get("background_color"):
                    try:
                        bg_color = format_options["background_color"]
                        if isinstance(bg_color, str) and bg_color.startswith("#"):
                            bg_color = int(bg_color[1:], 16)

                        # Set fill style and color for the shape
                        main_title_shape.FillStyle = 1  # SOLID fill
                        main_title_shape.FillColor = bg_color
                        logging.info(
                            f"Applied background color: {format_options['background_color']}"
                        )
                    except Exception as bg_error:
                        logging.error(f"Error applying background color: {bg_error}")

            except Exception as format_error:
                error_msg = f"Failed to apply formatting to title shape: {format_error}"
                logging.error(error_msg)
                raise HelperError(error_msg)

            # Save document
            logging.info("Saving document...")
            doc.store()

            # Build success message with applied formatting details
            applied_formats = []
            for key, value in format_options.items():
                if value is not None:
                    applied_formats.append(f"{key}: {value}")

            success_msg = f"Successfully formatted title of slide {slide_index} in {file_path}. Applied: {', '.join(applied_formats)}"
            logging.info(success_msg)
            return success_msg


def insert_slide_image(
    file_path,
    slide_index,
    image_path,
    max_width=None,
    max_height=None,
    img_width_px=None,
    img_height_px=None,
    dpi=96,
):
    """
    Insert an image into a specific slide of an Impress presentation.
    The image will be centered on the slide using proper positioning.

    Args:
        file_path: Path to the presentation file.
        slide_index: Index of the slide to insert the image into (0-based).
        image_path: Path to the image file to insert.
        max_width: Maximum width in 1/100mm (defaults to slide width minus margins).
        max_height: Maximum height in 1/100mm (defaults to slide height minus margins).
        img_width_px: Image width in pixels (for proper scaling calculation).
        img_height_px: Image height in pixels (for proper scaling calculation).
        dpi: Image DPI (for proper scaling calculation).
    """
    logging.info(
        f"insert_slide_image called with: file_path={file_path}, slide_index={slide_index}, image_path={image_path}"
    )

    with managed_document(file_path) as doc:
        if valid_presentation(doc):
            draw_pages = doc.getDrawPages()

            # Normalize and validate image path
            image_path = normalize_path(image_path)
            if not os.path.exists(image_path):
                raise HelperError(f"Image not found: {image_path}")

            target_slide = get_validated_slide(draw_pages, slide_index)
            logging.info(f"Inserting image into slide at index: {slide_index}")

            # Get slide dimensions (LibreOffice uses 1/100mm units internally)
            slide_width = 25400  # Standard slide width in 1/100mm (254mm = 10 inches)
            slide_height = (
                19050  # Standard slide height in 1/100mm (190.5mm = 7.5 inches)
            )

            # Try to get actual slide dimensions from the slide master or page setup
            try:
                # Method 1: Try to get slide dimensions from the master page
                if hasattr(target_slide, "getMasterPage"):
                    master_page = target_slide.getMasterPage()
                    if hasattr(master_page, "Width") and hasattr(master_page, "Height"):
                        slide_width = master_page.Width
                        slide_height = master_page.Height
                        logging.info(
                            f"Got slide dimensions from master page: {slide_width}x{slide_height} (1/100mm)"
                        )

                # Method 2: Try to get from the document's draw page size
                elif hasattr(doc, "getDrawPageSize"):
                    page_size = doc.getDrawPageSize()
                    slide_width = page_size.Width
                    slide_height = page_size.Height
                    logging.info(
                        f"Got slide dimensions from draw page size: {slide_width}x{slide_height} (1/100mm)"
                    )

            except Exception as size_error:
                logging.warning(
                    f"Could not get slide dimensions, using defaults: {size_error}"
                )

            # Log the parameters we received
            logging.info(
                f"Input parameters: max_width={max_width}, max_height={max_height}"
            )

            # Set maximum dimensions with reasonable defaults (75% of slide for good visual balance)
            if max_width is None:
                max_width = int(slide_width * 0.75)
            else:
                # Ensure provided max_width doesn't exceed slide
                max_width = min(max_width, int(slide_width * 0.9))

            if max_height is None:
                max_height = int(slide_height * 0.75)
            else:
                # Ensure provided max_height doesn't exceed slide
                max_height = min(max_height, int(slide_height * 0.9))

            logging.info(f"Slide dimensions: {slide_width}x{slide_height} (1/100mm)")
            logging.info(
                f"Maximum image dimensions: {max_width}x{max_height} (1/100mm)"
            )

            if img_width_px and img_height_px and dpi:
                # Convert pixels to LibreOffice units (1/100mm)
                mm_per_inch = 25.4
                conversion_factor = (mm_per_inch * 100) / dpi  # 1/100mm per pixel

                original_width = int(img_width_px * conversion_factor)
                original_height = int(img_height_px * conversion_factor)

                logging.info(
                    f"Calculated image size: {original_width}x{original_height} (1/100mm) from {img_width_px}x{img_height_px} pixels at {dpi} DPI"
                )
            else:
                # Fallback: use reasonable default size
                logging.warning(
                    "Could not get image size/DPI, using fallback dimensions"
                )
                original_width = max_width // 2
                original_height = max_height // 2
                logging.info(
                    f"Using fallback size: {original_width}x{original_height} (1/100mm)"
                )

            try:
                # Create a graphics shape to hold the image
                image_shape = doc.createInstance(
                    "com.sun.star.drawing.GraphicObjectShape"
                )
                if not image_shape:
                    raise HelperError("Failed to create graphics shape")

                # Convert image path to file URL
                image_url = uno.systemPathToFileUrl(image_path)
                logging.info(f"Image URL: {image_url}")

                # Set the image URL
                image_shape.GraphicURL = image_url

                # Calculate scaling to fit within maximum dimensions while preserving aspect ratio
                width_scale = max_width / original_width
                height_scale = max_height / original_height
                scale_factor = min(
                    width_scale, height_scale, 1.0
                )  # Don't scale up, only down

                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)

                # Ensure minimum size (at least 10mm x 10mm)
                min_size = 1000  # 10mm in 1/100mm
                if new_width < min_size:
                    new_width = min_size
                if new_height < min_size:
                    new_height = min_size

                logging.info(
                    f"Width scale: {width_scale:.3f}, Height scale: {height_scale:.3f}"
                )
                logging.info(f"Final scale factor: {scale_factor:.3f}")
                logging.info(f"Final image size: {new_width}x{new_height} (1/100mm)")

                # Set the size
                new_size = Size(new_width, new_height)
                image_shape.setSize(new_size)

                # PROPER CENTERING FOR DRAWING SHAPES
                # Calculate center position relative to slide
                slide_center_x = slide_width // 2
                slide_center_y = slide_height // 2

                # Calculate top-left position to center the image
                pos_x = slide_center_x - (new_width // 2)
                pos_y = slide_center_y - (new_height // 2)

                logging.info(f"Slide center: ({slide_center_x}, {slide_center_y})")
                logging.info(f"Image half-size: ({new_width // 2}, {new_height // 2})")
                logging.info(f"Calculated centered position: ({pos_x}, {pos_y})")

                # Set the position using the Point structure
                image_position = uno.createUnoStruct("com.sun.star.awt.Point")
                image_position.X = pos_x
                image_position.Y = pos_y
                image_shape.setPosition(image_position)

                # Verify positioning
                actual_position = image_shape.getPosition()
                logging.info(
                    f"Actual position after setting: ({actual_position.X}, {actual_position.Y})"
                )

                # Add the shape to the slide
                target_slide.add(image_shape)

                # Set additional properties for better image handling
                try:
                    if hasattr(image_shape, "KeepAspectRatio"):
                        image_shape.KeepAspectRatio = True
                        logging.info("Set KeepAspectRatio property")

                    # For drawing shapes, we can also try to set transformation matrix for perfect centering
                    if hasattr(image_shape, "Transformation"):
                        # The transformation matrix can be used for more precise positioning
                        # This is an advanced feature but might help with centering
                        logging.info("Shape has Transformation property available")

                except Exception as prop_error:
                    logging.warning(
                        f"Could not set additional image properties: {prop_error}"
                    )

                # Final verification of image bounds
                final_position = image_shape.getPosition()
                final_size = image_shape.getSize()
                image_right = final_position.X + final_size.Width
                image_bottom = final_position.Y + final_size.Height

                logging.info("Final verification:")
                logging.info(
                    f"Image position: ({final_position.X}, {final_position.Y})"
                )
                logging.info(f"Image size: {final_size.Width}x{final_size.Height}")
                logging.info(
                    f"Image bounds: X({final_position.X} to {image_right}), Y({final_position.Y} to {image_bottom})"
                )
                logging.info(
                    f"Slide bounds: X(0 to {slide_width}), Y(0 to {slide_height})"
                )

                # Check if image is properly contained within slide
                if (
                    final_position.X >= 0
                    and final_position.Y >= 0
                    and image_right <= slide_width
                    and image_bottom <= slide_height
                ):
                    logging.info("Image is properly contained within slide boundaries")
                else:
                    logging.warning("Image may extend beyond slide boundaries")

            except Exception as image_error:
                error_msg = f"Failed to create and configure image shape: {image_error}"
                logging.error(error_msg)
                raise HelperError(error_msg)

            # Save document
            logging.info("Saving document...")
            doc.store()

            success_msg = f"Successfully inserted image '{os.path.basename(image_path)}' into slide {slide_index} of {file_path}"
            success_msg += f" (resized to {new_width // 100}x{new_height // 100}mm, centered on slide)"
            logging.info(success_msg)
            return success_msg


def safe_execute(operation_name, handler_func, command):
    """Execute a function with consistent error handling and logging."""
    try:
        logging.info(f"Starting {operation_name}")
        result = handler_func(command)
        logging.info(f"Successfully completed {operation_name}")
        return result
    except HelperError as e:
        # Pass through HelperError messages directly
        logging.error(str(e))
        logging.error(traceback.format_exc())
        raise
    except Exception as e:
        error_msg = f"Error in {operation_name}: {str(e)}"
        logging.error(error_msg)
        logging.error(traceback.format_exc())
        raise HelperError(error_msg)


# Command handler mapping
COMMAND_HANDLERS = {
    # Document creation and management
    "create_document": lambda cmd: create_document(
        cmd.get("doc_type", "text"), cmd.get("file_path", ""), cmd.get("metadata", None)
    ),
    "read_text_document": lambda cmd: extract_text(cmd.get("file_path", "")),
    "get_document_properties": lambda cmd: get_document_properties(
        cmd.get("file_path", "")
    ),
    "list_documents": lambda cmd: list_documents(cmd.get("directory", "")),
    "copy_document": lambda cmd: copy_document(
        cmd.get("source_path", ""), cmd.get("target_path", "")
    ),
    # Impress presentation creation and management
    "add_slide": lambda cmd: add_slide(
        cmd.get("file_path", ""),
        cmd.get("slide_index", None),
        cmd.get("title", None),
        cmd.get("content", None),
    ),
    "edit_slide_content": lambda cmd: edit_slide_content(
        cmd.get("file_path", ""), cmd.get("slide_index", 0), cmd.get("new_content", "")
    ),
    "edit_slide_title": lambda cmd: edit_slide_title(
        cmd.get("file_path", ""), cmd.get("slide_index", 0), cmd.get("new_title", "")
    ),
    "delete_slide": lambda cmd: delete_slide(
        cmd.get("file_path", ""), cmd.get("slide_index", 0)
    ),
    "read_presentation": lambda cmd: extract_impress_text(cmd.get("file_path", "")),
    "apply_presentation_template": lambda cmd: apply_presentation_template(
        cmd.get("file_path", ""), cmd.get("template_name", "")
    ),
    "format_slide_content": lambda cmd: format_slide_content(
        cmd.get("file_path", ""),
        cmd.get("slide_index", 0),
        cmd.get("format_options", {}),
    ),
    "format_slide_title": lambda cmd: format_slide_title(
        cmd.get("file_path", ""),
        cmd.get("slide_index", 0),
        cmd.get("format_options", {}),
    ),
    "insert_slide_image": lambda cmd: insert_slide_image(
        cmd.get("file_path", ""),
        cmd.get("slide_index", 0),
        cmd.get("image_path", ""),
        cmd.get("max_width", None),
        cmd.get("max_height", None),
        cmd.get("img_width_px", None),
        cmd.get("img_height_px", None),
        cmd.get("dpi", 96),
    ),
    # Writer content creation
    "add_text": lambda cmd: add_text(
        cmd.get("file_path", ""), cmd.get("text", ""), cmd.get("position", "end")
    ),
    "add_heading": lambda cmd: add_heading(
        cmd.get("file_path", ""), cmd.get("text", ""), cmd.get("level", 1)
    ),
    "add_paragraph": lambda cmd: add_paragraph(
        cmd.get("file_path", ""),
        cmd.get("text", ""),
        cmd.get("style", None),
        cmd.get("alignment", None),
    ),
    "add_table": lambda cmd: add_table(
        cmd.get("file_path", ""),
        cmd.get("rows", 2),
        cmd.get("columns", 2),
        cmd.get("data", None),
        cmd.get("header_row", False),
    ),
    "insert_image": lambda cmd: insert_image(
        cmd.get("file_path", ""),
        cmd.get("image_path", ""),
        cmd.get("width", None),
        cmd.get("height", None),
    ),
    "insert_page_break": lambda cmd: insert_page_break(cmd.get("file_path", "")),
    # Text formatting
    "format_text": lambda cmd: format_text(
        cmd.get("file_path", ""),
        cmd.get("text_to_find", ""),
        {
            "bold": cmd.get("bold", False),
            "italic": cmd.get("italic", False),
            "underline": cmd.get("underline", False),
            "color": cmd.get("color", None),
            "font": cmd.get("font", None),
            "size": cmd.get("size", None),
        },
    ),
    "search_replace_text": lambda cmd: search_replace_text(
        cmd.get("file_path", ""),
        cmd.get("search_text", ""),
        cmd.get("replace_text", ""),
    ),
    "delete_text": lambda cmd: delete_text(
        cmd.get("file_path", ""), cmd.get("text_to_delete", "")
    ),
    # Table formatting
    "format_table": lambda cmd: format_table(
        cmd.get("file_path", ""),
        cmd.get("table_index", 0),
        cmd.get("format_options", {}),
    ),
    # Advanced document manipulation
    # "create_custom_style": lambda cmd: create_custom_style(
    #     cmd.get("file_path", ""),
    #     cmd.get("style_name", "CustomStyle"),
    #     cmd.get("style_properties", {})
    # ),
    "delete_paragraph": lambda cmd: delete_paragraph(
        cmd.get("file_path", ""), cmd.get("paragraph_index", 0)
    ),
    "apply_document_style": lambda cmd: apply_document_style(
        cmd.get("file_path", ""), cmd.get("style", {})
    ),
    # Testing functions
    "get_text_formatting": lambda cmd: get_text_formatting(
        cmd.get("file_path", ""), cmd.get("text_to_find", "")
    ),
    "get_table_info": lambda cmd: get_table_info(
        cmd.get("file_path", ""), cmd.get("table_index", 0)
    ),
    "has_image": lambda cmd: has_image(cmd.get("file_path", "")),
    "get_page_break_info": lambda cmd: get_page_break_info(cmd.get("file_path", "")),
    "get_presentation_template_info": lambda cmd: get_presentation_template_info(
        cmd.get("file_path", "")
    ),
    "get_presentation_text_formatting": lambda cmd: get_presentation_text_formatting(
        cmd.get("file_path", ""),
        cmd.get("text_to_find", ""),
        cmd.get("slide_index", None),
    ),
    "get_slide_image_info": lambda cmd: get_slide_image_info(
        cmd.get("file_path", ""), cmd.get("slide_index", 0)
    ),
    # System commands
    "ping": lambda cmd: "LibreOffice helper is running",
}


def handle_command(command):
    """Process commands from the MCP server using dictionary dispatch."""
    try:
        logging.info("handle_command called")
        action = command.get("action", "")
        logging.info(f"action: {action}")

        # Look up the handler function
        handler = COMMAND_HANDLERS.get(action)
        if handler:
            return safe_execute(action, handler, command)
        else:
            raise HelperError(f"Unknown action: {action}")

    except Exception as e:
        print(f"Error handling command: {str(e)}")
        print(traceback.format_exc())
        raise


# Main server loop
print("Starting command processing loop...")
try:
    while True:
        client_socket = None
        try:
            print("Waiting for connection...")
            logging.info("Waiting for connection...")

            # This can raise OSError if server socket is invalid
            client_socket, address = server_socket.accept()
            print(f"Connection from {address}")
            logging.info(f"Connection from {address}")

            # Set timeout for client operations
            client_socket.settimeout(30)

            # Receive data in chunks to handle large messages
            received_data = b""
            while True:
                try:
                    chunk = client_socket.recv(4096)  # Smaller chunk size
                    if not chunk:
                        break
                    received_data += chunk

                    # Check if we have a complete JSON message
                    try:
                        data_str = received_data.decode("utf-8")
                        json.loads(
                            data_str
                        )  # Try to parse - if successful, we have complete message
                        break
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Not complete yet, continue receiving
                        if len(received_data) > 65536:  # Prevent memory issues
                            raise Exception("Message too large")
                        continue

                except socket.timeout:
                    print("Timeout while receiving data")
                    logging.warning("Timeout while receiving data")
                    break
                except ConnectionResetError:
                    print("Client disconnected during receive")
                    logging.info("Client disconnected during receive")
                    break
                except Exception as recv_error:
                    print(f"Error receiving data: {recv_error}")
                    logging.error(f"Error receiving data: {recv_error}")
                    break

            if not received_data:
                print("No data received, closing connection")
                continue

            try:
                data_str = received_data.decode("utf-8")
                print(f"Received data: {data_str[:100]}...")
                logging.info(f"Received data: {data_str[:100]}...")
            except UnicodeDecodeError as decode_error:
                error_msg = f"Failed to decode received data: {decode_error}"
                print(error_msg)
                logging.error(error_msg)
                response = {"status": "error", "message": error_msg}
                try:
                    client_socket.send(json.dumps(response).encode("utf-8"))
                except:
                    pass
                continue

            # Parse and execute command
            try:
                command = json.loads(data_str)
                result = handle_command(command)
                response = {"status": "success", "message": result}

            except json.JSONDecodeError as json_error:
                error_msg = f"Invalid JSON received: {str(json_error)}"
                print(error_msg)
                logging.error(error_msg)
                response = {"status": "error", "message": error_msg}

            except HelperError as helper_error:
                error_msg = str(helper_error)
                print(f"Helper error: {error_msg}")
                logging.error(f"Helper error: {error_msg}")
                response = {"status": "error", "message": error_msg}

            except Exception as unexpected_error:
                error_msg = f"Unexpected error: {str(unexpected_error)}"
                print(error_msg)
                print(traceback.format_exc())
                logging.error(error_msg)
                logging.error(traceback.format_exc())
                response = {"status": "error", "message": error_msg}

            # Send response
            try:
                response_json = json.dumps(response)
                response_bytes = response_json.encode("utf-8")

                # Send response length first, then data
                length_header = len(response_bytes).to_bytes(4, byteorder="big")
                client_socket.send(length_header + response_bytes)
                print("Response sent")
                logging.info("Response sent")

            except ConnectionResetError:
                print("Client disconnected before response could be sent")
                logging.warning("Client disconnected before response could be sent")
            except BrokenPipeError:
                print("Broken pipe - client disconnected")
                logging.warning("Broken pipe - client disconnected")
            except Exception as send_error:
                print(f"Failed to send response: {send_error}")
                logging.error(f"Failed to send response: {send_error}")

        except socket.timeout:
            print("Server socket timeout")
            logging.warning("Server socket timeout")

        except ConnectionAbortedError:
            print("Connection aborted by client")
            logging.info("Connection aborted by client")

        except OSError as os_error:
            # Handle socket-related OS errors
            if os_error.errno == 22:  # Invalid argument
                print(f"Socket error (Invalid argument): {os_error}")
                logging.error(f"Socket error: {os_error}")
                # Try to recreate the server socket
                try:
                    server_socket.close()
                    print("Attempting to recreate server socket...")
                    logging.info("Attempting to recreate server socket...")

                    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    server_socket.bind(("localhost", 8765))
                    server_socket.listen(1)

                    print("Server socket recreated successfully")
                    logging.info("Server socket recreated successfully")
                    continue

                except Exception as recreate_error:
                    print(f"Failed to recreate server socket: {recreate_error}")
                    logging.fatal(f"Failed to recreate server socket: {recreate_error}")
                    break
            else:
                print(f"OS error in server loop: {os_error}")
                logging.error(f"OS error in server loop: {os_error}")

        except Exception as client_error:
            error_msg = f"Client connection error: {str(client_error)}"
            print(error_msg)
            logging.error(error_msg)
            logging.error(traceback.format_exc())

        finally:
            # Always close the client socket
            if client_socket:
                try:
                    client_socket.close()
                    print("Client connection closed")
                except Exception as close_error:
                    print(f"Error closing client socket: {close_error}")

except KeyboardInterrupt:
    print("Helper server shutting down...")
    logging.info("Helper server shutting down...")
except Exception as fatal_error:
    print(f"Fatal server error: {str(fatal_error)}")
    logging.fatal(f"Fatal server error: {str(fatal_error)}")
    print(traceback.format_exc())
    logging.fatal(traceback.format_exc())
finally:
    try:
        server_socket.close()
        print("Server socket closed")
        logging.info("Server socket closed")
    except Exception as final_close_error:
        print(f"Error closing server socket: {final_close_error}")
        logging.error(f"Error closing server socket: {final_close_error}")
