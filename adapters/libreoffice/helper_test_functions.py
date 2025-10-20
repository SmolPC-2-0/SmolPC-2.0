import logging
import json
import os
from helper_utils import managed_document, HelperError
from com.sun.star.awt.FontSlant import ITALIC
from com.sun.star.table import BorderLine2, TableBorder2
from com.sun.star.table.BorderLineStyle import SOLID


# Functions for testing
def get_text_formatting(file_path, text_to_find):
    """Get formatting information for specific text in a document."""
    with managed_document(file_path, read_only=True) as doc:
        if hasattr(doc, "getText"):
            search = doc.createSearchDescriptor()
            search.SearchString = text_to_find
            search.SearchCaseSensitive = False

            found = doc.findFirst(search)
            if not found:
                raise HelperError(f"Text '{text_to_find}' not found in document")

            # Extract formatting properties from the found text
            formatting_info = {}

            # Character formatting
            try:
                formatting_info["font_name"] = getattr(found, "CharFontName", "Unknown")
                formatting_info["font_size"] = getattr(found, "CharHeight", 0)

                # Bold (CharWeight: 100=normal, 150=bold)
                char_weight = getattr(found, "CharWeight", 100)
                formatting_info["bold"] = char_weight >= 150

                # Italic (CharPosture: 0=none, 2=italic)
                char_posture = getattr(found, "CharPosture", 0)
                # Compare directly with the ITALIC constant
                formatting_info["italic"] = char_posture == ITALIC

                # Underline (CharUnderline: 0=none, 1=single, etc.)
                char_underline = getattr(found, "CharUnderline", 0)
                formatting_info["underline"] = char_underline > 0

                # Text color
                char_color = getattr(found, "CharColor", 0)
                formatting_info["color"] = (
                    f"#{char_color:06X}" if char_color > 0 else "#000000"
                )

                # Background color
                char_back_color = getattr(found, "CharBackColor", -1)
                if char_back_color != -1:
                    formatting_info["background_color"] = f"#{char_back_color:06X}"
                else:
                    formatting_info["background_color"] = "transparent"

            except Exception as char_error:
                logging.warning(f"Error reading character formatting: {char_error}")

            # Paragraph formatting
            try:
                # Alignment - convert enum to string
                para_adjust = getattr(found, "ParaAdjust", None)
                if para_adjust is not None:
                    # Convert the enum value to its numeric value first, then to string
                    try:
                        adjust_value = int(para_adjust)
                        alignment_map = {
                            0: "left",  # LEFT
                            1: "right",  # RIGHT
                            2: "block",  # BLOCK
                            3: "center",  # CENTER
                            4: "stretch",  # STRETCH
                        }
                        formatting_info["alignment"] = alignment_map.get(
                            adjust_value, f"unknown({adjust_value})"
                        )
                    except (ValueError, TypeError):
                        formatting_info["alignment"] = "unknown"

                # Line spacing
                para_line_spacing = getattr(found, "ParaLineSpacing", None)
                if para_line_spacing and hasattr(para_line_spacing, "Height"):
                    # Height is in percentage (100 = single spacing)
                    spacing_value = para_line_spacing.Height / 100.0
                    formatting_info["line_spacing"] = spacing_value
                else:
                    formatting_info["line_spacing"] = 1.0

                # Paragraph margins
                formatting_info["left_margin"] = getattr(found, "ParaLeftMargin", 0)
                formatting_info["right_margin"] = getattr(found, "ParaRightMargin", 0)
                formatting_info["top_margin"] = getattr(found, "ParaTopMargin", 0)
                formatting_info["bottom_margin"] = getattr(found, "ParaBottomMargin", 0)

                # First line indent
                formatting_info["first_line_indent"] = getattr(
                    found, "ParaFirstLineIndent", 0
                )

            except Exception as para_error:
                logging.warning(f"Error reading paragraph formatting: {para_error}")

            # Style information
            try:
                formatting_info["paragraph_style"] = getattr(
                    found, "ParaStyleName", "Standard"
                )
                formatting_info["character_style"] = getattr(found, "CharStyleName", "")

            except Exception as style_error:
                logging.warning(f"Error reading style information: {style_error}")

            # Additional properties
            try:
                # Strikethrough
                char_strikeout = getattr(found, "CharStrikeout", 0)
                formatting_info["strikethrough"] = char_strikeout > 0

                # Superscript/Subscript
                char_escapement = getattr(found, "CharEscapement", 0)
                if char_escapement > 0:
                    formatting_info["script"] = "superscript"
                elif char_escapement < 0:
                    formatting_info["script"] = "subscript"
                else:
                    formatting_info["script"] = "normal"

                # Font style (italic alternative) - convert to numeric value
                font_slant = getattr(found, "CharPosture", 0)
                try:
                    formatting_info["font_slant"] = int(font_slant)
                except (ValueError, TypeError):
                    formatting_info["font_slant"] = 0

                # Character scaling
                formatting_info["char_scale_width"] = getattr(
                    found, "CharScaleWidth", 100
                )

            except Exception as additional_error:
                logging.warning(
                    f"Error reading additional formatting: {additional_error}"
                )

            # Count occurrences
            occurrence_count = 0
            current_found = found
            while current_found:
                occurrence_count += 1
                current_found = doc.findNext(current_found.End, search)

            formatting_info["occurrences_found"] = occurrence_count
            formatting_info["search_text"] = text_to_find

            return json.dumps(formatting_info, indent=2)

        else:
            raise HelperError("Document does not support text formatting retrieval")


