#!/usr/bin/env python3
import os
import sys
from typing import Optional, List
import socket
import json
import logging
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
import time

log_path = os.path.join(os.path.dirname(__file__), "libre.log")
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# Extensions
writer_extensions = (
    ".odt",
    ".docx",
    ".dotx",
    ".xml",
    ".doc",
    ".dot",
    ".rtf",
    ".wpd",
)

impress_extensions = (
    ".odp",
    ".pptx",
    ".ppsx",
    ".ppmx",
    ".potx",
    ".pomx",
    ".ppt",
    ".pps",
    ".ppm",
    ".pot",
    ".pom",
)

# Global Queue and Thread Pool
request_queue = Queue()
response_dict = {}
response_lock = threading.Lock()
thread_pool = ThreadPoolExecutor(max_workers=1)


def queue_worker():
    """Worker function that processes requests from the queue sequentially"""
    while True:
        try:
            request_id, command = request_queue.get(timeout=1)

            # Process the request
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(30)  # 30 second timeout
                client_socket.connect(("localhost", 8765))

                logging.info(client_socket)

                # Send command
                request_data = json.dumps(command).encode("utf-8")
                client_socket.send(request_data)

                logging.info(request_data)

                # Receive response
                response_data = client_socket.recv(16384).decode("utf-8")
                client_socket.close()

                logging.info(response_data)

                if not response_data:
                    response = {
                        "status": "error",
                        "message": "Empty response from helper",
                    }
                else:
                    response = json.loads(response_data)

            except socket.timeout:
                response = {
                    "status": "error",
                    "message": "Connection to helper timed out",
                }
            except ConnectionRefusedError:
                response = {
                    "status": "error",
                    "message": "Connection refused. Is the helper script running?",
                }
            except Exception as e:
                response = {
                    "status": "error",
                    "message": f"Error communicating with helper: {str(e)}",
                }

            # Store the response
            with response_lock:
                response_dict[request_id] = response

            request_queue.task_done()
        except Empty:
            continue
        except Exception as e:
            logging.error(f"Queue worker error: {e}")


# Start the queue worker thread
queue_worker_thread = threading.Thread(target=queue_worker, daemon=True)
queue_worker_thread.start()


def get_image_size(image_path):
    """Get image size and DPI using PIL/Pillow."""
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            width, height = img.size

            # Get DPI information
            dpi = 96  # Default DPI
            try:
                if hasattr(img, "info") and "dpi" in img.info:
                    dpi_info = img.info["dpi"]
                    if isinstance(dpi_info, tuple):
                        dpi = dpi_info[0]  # Use horizontal DPI
                    else:
                        dpi = dpi_info
                    logging.info(f"Found image DPI: {dpi}")
                else:
                    logging.info(f"No DPI info found in image, using default: {dpi}")
            except Exception as dpi_error:
                logging.warning(f"Could not extract DPI info: {dpi_error}")
                dpi = 96  # Fallback to default

            return width, height, dpi  # Returns (width_px, height_px, dpi)

    except ImportError:
        logging.warning("PIL/Pillow not available")
        return None, None, None
    except Exception as e:
        logging.warning(f"Could not get image size using PIL: {e}")
        return None, None, None


# Helper function for directory management
def ensure_directory_exists(file_path: str) -> None:
    """Ensure the directory for a file exists, creating it if necessary."""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")
        except Exception as e:
            print(f"Failed to create directory {directory}: {str(e)}")
            raise


# Helper function to normalize file paths
def normalize_path(file_path: str) -> str:
    """Convert a relative path to an absolute path."""
    if not file_path:
        raise ValueError("Empty file path provided")

    # Expand user directory if path starts with ~
    if file_path.startswith("~"):
        file_path = os.path.expanduser(file_path)

    # Make absolute if relative
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)

    print(f"Normalized path: {file_path}")
    return file_path