def get_table_info(file_path, table_index=0):
    """Get detailed information about a table in a document."""
    with managed_document(file_path, read_only=True) as doc:
        if not hasattr(doc, "getTextTables"):
            raise HelperError("Document does not support tables")

        tables = doc.getTextTables()
        table_count = tables.getCount()

        if table_count == 0:
            raise HelperError("No tables found in document")

        if table_index < 0 or table_index >= table_count:
            raise HelperError(
                f"Table index {table_index} is out of range (document has {table_count} tables)"
            )

        table = tables.getByIndex(table_index)

        # Get table dimensions
        rows = table.getRows()
        columns = table.getColumns()
        row_count = rows.getCount()
        column_count = columns.getCount()

        # Extract table data
        table_data = []
        for row_idx in range(row_count):
            row_data = []
            for col_idx in range(column_count):
                try:
                    cell_name = chr(65 + col_idx) + str(row_idx + 1)  # A1, B1, etc.
                    cell = table.getCellByName(cell_name)
                    cell_text = (
                        cell.getText().getString() if hasattr(cell, "getText") else ""
                    )
                    row_data.append(cell_text)
                except Exception as cell_error:
                    logging.warning(f"Error reading cell: {cell_error}")
                    row_data.append("")
            table_data.append(row_data)

        # Get table formatting information
        table_info = {
            "table_index": table_index,
            "rows": row_count,
            "columns": column_count,
            "data": table_data,
            "total_tables": table_count,
        }

        # Get table border information with enhanced debugging
        try:
            # Check both TableBorder2 and TableBorder properties for comparison
            border_info = None
            border_source = "none"

            if hasattr(table, "TableBorder2"):
                border_info = table.TableBorder2
                border_source = "TableBorder2"
                logging.info("Reading borders from TableBorder2 property")
            elif hasattr(table, "TableBorder"):
                border_info = table.TableBorder
                border_source = "TableBorder"
                logging.info("Reading borders from TableBorder property")

            table_info["border_source"] = border_source

            if border_info:
                # Extract border line widths with detailed logging
                border_widths = {}

                # Log the border_info object for debugging
                logging.info(f"Border info object: {border_info}")

                # Check each border line with detailed logging
                if hasattr(border_info, "TopLine") and border_info.TopLine:
                    top_width = border_info.TopLine.LineWidth
                    logging.info(f"TopLine.LineWidth: {top_width}")
                    border_widths["top"] = top_width
                else:
                    logging.info("TopLine is None or missing")
                    border_widths["top"] = 0

                if hasattr(border_info, "BottomLine") and border_info.BottomLine:
                    bottom_width = border_info.BottomLine.LineWidth
                    logging.info(f"BottomLine.LineWidth: {bottom_width}")
                    border_widths["bottom"] = bottom_width
                else:
                    logging.info("BottomLine is None or missing")
                    border_widths["bottom"] = 0

                if hasattr(border_info, "LeftLine") and border_info.LeftLine:
                    left_width = border_info.LeftLine.LineWidth
                    logging.info(f"LeftLine.LineWidth: {left_width}")
                    border_widths["left"] = left_width
                else:
                    logging.info("LeftLine is None or missing")
                    border_widths["left"] = 0

                if hasattr(border_info, "RightLine") and border_info.RightLine:
                    right_width = border_info.RightLine.LineWidth
                    logging.info(f"RightLine.LineWidth: {right_width}")
                    border_widths["right"] = right_width
                else:
                    logging.info("RightLine is None or missing")
                    border_widths["right"] = 0

                if (
                    hasattr(border_info, "HorizontalLine")
                    and border_info.HorizontalLine
                ):
                    horizontal_width = border_info.HorizontalLine.LineWidth
                    logging.info(f"HorizontalLine.LineWidth: {horizontal_width}")
                    border_widths["horizontal"] = horizontal_width
                else:
                    logging.info("HorizontalLine is None or missing")
                    border_widths["horizontal"] = 0

                if hasattr(border_info, "VerticalLine") and border_info.VerticalLine:
                    vertical_width = border_info.VerticalLine.LineWidth
                    logging.info(f"VerticalLine.LineWidth: {vertical_width}")
                    border_widths["vertical"] = vertical_width
                else:
                    logging.info("VerticalLine is None or missing")
                    border_widths["vertical"] = 0

                table_info["border_widths"] = border_widths

                # Log the final border_widths for debugging
                logging.info(f"Final border_widths: {border_widths}")

                # Check if table has any borders
                has_borders = any(width > 0 for width in border_widths.values())
                table_info["has_borders"] = has_borders

                # Get maximum border width
                table_info["max_border_width"] = (
                    max(border_widths.values()) if border_widths.values() else 0
                )

                # Get border styles if available
                border_styles = {}
                if hasattr(border_info, "TopLine") and border_info.TopLine:
                    border_styles["top"] = getattr(
                        border_info.TopLine, "LineStyle", "unknown"
                    )
                if hasattr(border_info, "BottomLine") and border_info.BottomLine:
                    border_styles["bottom"] = getattr(
                        border_info.BottomLine, "LineStyle", "unknown"
                    )
                if hasattr(border_info, "LeftLine") and border_info.LeftLine:
                    border_styles["left"] = getattr(
                        border_info.LeftLine, "LineStyle", "unknown"
                    )
                if hasattr(border_info, "RightLine") and border_info.RightLine:
                    border_styles["right"] = getattr(
                        border_info.RightLine, "LineStyle", "unknown"
                    )

                table_info["border_styles"] = border_styles

            else:
                table_info["has_borders"] = False
                table_info["border_widths"] = {
                    "top": 0,
                    "bottom": 0,
                    "left": 0,
                    "right": 0,
                    "horizontal": 0,
                    "vertical": 0,
                }
                table_info["max_border_width"] = 0

        except Exception as border_error:
            logging.warning(f"Error reading table border properties: {border_error}")
            table_info["border_error"] = str(border_error)
            table_info["has_borders"] = False

        # Get other table properties
        try:
            if hasattr(table, "BackColor"):
                table_info["background_color"] = (
                    f"#{table.BackColor:06X}"
                    if table.BackColor != -1
                    else "transparent"
                )

            if hasattr(table, "Width"):
                table_info["width"] = table.Width

        except Exception as prop_error:
            logging.warning(f"Error reading table properties: {prop_error}")

        return json.dumps(table_info, indent=2)


def has_image(file_path):
    """Check if a document contains at least one image and get dimensions of the first image."""
    with managed_document(file_path, read_only=True) as doc:
        if not hasattr(doc, "getGraphicObjects"):
            raise HelperError("Document does not support graphics/images")

        graphic_objects = doc.getGraphicObjects()
        image_count = graphic_objects.getCount()

        result = {"has_image": image_count > 0, "image_count": image_count}

        # If there's at least one image, get dimensions of the first one
        if image_count > 0:
            try:
                first_image = graphic_objects.getByIndex(0)
                if hasattr(first_image, "Size"):
                    size = first_image.Size
                    result["first_image_width"] = size.Width
                    result["first_image_height"] = size.Height
                    # Also provide dimensions in mm for convenience
                    result["first_image_width_mm"] = size.Width / 100.0
                    result["first_image_height_mm"] = size.Height / 100.0
                else:
                    result["first_image_width"] = None
                    result["first_image_height"] = None
            except Exception as e:
                logging.warning(f"Error reading first image dimensions: {e}")
                result["first_image_width"] = None
                result["first_image_height"] = None

        return json.dumps(result, indent=2)


def get_page_break_info(file_path):
    """Get information about page breaks in a document."""
    with managed_document(file_path, read_only=True) as doc:
        if not hasattr(doc, "getText"):
            raise HelperError("Document does not support text content")

        text = doc.getText()

        # Method 1: Check paragraphs for BreakType property
        text_enum = text.createEnumeration()
        page_break_count = 0
        paragraph_details = []

        paragraph_index = 0
        while text_enum.hasMoreElements():
            paragraph = text_enum.nextElement()
            paragraph_info = {
                "index": paragraph_index,
                "has_break": False,
                "break_type": None,
            }

            try:
                if hasattr(paragraph, "BreakType"):
                    break_type = paragraph.BreakType
                    paragraph_info["break_type"] = str(break_type)

                    # Handle different ways the enum might be represented
                    if hasattr(break_type, "value"):
                        break_value = break_type.value
                    else:
                        # Convert string representation to check for page break types
                        break_str = str(break_type).upper()
                        if "PAGE_BEFORE" in break_str:
                            break_value = "PAGE_BEFORE"
                        elif "PAGE_AFTER" in break_str:
                            break_value = "PAGE_AFTER"
                        elif "PAGE_BOTH" in break_str:
                            break_value = "PAGE_BOTH"
                        else:
                            break_value = "NONE"

                    paragraph_info["break_value"] = break_value

                    # Check for any page break type
                    if break_value in ["PAGE_BEFORE", "PAGE_AFTER", "PAGE_BOTH"]:
                        page_break_count += 1
                        paragraph_info["has_break"] = True

                # Also check the paragraph text content
                if hasattr(paragraph, "getString"):
                    para_text = paragraph.getString()
                    paragraph_info["text"] = (
                        para_text[:50] + "..." if len(para_text) > 50 else para_text
                    )
                    paragraph_info["length"] = len(para_text)

            except Exception as e:
                paragraph_info["error"] = str(e)
                logging.debug(f"Error checking paragraph {paragraph_index}: {e}")

            paragraph_details.append(paragraph_info)
            paragraph_index += 1

        # Method 2: Check for manual page breaks (form feed characters)
        text_content = text.getString()
        manual_breaks = text_content.count("\x0c")  # Form feed character

        # Method 3: Try to get actual page count from view
        estimated_pages = None
        try:
            if hasattr(doc, "getCurrentController"):
                controller = doc.getCurrentController()
                if hasattr(controller, "getPageCount"):
                    estimated_pages = controller.getPageCount()
        except Exception as e:
            logging.debug(f"Could not get page count: {e}")

        result = {
            "paragraph_page_breaks": page_break_count,
            "manual_page_breaks": manual_breaks,
            "total_page_breaks": page_break_count + manual_breaks,
            "estimated_page_count": estimated_pages,
            "total_paragraphs": len(paragraph_details),
            "paragraph_details": paragraph_details,
            "text_length": len(text_content),
            "contains_form_feed": "\x0c" in text_content,
            "debug_text_sample": text_content[:200] + "..."
            if len(text_content) > 200
            else text_content,
        }

        return json.dumps(result, indent=2)