# Function to communicate with the LibreOffice helper
async def call_libreoffice_helper(command: dict) -> dict:
    """
    Send a command to the LibreOffice helper process.

    Args:
        command: Dictionary with command details

    Returns:
        Dictionary with response from helper
    """
    try:
        logging.info("call_libreoffice_helper function called")

        # Generate unique request ID
        request_id = f"{time.time()}_{threading.get_ident()}"

        # Add request to queue
        request_queue.put((request_id, command))

        # Wait for response with timeout
        max_wait_time = 60
        wait_interval = 0.1
        waited_time = 0

        while waited_time < max_wait_time:
            with response_lock:
                if request_id in response_dict:
                    response = response_dict.pop(request_id)
                    logging.info(f"Got response for request {request_id}: {response}")
                    return response

            await asyncio.sleep(wait_interval)
            waited_time += wait_interval

        # Timeout occurred
        return {"status": "error", "message": "Request timed out in queue"}

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error queuing request: {str(e)}",
        }


# Now import MCP dependencies
try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    print(f"Dependency Import Error: {e}")
    print("Ensure you have installed:")
    print("- mcp[cli]")
    sys.exit(1)

# Initialize MCP server
mcp = FastMCP("libreoffice-server")


def get_default_document_path(filename: str) -> str:
    """Get the path to user's default Documents folder path on Windows plus the filename passed in"""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            # Use the actual GUID structure
            from uuid import UUID

            class GUID(ctypes.Structure):
                _fields_ = [
                    ("Data1", ctypes.c_ulong),
                    ("Data2", ctypes.c_ushort),
                    ("Data3", ctypes.c_ushort),
                    ("Data4", ctypes.c_ubyte * 8),
                ]

                def __init__(self, uuidstr):
                    uuid = UUID(uuidstr)
                    ctypes.Structure.__init__(self)
                    self.Data1 = uuid.time_low
                    self.Data2 = uuid.time_mid
                    self.Data3 = uuid.time_hi_version
                    self.Data4[:] = uuid.bytes[8:]

            SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
            SHGetKnownFolderPath.argtypes = [
                ctypes.POINTER(GUID),
                wintypes.DWORD,
                wintypes.HANDLE,
                ctypes.POINTER(ctypes.c_wchar_p),
            ]
            SHGetKnownFolderPath.restype = ctypes.HRESULT

            path_ptr = ctypes.c_wchar_p()
            guid = GUID("FDD39AD0-238F-46AF-ADB4-6C85480369C7")
            result = SHGetKnownFolderPath(
                ctypes.byref(guid), 0, 0, ctypes.byref(path_ptr)
            )
            if result == 0 and path_ptr.value:
                docs_path = path_ptr.value
                logging.info(f"Found default document path: {docs_path}")
                ctypes.windll.ole32.CoTaskMemFree(path_ptr)
                return os.path.join(docs_path, filename)
        except Exception as e:
            logging.error(f"Could not get Windows Documents folder: {e}")
    # Fallback for non-Windows or error
    docs_path = os.path.join(os.path.expanduser("~"), "Documents")
    return os.path.join(docs_path, filename)


# Document Management Tools


@mcp.tool()
async def create_blank_document(
    filename: str,
    title: str = "",
    author: str = "",
    subject: str = "",
    keywords: str = "",
) -> str:
    """
    Create a new LibreOffice Writer document.

    Args:
        filename: Name of the document to create
        title: Document title metadata
        author: Document author metadata
        subject: Document subject metadata
        keywords: Document keywords metadata (comma-separated)
    """
    try:
        # Check for supported file extensions
        if not filename.lower().endswith(writer_extensions):
            filename += ".odt"

        # If filename doesn't include a path, add default path
        if os.path.basename(filename) == filename:
            save_path = get_default_document_path(filename)
        else:
            save_path = filename

        # Normalize path
        save_path = normalize_path(save_path)
        print(f"Creating document at: {save_path}")

        # Prepare metadata if provided
        metadata = {}
        if title:
            metadata["Title"] = title
        if author:
            metadata["Author"] = author
        if subject:
            metadata["Subject"] = subject
        if keywords:
            # Split by comma and strip whitespace
            keywords_list = [k.strip() for k in keywords.split(",")]
            metadata["Keywords"] = keywords_list

        logging.info(save_path)
        logging.info(metadata)

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "create_document",
                "doc_type": "text",
                "file_path": save_path,
                "metadata": metadata,
            }
        )

        logging.info(response["status"])
        logging.info(response["message"])

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"

    except Exception as e:
        logging.error(f"Error in create_document: {str(e)}")
        return f"Failed to create document: {str(e)}"