def get_presentation_template_info(file_path):
    """Get the name of the template used by a presentation."""
    with managed_document(file_path, read_only=True) as doc:
        if not hasattr(doc, "getDrawPages"):
            raise HelperError("Document does not support slides/pages")

        template_info = {
            "template_name": None,
            "master_slide_name": None,
            "template_path": None,
        }

        # Check document properties for template info
        try:
            if hasattr(doc, "DocumentProperties"):
                doc_props = doc.DocumentProperties
                if hasattr(doc_props, "TemplateName") and doc_props.TemplateName:
                    template_info["template_name"] = doc_props.TemplateName
                if hasattr(doc_props, "TemplateURL") and doc_props.TemplateURL:
                    template_info["template_path"] = doc_props.TemplateURL
        except Exception as e:
            logging.warning(f"Error reading document properties: {e}")

        # Get master slide name as potential template indicator
        try:
            if hasattr(doc, "getMasterPages"):
                master_pages = doc.getMasterPages()
                if master_pages.getCount() > 0:
                    master_slide = master_pages.getByIndex(0)
                    if hasattr(master_slide, "Name") and master_slide.Name:
                        template_info["master_slide_name"] = master_slide.Name
        except Exception as e:
            logging.warning(f"Error reading master slide: {e}")

        # Return the most likely template name
        template_name = (
            template_info["template_name"]
            or template_info["master_slide_name"]
            or "Default"
        )

        return f"Template: {template_name}"


def get_presentation_text_formatting(file_path, text_to_find, slide_index=None):
    """Get formatting information for specific text in a presentation."""
    with managed_document(file_path, read_only=True) as doc:
        if not hasattr(doc, "getDrawPages"):
            raise HelperError("Document does not support slides/pages")

        draw_pages = doc.getDrawPages()
        slide_count = draw_pages.getCount()

        if slide_count == 0:
            raise HelperError("No slides found in presentation")

        # If slide_index is specified, search only that slide
        if slide_index is not None:
            if slide_index < 0 or slide_index >= slide_count:
                raise HelperError(
                    f"Slide index {slide_index} is out of range (presentation has {slide_count} slides)"
                )
            slides_to_search = [slide_index]
        else:
            # Search all slides
            slides_to_search = range(slide_count)

        # Search for text across specified slides
        found_text_object = None
        found_slide_index = None
        found_shape_index = None
        found_shape_type = None

        for slide_idx in slides_to_search:
            slide = draw_pages.getByIndex(slide_idx)

            # Check each shape on the slide
            if hasattr(slide, "getCount"):
                shape_count = slide.getCount()

                for shape_idx in range(shape_count):
                    try:
                        shape = slide.getByIndex(shape_idx)
                        shape_type = shape.getShapeType()

                        # Check if shape contains text
                        if hasattr(shape, "getText"):
                            text_obj = shape.getText()
                            if text_obj:
                                # Get the full text content as string
                                text_content = text_obj.getString()

                                # Check if our search text is in this shape's content
                                if text_to_find.lower() in text_content.lower():
                                    found_text_object = text_obj
                                    found_slide_index = slide_idx
                                    found_shape_index = shape_idx
                                    found_shape_type = shape_type
                                    break

                    except Exception as shape_error:
                        logging.warning(
                            f"Error searching shape {shape_idx} on slide {slide_idx}: {shape_error}"
                        )
                        continue

                if found_text_object:
                    break

        if not found_text_object:
            raise HelperError(
                f"Text '{text_to_find}' not found in presentation"
                + (f" slide {slide_index}" if slide_index is not None else "")
            )

        # Extract formatting properties from the found text object
        formatting_info = {
            "search_text": text_to_find,
            "found_on_slide": found_slide_index,
            "found_in_shape": found_shape_index,
            "shape_type": found_shape_type,
        }

        # Determine if this is likely a title or content shape
        shape_category = "unknown"
        if found_shape_type and "Title" in found_shape_type:
            shape_category = "title"
        elif found_shape_type and (
            "Outliner" in found_shape_type or "Text" in found_shape_type
        ):
            shape_category = "content"
        formatting_info["shape_category"] = shape_category

        # Try to get formatting from the text object using the same method as format_slide_content
        text_to_format = found_text_object

        # Try to create a text cursor like format_slide_content does
        try:
            if hasattr(found_text_object, "createTextCursor"):
                text_cursor = found_text_object.createTextCursor()
                text_cursor.gotoStart(False)
                text_cursor.gotoEnd(
                    True
                )  # Select all text like format_slide_content does
                text_to_format = text_cursor
                logging.info(
                    "Using text cursor for formatting detection (matching format_slide_content method)"
                )
        except Exception as cursor_error:
            logging.warning(f"Could not create text cursor: {cursor_error}")

            # Fallback: Try to get the first paragraph for more specific formatting
            try:
                if hasattr(found_text_object, "createEnumeration"):
                    text_enum = found_text_object.createEnumeration()
                    if text_enum.hasMoreElements():
                        first_paragraph = text_enum.nextElement()
                        if first_paragraph:
                            # Try to get text portions within the paragraph for more specific formatting
                            if hasattr(first_paragraph, "createEnumeration"):
                                portion_enum = first_paragraph.createEnumeration()
                                if portion_enum.hasMoreElements():
                                    first_portion = portion_enum.nextElement()
                                    if first_portion:
                                        text_to_format = first_portion
                            else:
                                text_to_format = first_paragraph
            except Exception as enum_error:
                logging.warning(f"Could not get paragraph enumeration: {enum_error}")

        # Character formatting
        try:
            formatting_info["font_name"] = getattr(
                text_to_format, "CharFontName", "Unknown"
            )
            formatting_info["font_size"] = getattr(text_to_format, "CharHeight", 0)

            # Bold (CharWeight: 100=normal, 150=bold)
            char_weight = getattr(text_to_format, "CharWeight", 100)
            formatting_info["bold"] = char_weight >= 150

            # Italic (CharPosture: 0=none, 2=italic)
            char_posture = getattr(text_to_format, "CharPosture", 0)
            formatting_info["italic"] = (
                char_posture == 2
            )  # Use numeric value like in format functions

            # Underline (CharUnderline: 0=none, 1=single, etc.)
            char_underline = getattr(text_to_format, "CharUnderline", 0)
            formatting_info["underline"] = char_underline > 0

            # Text color
            char_color = getattr(text_to_format, "CharColor", 0)
            formatting_info["color"] = (
                f"#{char_color:06X}" if char_color > 0 else "#000000"
            )

            # Background color
            char_back_color = getattr(text_to_format, "CharBackColor", -1)
            if char_back_color != -1:
                formatting_info["background_color"] = f"#{char_back_color:06X}"
            else:
                formatting_info["background_color"] = "transparent"

        except Exception as char_error:
            logging.warning(f"Error reading character formatting: {char_error}")

        # Paragraph formatting
        try:
            # Alignment - convert enum to string (matching format functions)
            para_adjust = getattr(text_to_format, "ParaAdjust", None)
            if para_adjust is not None:
                try:
                    adjust_value = int(para_adjust)
                    alignment_map = {
                        0: "left",  # LEFT
                        1: "right",  # RIGHT
                        2: "block",  # BLOCK
                        3: "center",  # CENTER
                        4: "stretch",  # STRETCH
                    }
                    formatting_info["alignment"] = alignment_map.get(
                        adjust_value, f"unknown({adjust_value})"
                    )
                except (ValueError, TypeError):
                    formatting_info["alignment"] = "unknown"

            # Line spacing
            para_line_spacing = getattr(text_to_format, "ParaLineSpacing", None)
            if para_line_spacing and hasattr(para_line_spacing, "Height"):
                spacing_value = para_line_spacing.Height / 100.0
                formatting_info["line_spacing"] = spacing_value
            else:
                formatting_info["line_spacing"] = 1.0

            # Paragraph margins/indents
            formatting_info["left_margin"] = getattr(
                text_to_format, "ParaLeftMargin", 0
            )
            formatting_info["right_margin"] = getattr(
                text_to_format, "ParaRightMargin", 0
            )
            formatting_info["top_margin"] = getattr(text_to_format, "ParaTopMargin", 0)
            formatting_info["bottom_margin"] = getattr(
                text_to_format, "ParaBottomMargin", 0
            )
            formatting_info["first_line_indent"] = getattr(
                text_to_format, "ParaFirstLineIndent", 0
            )

        except Exception as para_error:
            logging.warning(f"Error reading paragraph formatting: {para_error}")

        # Style information
        try:
            formatting_info["paragraph_style"] = getattr(
                text_to_format, "ParaStyleName", "Standard"
            )
            formatting_info["character_style"] = getattr(
                text_to_format, "CharStyleName", ""
            )

        except Exception as style_error:
            logging.warning(f"Error reading style information: {style_error}")

        # Additional presentation-specific properties
        try:
            # Strikethrough
            char_strikeout = getattr(text_to_format, "CharStrikeout", 0)
            formatting_info["strikethrough"] = char_strikeout > 0

            # Superscript/Subscript
            char_escapement = getattr(text_to_format, "CharEscapement", 0)
            if char_escapement > 0:
                formatting_info["script"] = "superscript"
            elif char_escapement < 0:
                formatting_info["script"] = "subscript"
            else:
                formatting_info["script"] = "normal"

            # Character scaling
            formatting_info["char_scale_width"] = getattr(
                text_to_format, "CharScaleWidth", 100
            )

        except Exception as additional_error:
            logging.warning(f"Error reading additional formatting: {additional_error}")

        # Count total occurrences across all slides
        try:
            total_occurrences = 0
            for slide_idx in range(slide_count):
                slide = draw_pages.getByIndex(slide_idx)
                if hasattr(slide, "getCount"):
                    shape_count = slide.getCount()
                    for shape_idx in range(shape_count):
                        try:
                            shape = slide.getByIndex(shape_idx)
                            if hasattr(shape, "getText"):
                                text_obj = shape.getText()
                                if text_obj:
                                    text_content = text_obj.getString()
                                    total_occurrences += text_content.lower().count(
                                        text_to_find.lower()
                                    )
                        except Exception:
                            continue

            formatting_info["total_occurrences"] = total_occurrences

        except Exception as count_error:
            logging.warning(f"Error counting occurrences: {count_error}")
            formatting_info["total_occurrences"] = 1

        # Add the actual text content found for debugging
        try:
            formatting_info["full_text_content"] = found_text_object.getString()
        except Exception:
            formatting_info["full_text_content"] = "Could not retrieve text content"

        return json.dumps(formatting_info, indent=2)