@mcp.tool()
async def read_text_document(file_path: str) -> str:
    """
    Open and read a text document.

    Args:
        file_path: Path to the document
    """
    try:
        # Normalize path
        file_path = normalize_path(file_path)

        # Send command to helper
        response = await call_libreoffice_helper(
            {"action": "read_text_document", "file_path": file_path}
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in open_text_document: {str(e)}")
        return f"Failed to open document: {str(e)}"


@mcp.tool()
async def get_document_properties(file_path: str) -> str:
    """
    Get document properties and statistics, including author, description, keywords, word count, etc.

    Args:
        file_path: Path to the document
    """
    try:
        # Normalize path
        file_path = normalize_path(file_path)

        # Send command to helper
        response = await call_libreoffice_helper(
            {"action": "get_document_properties", "file_path": file_path}
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in get_document_properties: {str(e)}")
        return f"Failed to get document properties: {str(e)}"


@mcp.tool()
async def list_documents(directory: str) -> str:
    """
    List all documents in a directory.

    Args:
        directory: Path to the directory to scan
    """
    try:
        # Normalize path
        directory = normalize_path(directory)

        # Send command to helper
        response = await call_libreoffice_helper(
            {"action": "list_documents", "directory": directory}
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in list_documents: {str(e)}")
        return f"Failed to list documents: {str(e)}"


@mcp.tool()
async def copy_document(source_path: str, target_path: str) -> str:
    """
    Create a copy of an existing document.

    Args:
        source_path: Path to the document to copy
        target_path: Path where to save the copy
    """
    try:
        # Normalize paths
        source_path = normalize_path(source_path)
        target_path = normalize_path(target_path)

        if source_path is target_path:
            raise Exception("Cannot copy a document to itself")

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "copy_document",
                "source_path": source_path,
                "target_path": target_path,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in copy_document: {str(e)}")
        return f"Failed to copy document: {str(e)}"


# Content Creation Tools


@mcp.tool()
async def add_text(file_path: str, text: str, position: Optional[str] = "end") -> str:
    """
    Add text to a LibreOffice document.

    Args:
        file_path: Path to the document
        text: Text to add
        position: Where to add text (start, end, or cursor)
    """
    try:
        # Normalize path
        file_path = normalize_path(file_path)

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "add_text",
                "file_path": file_path,
                "text": text,
                "position": position,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in add_text: {str(e)}")
        return f"Failed to add text: {str(e)}"


@mcp.tool()
async def add_heading(file_path: str, text: str, level: int = 1) -> str:
    """
    Add a heading to a document.

    Args:
        file_path: Path to the document
        text: Heading text
        level: Heading level (1-6, where 1 is the highest level)
    """
    try:
        # Normalize path
        file_path = normalize_path(file_path)

        # Validate heading level
        if level < 1 or level > 6:
            return f"Invalid heading level: {level}. Choose a level between 1 and 6."

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "add_heading",
                "file_path": file_path,
                "text": text,
                "level": level,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in add_heading: {str(e)}")
        return f"Failed to add heading: {str(e)}"


@mcp.tool()
async def add_paragraph(
    file_path: str,
    text: str,
    style: Optional[str] = None,
    alignment: Optional[str] = None,
) -> str:
    """
    Add a paragraph with optional styling.

    Args:
        file_path: Path to the document
        text: Paragraph text
        style: Paragraph style name (if available in document)
        alignment: Text alignment (left, center, right, justify)
    """
    try:
        # Normalize path
        file_path = normalize_path(file_path)

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "add_paragraph",
                "file_path": file_path,
                "text": text,
                "style": style,
                "alignment": alignment,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in add_paragraph: {str(e)}")
        return f"Failed to add paragraph: {str(e)}"


@mcp.tool()
async def add_table(
    file_path: str,
    rows: int,
    columns: int,
    data: Optional[List[List[str]]] = None,
    header_row: bool = False,
) -> str:
    """
    Add a table to a LibreOffice text document.

    Args:
        file_path: Path to the document
        rows: Number of rows
        columns: Number of columns
        data: Optional 2D list of data to populate the table
        header_row: Whether to format the first row as a header
    """
    try:
        # Normalize path
        file_path = normalize_path(file_path)

        # Check dimensions of table match data
        if data:
            if len(data) != rows:
                raise Exception("Data does not match dimensions provided")
            else:
                for row in data:
                    if len(row) != columns:
                        raise Exception("Data does not match dimensions provided")

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "add_table",
                "file_path": file_path,
                "rows": rows,
                "columns": columns,
                "data": data,
                "header_row": header_row,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in add_table: {str(e)}")
        return f"Failed to add table: {str(e)}"


@mcp.tool()
async def insert_image(
    file_path: str,
    image_path: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> str:
    """
    Insert an image into a LibreOffice document with optional resizing.

    Args:
        file_path: Path to the target document
        image_path: Path to the image file to insert
        width: Optional width in 100ths of mm (maintains aspect ratio if only width is specified)
        height: Optional height in 100ths of mm (maintains aspect ratio if only height is specified)
    """
    try:
        # Normalize paths
        file_path = normalize_path(file_path)
        image_path = normalize_path(image_path)

        if width and width <= 0:
            raise Exception("Invalid dimensions")
        if height and height <= 0:
            raise Exception("Invalid dimensions")

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "insert_image",
                "file_path": file_path,
                "image_path": image_path,
                "width": width,
                "height": height,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in insert_image: {str(e)}")
        return f"Failed to insert image: {str(e)}"


@mcp.tool()
async def insert_page_break(file_path: str) -> str:
    """
    Insert a page break at the end of a document.

    Args:
        file_path: Path to the document
    """
    try:
        # Normalize path
        file_path = normalize_path(file_path)

        # Send command to helper
        response = await call_libreoffice_helper(
            {"action": "insert_page_break", "file_path": file_path}
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in insert_page_break: {str(e)}")
        return f"Failed to insert page break: {str(e)}"


# Text Formatting Tools


@mcp.tool()
async def format_text(
    file_path: str,
    text_to_find: str,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    color: Optional[str] = None,
    font: Optional[str] = None,
    size: Optional[float] = None,
) -> str:
    """
    Format specific text in a document.

    Args:
        file_path: Path to the document to modify.
        text_to_find: The exact text string to search for and format.
        bold: If True, apply bold formatting to the found text.
        italic: If True, apply italic formatting to the found text.
        underline: If True, apply underline formatting to the found text.
        color: Optional text color in hex format (e.g., "#FF0000" for red).
        font: Optional font family name to apply (e.g., "Arial").
        size: Optional font size in points (e.g., 12.0).
    """
    try:
        # Normalize path
        file_path = normalize_path(file_path)

        # Send command to helper with all parameters using the correct names
        response = await call_libreoffice_helper(
            {
                "action": "format_text",
                "file_path": file_path,  # Note: using file_path, not filepath
                "text_to_find": text_to_find,
                "bold": bold,
                "italic": italic,
                "underline": underline,
                "color": color,
                "font": font,
                "size": size,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in format_text: {str(e)}")
        return f"Failed to format text: {str(e)}"


@mcp.tool()
async def search_replace_text(
    file_path: str, search_text: str, replace_text: str
) -> str:
    """
    Search and replace text throughout the document.

    Args:
        file_path: Path to the document
        search_text: Text to search for
        replace_text: Text to replace with
    """
    try:
        # Normalize path
        file_path = normalize_path(file_path)

        if not search_text:
            raise Exception("No search text provided")

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "search_replace_text",
                "file_path": file_path,
                "search_text": search_text,
                "replace_text": replace_text,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in search_replace_text: {str(e)}")
        return f"Failed to search and replace text: {str(e)}"


@mcp.tool()
async def delete_text(file_path: str, text_to_delete: str) -> str:
    """
    Delete specific text from the document.

    Args:
        file_path: Path to the document
        text_to_delete: Text to search for and delete
    """
    try:
        # Normalize path
        file_path = normalize_path(file_path)

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "delete_text",
                "file_path": file_path,
                "text_to_delete": text_to_delete,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in delete_text: {str(e)}")
        return f"Failed to delete text: {str(e)}"


# Table Formatting Tools


@mcp.tool()
async def format_table(
    file_path: str,
    table_index: int = 0,
    border_width: Optional[int] = None,
    background_color: Optional[str] = None,
    header_row: bool = False,
) -> str:
    """
    Format a table with borders, background color, and a header row

    Args:
        file_path: Path to the document
        table_index: Index of the table to format (0 = first table)
        border_width: Border width in points
        background_color: Background color (hex format, e.g., "#F0F0F0")
        header_row: Whether to format the first row as a header
    """
    try:
        # Normalize path
        file_path = normalize_path(file_path)

        # Prepare format options
        format_options = {}

        if border_width is not None:
            format_options["border_width"] = border_width

        if background_color:
            format_options["background_color"] = background_color

        format_options["header_row"] = header_row

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "format_table",
                "file_path": file_path,
                "table_index": table_index,
                "format_options": format_options,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in format_table: {str(e)}")
        return f"Failed to format table: {str(e)}"


# Advanced Document Manipulation Tools

# DISABLED - not currently functional
# @mcp.tool()
# async def create_custom_style(file_path: str, style_name: str, font_name: Optional[str] = None,
#                              font_size: Optional[float] = None, bold: bool = False, italic: bool = False,
#                              underline: bool = False, color: Optional[str] = None,
#                              alignment: Optional[str] = None) -> str:
#     """
#     Create a custom paragraph style.

#     Args:
#         file_path: Path to the document
#         style_name: Name for the style
#         font_name: Font name
#         font_size: Font size in points
#         bold: Apply bold formatting
#         italic: Apply italic formatting
#         underline: Apply underline formatting
#         color: Text color (hex format, e.g., "#000000")
#         alignment: Paragraph alignment (left, center, right, justify)
#     """
#     try:
#         # Normalize path
#         file_path = normalize_path(file_path)

#         # Prepare style properties
#         style_properties = {}

#         if font_name:
#             style_properties["font_name"] = font_name

#         if font_size is not None:
#             style_properties["font_size"] = font_size

#         if bold:
#             style_properties["bold"] = True

#         if italic:
#             style_properties["italic"] = True

#         if underline:
#             style_properties["underline"] = True

#         if color:
#             style_properties["color"] = color

#         if alignment:
#             style_properties["alignment"] = alignment

#         # Send command to helper
#         response = await call_libreoffice_helper({
#             "action": "create_custom_style",
#             "file_path": file_path,
#             "style_name": style_name,
#             "style_properties": style_properties
#         })

#         if response["status"] == "success":
#             return response["message"]
#         else:
#             return f"Error: {response['message']}"
#     except Exception as e:
#         print(f"Error in create_custom_style: {str(e)}")
#         return f"Failed to create custom style: {str(e)}"


@mcp.tool()
async def delete_paragraph(file_path: str, paragraph_index: int) -> str:
    """
    Delete a paragraph at the given index.
    If the user has not specified an index, you may need to call the read_text_document function first to find the correct index.

    Args:
        file_path: Path to the document
        paragraph_index: Index of the paragraph to delete (0 = first paragraph)
    """
    try:
        # Normalize path
        file_path = normalize_path(file_path)

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "delete_paragraph",
                "file_path": file_path,
                "paragraph_index": paragraph_index,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in delete_paragraph: {str(e)}")
        return f"Failed to delete paragraph: {str(e)}"


@mcp.tool()
async def apply_document_style(
    file_path: str,
    font_name: Optional[str] = None,
    font_size: Optional[float] = None,
    color: Optional[str] = None,
    alignment: Optional[str] = None,
) -> str:
    """
    Apply consistent formatting throughout the document.

    Args:
        file_path: Path to the document
        font_name: Font name
        font_size: Font size in points
        color: Text color (hex format, e.g., "#000000")
        alignment: Alignment (left, center, right, justify)
    """
    try:
        # Normalize path
        file_path = normalize_path(file_path)

        # Prepare style
        style = {}

        if font_name:
            style["font_name"] = font_name

        if font_size:
            style["font_size"] = font_size

        if color:
            style["color"] = color

        if alignment:
            style["alignment"] = alignment

        # Send command to helper
        response = await call_libreoffice_helper(
            {"action": "apply_document_style", "file_path": file_path, "style": style}
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in apply_document_style: {str(e)}")
        return f"Failed to apply document style: {str(e)}"


# Impress Presentation functions
@mcp.tool()
async def create_blank_presentation(
    filename: str,
    title: str = "",
    author: str = "",
    subject: str = "",
    keywords: str = "",
) -> str:
    """
    Create a new LibreOffice Impress presentation.

    Args:
        filename: Name of the presentation
        title: Presentation title metadata
        author: Presentation author metadata
        subject: Presentation subject metadata
        keywords: Presentation keywords metadata (comma-separated)
    """
    try:
        # Check for supported file extensions
        if not filename.lower().endswith(impress_extensions):
            filename += ".odp"

        # If filename doesn't include a path, add default path
        if os.path.basename(filename) == filename:
            save_path = get_default_document_path(filename)
        else:
            save_path = filename

        # Normalize path
        save_path = normalize_path(save_path)
        print(f"Creating document at: {save_path}")

        # Prepare metadata if provided
        metadata = {}
        if title:
            metadata["Title"] = title
        if author:
            metadata["Author"] = author
        if subject:
            metadata["Subject"] = subject
        if keywords:
            # Split by comma and strip whitespace
            keywords_list = [k.strip() for k in keywords.split(",")]
            metadata["Keywords"] = keywords_list

        logging.info(save_path)
        logging.info(metadata)

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "create_document",
                "doc_type": "impress",
                "file_path": save_path,
                "metadata": metadata,
            }
        )

        logging.info(response["status"])
        logging.info(response["message"])

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"

    except Exception as e:
        logging.error(f"Error in create_document: {str(e)}")
        return f"Failed to create document: {str(e)}"


@mcp.tool()
async def read_presentation(file_path: str) -> str:
    """
    Open and read the text of an Impress presentation.

    Args:
        file_path: Path to the presentation
    """
    try:
        # Normalize path
        file_path = normalize_path(file_path)

        # Send command to helper
        response = await call_libreoffice_helper(
            {"action": "read_presentation", "file_path": file_path}
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in open_presentation: {str(e)}")
        return f"Failed to open presentation: {str(e)}"


@mcp.tool()
async def add_slide(
    file_path: str,
    slide_index: Optional[int] = None,
    title: Optional[str] = None,
    content: Optional[str] = None,
) -> str:
    """
    Add a new slide to an Impress presentation using the built-in layout.

    Args:
        file_path: Path to the presentation file.
        slide_index: Index at which to insert the new slide (0-based). If None, the slide is appended at the end.
        title: Optional title text for the new slide.
        content: Optional content text for the new slide.
    """
    try:
        if not file_path.endswith(impress_extensions):
            return "Error: file_path is not a presentation."

        file_path = normalize_path(file_path)

        response = await call_libreoffice_helper(
            {
                "action": "add_slide",
                "file_path": file_path,
                "slide_index": slide_index,
                "title": title,
                "content": content,
            }
        )

        print(f"add_slide: response={response}")

        if not response:
            return "Error: No response from helper."
        if response.get("status") == "success":
            return response.get("message", "")
        else:
            return f"Error: {response.get('message', 'Unknown error')}"
    except Exception as e:
        print(f"Error in add_slide: {str(e)}")
        return f"Failed to add slide: {str(e)}"


@mcp.tool()
async def edit_slide_content(file_path: str, slide_index: int, new_content: str) -> str:
    """
    Edit the main text content of a specific slide in an Impress presentation.

    Args:
        file_path: Path to the presentation file
        slide_index: Index of the slide to edit (0-based, where 0 is the first slide)
        new_content: New text content to set in the main content area
    """
    try:
        # Validate file extension
        if not file_path.lower().endswith(impress_extensions):
            return "Error: file_path is not a presentation file."

        # Normalize path
        file_path = normalize_path(file_path)

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "edit_slide_content",
                "file_path": file_path,
                "slide_index": slide_index,
                "new_content": new_content,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in edit_slide_content: {str(e)}")
        return f"Failed to edit slide content: {str(e)}"


@mcp.tool()
async def edit_slide_title(file_path: str, slide_index: int, new_title: str) -> str:
    """
    Edit the title of a specific slide in an Impress presentation.

    Args:
        file_path: Path to the presentation file
        slide_index: Index of the slide to edit (0-based, where 0 is the first slide)
        new_title: New title text to set in the title area
    """
    try:
        # Validate file extension
        if not file_path.lower().endswith(impress_extensions):
            return "Error: file_path is not a presentation file."

        # Normalize path
        file_path = normalize_path(file_path)

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "edit_slide_title",
                "file_path": file_path,
                "slide_index": slide_index,
                "new_title": new_title,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in edit_slide_title: {str(e)}")
        return f"Failed to edit slide title: {str(e)}"


@mcp.tool()
async def delete_slide(file_path: str, slide_index: int) -> str:
    """
    Delete a slide from an Impress presentation.

    Args:
        file_path: Path to the presentation file
        slide_index: Index of the slide to delete (0-based, where 0 is the first slide)
    """
    try:
        # Validate file extension
        if not file_path.lower().endswith(impress_extensions):
            return "Error: file_path is not a presentation file."

        # Normalize path
        file_path = normalize_path(file_path)

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "delete_slide",
                "file_path": file_path,
                "slide_index": slide_index,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in delete_slide: {str(e)}")
        return f"Failed to delete slide: {str(e)}"


@mcp.tool()
async def apply_presentation_template(file_path: str, template_name: str) -> str:
    """
    Apply a built-in LibreOffice presentation template/master slide to a presentation.

    Args:
        file_path: Path to the presentation file
        template_name: Name of the built-in template to apply (can be exact name, partial match, or numeric index)
    """
    try:
        # Validate file extension
        if not file_path.lower().endswith(impress_extensions):
            return "Error: file_path is not a presentation file."

        # Normalize path
        file_path = normalize_path(file_path)

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "apply_presentation_template",
                "file_path": file_path,
                "template_name": template_name,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in apply_presentation_template: {str(e)}")
        return f"Failed to apply presentation template: {str(e)}"


@mcp.tool()
async def format_slide_content(
    file_path: str,
    slide_index: int,
    font_name: Optional[str] = None,
    font_size: Optional[float] = None,
    bold: Optional[bool] = None,
    italic: Optional[bool] = None,
    underline: Optional[bool] = None,
    color: Optional[str] = None,
    alignment: Optional[str] = None,
    line_spacing: Optional[float] = None,
    background_color: Optional[str] = None,
) -> str:
    """
    Format the content text of a specific slide in an Impress presentation.

    Args:
        file_path: Path to the presentation file
        slide_index: Index of the slide to format (0-based, where 0 is the first slide)
        font_name: Font family name (e.g., "Arial", "Times New Roman")
        font_size: Font size in points (e.g., 18, 24)
        bold: Apply bold formatting (True/False)
        italic: Apply italic formatting (True/False)
        underline: Apply underline formatting (True/False)
        color: Text color as hex string (e.g., "#FF0000") or RGB integer
        alignment: Text alignment ("left", "center", "right", "justify")
        line_spacing: Line spacing multiplier (e.g., 1.5, 2.0)
        background_color: Background color as hex string (e.g., "#F0F0F0") or RGB integer
    """
    try:
        # Validate file extension
        if not file_path.lower().endswith(impress_extensions):
            return "Error: file_path is not a presentation file."

        # Normalize path
        file_path = normalize_path(file_path)

        # Prepare format options
        format_options = {}

        if font_name is not None:
            format_options["font_name"] = font_name
        if font_size is not None:
            format_options["font_size"] = font_size
        if bold is not None:
            format_options["bold"] = bold
        if italic is not None:
            format_options["italic"] = italic
        if underline is not None:
            format_options["underline"] = underline
        if color is not None:
            format_options["color"] = color
        if alignment is not None:
            format_options["alignment"] = alignment
        if line_spacing is not None:
            format_options["line_spacing"] = line_spacing
        if background_color is not None:
            format_options["background_color"] = background_color

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "format_slide_content",
                "file_path": file_path,
                "slide_index": slide_index,
                "format_options": format_options,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in format_slide_content: {str(e)}")
        return f"Failed to format slide content: {str(e)}"


@mcp.tool()
async def format_slide_title(
    file_path: str,
    slide_index: int,
    font_name: Optional[str] = None,
    font_size: Optional[float] = None,
    bold: Optional[bool] = None,
    italic: Optional[bool] = None,
    underline: Optional[bool] = None,
    color: Optional[str] = None,
    alignment: Optional[str] = None,
    line_spacing: Optional[float] = None,
    background_color: Optional[str] = None,
) -> str:
    """
    Format the title text of a specific slide in an Impress presentation.

    Args:
        file_path: Path to the presentation file
        slide_index: Index of the slide to format (0-based, where 0 is the first slide)
        font_name: Font family name (e.g., "Arial", "Times New Roman")
        font_size: Font size in points (e.g., 28, 36)
        bold: Apply bold formatting (True/False)
        italic: Apply italic formatting (True/False)
        underline: Apply underline formatting (True/False)
        color: Text color as hex string (e.g., "#FF0000") or RGB integer
        alignment: Text alignment ("left", "center", "right", "justify")
        line_spacing: Line spacing multiplier (e.g., 1.5, 2.0)
        background_color: Background color as hex string (e.g., "#F0F0F0") or RGB integer
    """
    try:
        # Validate file extension
        if not file_path.lower().endswith(impress_extensions):
            return "Error: file_path is not a presentation file."

        # Normalize path
        file_path = normalize_path(file_path)

        # Prepare format options
        format_options = {}

        if font_name is not None:
            format_options["font_name"] = font_name
        if font_size is not None:
            format_options["font_size"] = font_size
        if bold is not None:
            format_options["bold"] = bold
        if italic is not None:
            format_options["italic"] = italic
        if underline is not None:
            format_options["underline"] = underline
        if color is not None:
            format_options["color"] = color
        if alignment is not None:
            format_options["alignment"] = alignment
        if line_spacing is not None:
            format_options["line_spacing"] = line_spacing
        if background_color is not None:
            format_options["background_color"] = background_color

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "format_slide_title",
                "file_path": file_path,
                "slide_index": slide_index,
                "format_options": format_options,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in format_slide_title: {str(e)}")
        return f"Failed to format slide title: {str(e)}"


@mcp.tool()
async def insert_slide_image(
    file_path: str,
    slide_index: int,
    image_path: str,
    max_width: Optional[int] = None,
    max_height: Optional[int] = None,
) -> str:
    """
    Insert an image into a specific slide of an Impress presentation.
    The image will be centered on the slide and resized if necessary to fit.

    Args:
        file_path: Path to the presentation file
        slide_index: Index of the slide to insert the image into (0-based, where 0 is the first slide)
        image_path: Path to the image file to insert
        max_width: Maximum width in 1/100mm units (defaults to slide width minus margins)
        max_height: Maximum height in 1/100mm units (defaults to slide height minus margins)
    """
    try:
        # Validate file extension
        if not file_path.lower().endswith(impress_extensions):
            return "Error: file_path is not a presentation file."

        # Get image dimensions and DPI
        img_width_px, img_height_px, dpi = get_image_size(image_path)

        # Normalize paths
        file_path = normalize_path(file_path)
        image_path = normalize_path(image_path)

        # Send command to helper
        response = await call_libreoffice_helper(
            {
                "action": "insert_slide_image",
                "file_path": file_path,
                "slide_index": slide_index,
                "image_path": image_path,
                "max_width": max_width,
                "max_height": max_height,
                "img_width_px": img_width_px,
                "img_height_px": img_height_px,
                "dpi": dpi,
            }
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Error: {response['message']}"
    except Exception as e:
        print(f"Error in insert_slide_image: {str(e)}")
        return f"Failed to insert slide image: {str(e)}"


# Resource for document access
@mcp.resource("libreoffice:{path}")
async def document_resource(path: str) -> str:
    """
    Resource for accessing LibreOffice document content.

    Args:
        path: Path to the document

    Returns:
        Document content as text
    """
    try:
        normalized_path = normalize_path(path)

        # Send command to helper
        response = await call_libreoffice_helper(
            {"action": "open_text_document", "file_path": normalized_path}
        )

        if response["status"] == "success":
            return response["message"]
        else:
            return f"Failed to access document resource: {response['message']}"
    except Exception as e:
        print(f"Error in document_resource: {str(e)}")
        return f"Failed to access document resource: {str(e)}"


async def main():
    """
    Main entry point for the LibreOffice MCP server.
    """
    print("Starting LibreOffice MCP server with stdio transport")

    # Check if helper is running
    try:
        response = await call_libreoffice_helper({"action": "ping"})
        if (
            response["status"] == "error"
            and "Connection refused" in response["message"]
        ):
            print("⚠️ WARNING: LibreOffice helper is not running!")
            print("Please start the helper first with:")
            print('"C:\\Program Files\\LibreOffice\\program\\python.exe" helper.py')
            print("Continuing anyway, but LibreOffice operations will fail...")
    except Exception:
        print("Failed to check helper status")

    # Run the server using stdio transport
    await mcp.run_stdio_async()
    logging.info("MCP server exited")


if __name__ == "__main__":
    asyncio.run(main())