def get_slide_image_info(file_path, slide_index):
    """Check if a specific slide contains images and get information about them."""
    with managed_document(file_path, read_only=True) as doc:
        if not hasattr(doc, "getDrawPages"):
            raise HelperError("Document does not support slides/pages")

        draw_pages = doc.getDrawPages()
        slide_count = draw_pages.getCount()

        if slide_count == 0:
            raise HelperError("No slides found in presentation")

        if slide_index < 0 or slide_index >= slide_count:
            raise HelperError(
                f"Slide index {slide_index} is out of range (presentation has {slide_count} slides)"
            )

        target_slide = draw_pages.getByIndex(slide_index)

        result = {
            "slide_index": slide_index,
            "has_images": False,
            "image_count": 0,
            "images": [],
            "total_slides": slide_count,
        }

        # Check all shapes on the slide for images
        shape_count = target_slide.getCount()

        for shape_idx in range(shape_count):
            try:
                shape = target_slide.getByIndex(shape_idx)
                shape_type = shape.getShapeType()

                # Check if this is a graphic/image shape (same check as insert_slide_image)
                if shape_type == "com.sun.star.drawing.GraphicObjectShape":
                    image_info = {
                        "shape_index": shape_idx,
                        "shape_type": shape_type,
                        "width": None,
                        "height": None,
                        "width_mm": None,
                        "height_mm": None,
                        "position_x": None,
                        "position_y": None,
                        "position_x_mm": None,
                        "position_y_mm": None,
                        "graphic_url": None,
                        "filename": None,
                    }

                    # Get image dimensions (same method as insert_slide_image)
                    try:
                        if hasattr(shape, "getSize"):
                            size = shape.getSize()
                            image_info["width"] = size.Width  # 1/100mm units
                            image_info["height"] = size.Height  # 1/100mm units
                            # Convert to mm for convenience
                            image_info["width_mm"] = size.Width / 100.0
                            image_info["height_mm"] = size.Height / 100.0
                    except Exception as size_error:
                        logging.warning(f"Error reading image size: {size_error}")

                    # Get image position (same method as insert_slide_image)
                    try:
                        if hasattr(shape, "getPosition"):
                            position = shape.getPosition()
                            image_info["position_x"] = position.X  # 1/100mm units
                            image_info["position_y"] = position.Y  # 1/100mm units
                            # Convert to mm for convenience
                            image_info["position_x_mm"] = position.X / 100.0
                            image_info["position_y_mm"] = position.Y / 100.0
                    except Exception as pos_error:
                        logging.warning(f"Error reading image position: {pos_error}")

                    # Get graphic URL/source if available (fixed to handle None values)
                    try:
                        if hasattr(shape, "GraphicURL"):
                            graphic_url = shape.GraphicURL
                            if graphic_url and isinstance(graphic_url, str):
                                image_info["graphic_url"] = graphic_url
                                # Try to extract just the filename for readability
                                if graphic_url.startswith("file://"):
                                    try:
                                        import urllib.parse

                                        file_path_from_url = urllib.parse.unquote(
                                            graphic_url[7:]
                                        )
                                        image_info["filename"] = os.path.basename(
                                            file_path_from_url
                                        )
                                    except Exception as parse_error:
                                        logging.warning(
                                            f"Error parsing file URL: {parse_error}"
                                        )
                                        image_info["filename"] = "unknown"
                                else:
                                    # For non-file URLs or embedded images
                                    image_info["filename"] = "embedded_or_unknown"
                    except Exception as url_error:
                        logging.warning(f"Error reading graphic URL: {url_error}")

                    # Check if image is centered on slide (same logic as insert_slide_image)
                    try:
                        if (
                            image_info["position_x"] is not None
                            and image_info["position_y"] is not None
                            and image_info["width"] is not None
                            and image_info["height"] is not None
                        ):
                            # Get slide dimensions (using same defaults and methods as insert_slide_image)
                            slide_width = 25400  # Standard slide width in 1/100mm
                            slide_height = 19050  # Standard slide height in 1/100mm

                            try:
                                # Method 1: Try to get slide dimensions from the master page
                                if hasattr(target_slide, "getMasterPage"):
                                    master_page = target_slide.getMasterPage()
                                    if hasattr(master_page, "Width") and hasattr(
                                        master_page, "Height"
                                    ):
                                        slide_width = master_page.Width
                                        slide_height = master_page.Height

                                # Method 2: Try to get from the document's draw page size
                                elif hasattr(doc, "getDrawPageSize"):
                                    page_size = doc.getDrawPageSize()
                                    slide_width = page_size.Width
                                    slide_height = page_size.Height

                            except Exception as slide_dim_error:
                                logging.warning(
                                    f"Could not get slide dimensions, using defaults: {slide_dim_error}"
                                )

                            # Calculate if image is centered (same calculation as insert_slide_image)
                            slide_center_x = slide_width // 2
                            slide_center_y = slide_height // 2
                            image_center_x = image_info["position_x"] + (
                                image_info["width"] // 2
                            )
                            image_center_y = image_info["position_y"] + (
                                image_info["height"] // 2
                            )

                            # Allow some tolerance for "centered" (within 5mm)
                            center_tolerance = 500  # 5mm in 1/100mm units
                            is_centered_x = (
                                abs(image_center_x - slide_center_x) <= center_tolerance
                            )
                            is_centered_y = (
                                abs(image_center_y - slide_center_y) <= center_tolerance
                            )

                            image_info["is_centered"] = is_centered_x and is_centered_y
                            image_info["is_centered_horizontally"] = is_centered_x
                            image_info["is_centered_vertically"] = is_centered_y

                            # Add slide dimensions for reference
                            image_info["slide_width"] = slide_width
                            image_info["slide_height"] = slide_height
                            image_info["slide_width_mm"] = slide_width / 100.0
                            image_info["slide_height_mm"] = slide_height / 100.0

                    except Exception as center_error:
                        logging.warning(
                            f"Error calculating image centering: {center_error}"
                        )

                    result["images"].append(image_info)
                    result["image_count"] += 1
                    result["has_images"] = True

            except Exception as shape_error:
                logging.warning(f"Error examining shape {shape_idx}: {shape_error}")
                continue

        return json.dumps(result, indent=2)
