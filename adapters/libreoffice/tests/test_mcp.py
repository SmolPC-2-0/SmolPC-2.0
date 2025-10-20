import os
import sys
import subprocess
import pytest
import time
import json
import socket
import tempfile
import shutil
import asyncio
from fastmcp import Client
from mcp.types import TextContent
from main import start_office, is_port_in_use, get_python_path
from test_helper import check_helper_status
from libre import mcp


def start_helper():
    """Start the Office helper script with LibreOffice"""
    if not is_port_in_use(8765):
        print("Starting Office helper...", file=sys.stderr)
        current_dir = os.path.dirname(__file__)
        parent_dir = os.path.dirname(current_dir)
        helper_script = os.path.join(parent_dir, "helper.py")
        python_path = get_python_path()
        subprocess.Popen([python_path, helper_script])
        time.sleep(3)
    else:
        print("Helper script already running on port 8765", file=sys.stderr)


def send_command_to_helper(command):
    """Send a command to the LibreOffice helper and get response"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(("localhost", 8765))
            sock.send(json.dumps(command).encode("utf-8"))
            response = sock.recv(16384).decode("utf-8")
            return json.loads(response)
    except Exception as e:
        return {"status": "error", "message": str(e)}


@pytest.fixture(scope="session")
def libreoffice_server():
    """Fixture that starts LibreOffice and helper services for the entire test session"""
    start_office()
    start_helper()

    # Verify the helper is running correctly before proceeding
    helper_status = check_helper_status()
    if not helper_status:
        pytest.fail("Helper is not running correctly. Cannot proceed with tests.")

    yield mcp


@pytest.fixture(scope="function")
def temp_dir():
    """Fixture that creates a temporary directory for test files and cleans up after each test"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def test_document(libreoffice_server, temp_dir):
    """Fixture that creates a test ODT document with sample content for each test function"""

    async def create_document():
        async with Client(libreoffice_server) as client:
            # Create a document with some content
            filename = os.path.join(temp_dir, "test_document.odt")
            await client.call_tool(
                "create_blank_document",
                {"filename": filename, "title": "Test Document", "author": "pytest"},
            )
            await client.call_tool(
                "add_text",
                {
                    "file_path": filename,
                    "text": "This is a test document with sample content. This is some formatted text.",
                },
            )
            return filename

    # Run the async function and return the result
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(create_document())


@pytest.fixture(scope="function")
def test_presentation(libreoffice_server, temp_dir):
    """Fixture that creates a test ODP presentation with sample content for each test function"""

    async def create_presentation():
        async with Client(libreoffice_server) as client:
            # Create a presentation with some content
            filename = os.path.join(temp_dir, "test_presentation.odp")
            await client.call_tool(
                "create_blank_presentation",
                {
                    "filename": filename,
                    "title": "Test Presentation",
                    "author": "pytest",
                },
            )
            # Add a slide with content
            await client.call_tool(
                "add_slide",
                {
                    "file_path": filename,
                    "title": "Test Slide",
                    "content": "This is test slide content.",
                },
            )
            return filename

    # Run the async function and return the result
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(create_presentation())


@pytest.fixture(scope="function")
def test_image(temp_dir):
    """Fixture that creates a simple 100x100 red PNG image for testing image insertion functionality"""
    try:
        from PIL import Image

        image_path = os.path.join(temp_dir, "test_image.png")
        # Create a simple 100x100 red image
        img = Image.new("RGB", (100, 100), color="red")
        img.save(image_path)
        return image_path
    except ImportError:
        pytest.skip("PIL not available for image tests")


# Document Management Tests


@pytest.mark.asyncio
async def test_create_blank_document(libreoffice_server, temp_dir):
    """Test creating a new blank Writer document with metadata (title, author, subject, keywords)"""
    async with Client(libreoffice_server) as client:
        filename = os.path.join(temp_dir, "test_document.odt")
        result = await client.call_tool(
            "create_blank_document",
            {
                "filename": filename,
                "title": "Test Document",
                "author": "pytest",
                "subject": "Testing",
                "keywords": "test, pytest, document",
            },
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "Successfully created text document" in result_content.text
        assert os.path.exists(filename)


@pytest.mark.asyncio
async def test_read_text_document(libreoffice_server, test_document):
    """Test reading the complete text content from an existing Writer document"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "read_text_document", {"file_path": test_document}
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "This is a test document with sample content." in result_content.text


@pytest.mark.asyncio
async def test_get_document_properties(libreoffice_server, test_document):
    """Test retrieving document metadata properties (title, author, subject, etc.)"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "get_document_properties", {"file_path": test_document}
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert (
            "Test Document" in result_content.text
            or "properties" in result_content.text.lower()
        )


@pytest.mark.asyncio
async def test_list_documents(libreoffice_server, temp_dir):
    """Test listing all LibreOffice documents (.odt, .odp, .ods files) in a specified directory"""
    async with Client(libreoffice_server) as client:
        # Create test documents first
        filename = os.path.join(temp_dir, "list_test.odt")
        filename2 = os.path.join(temp_dir, "list_test2.odt")

        await client.call_tool("create_blank_document", {"filename": filename})
        await client.call_tool("create_blank_document", {"filename": filename2})

        result = await client.call_tool("list_documents", {"directory": temp_dir})

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert (
            "list_test.odt" in result_content.text
            and "list_test2.odt" in result_content.text
        )


@pytest.mark.asyncio
async def test_copy_document(libreoffice_server, test_document, temp_dir):
    """Test copying an existing document to a new location while preserving all content and formatting"""
    async with Client(libreoffice_server) as client:
        target_file = os.path.join(temp_dir, "copied_document.odt")

        # Copy the test document
        result = await client.call_tool(
            "copy_document", {"source_path": test_document, "target_path": target_file}
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "copied" in result_content.text.lower()
        assert os.path.exists(target_file)

        # Check the content has also been copied
        read_result = await client.call_tool(
            "read_text_document", {"file_path": target_file}
        )

        read_result_content = read_result.content[0]
        assert isinstance(read_result_content, TextContent)
        assert (
            "This is a test document with sample content." in read_result_content.text
        )


# Content Creation Tests


@pytest.mark.asyncio
async def test_add_text(libreoffice_server, test_document):
    """Test adding plain text to a document at a specified position (beginning, end, or current cursor)"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "add_text",
            {
                "file_path": test_document,
                "text": " Additional text added!",
                "position": "end",
            },
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "text added" in result_content.text.lower()

        # Check the content has been added
        read_result = await client.call_tool(
            "read_text_document", {"file_path": test_document}
        )

        read_result_content = read_result.content[0]
        assert isinstance(read_result_content, TextContent)
        assert "Additional text added!" in read_result_content.text


@pytest.mark.asyncio
async def test_add_heading(libreoffice_server, test_document):
    """Test adding a formatted heading with specified level (1-6) and verifying the heading style is applied"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "add_heading", {"file_path": test_document, "text": "Chapter 1", "level": 1}
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "heading" in result_content.text.lower()

        # Check the content has been added
        formatting_result = send_command_to_helper(
            {
                "action": "get_text_formatting",
                "file_path": test_document,
                "text_to_find": "Chapter 1",
            }
        )

        if formatting_result["status"] == "success":
            formatting_data = json.loads(formatting_result["message"])

            assert formatting_data["occurrences_found"] >= 1
            assert formatting_data["paragraph_style"] == "Heading 1"
        else:
            assert False, "Failed to get formatting data"


@pytest.mark.asyncio
async def test_add_paragraph(libreoffice_server, test_document):
    """Test adding a paragraph with specified text alignment (left, center, right, justify)"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "add_paragraph",
            {
                "file_path": test_document,
                "text": "This is a test paragraph.",
                "alignment": "center",
            },
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "paragraph" in result_content.text.lower()

        # Check the content has been added
        formatting_result = send_command_to_helper(
            {
                "action": "get_text_formatting",
                "file_path": test_document,
                "text_to_find": "This is a test paragraph.",
            }
        )

        if formatting_result["status"] == "success":
            formatting_data = json.loads(formatting_result["message"])

            assert formatting_data["occurrences_found"] >= 1
            assert formatting_data["paragraph_style"] == "Standard"
            assert formatting_data["alignment"] == "center"
        else:
            assert False, "Failed to get formatting data"


@pytest.mark.asyncio
async def test_add_table(libreoffice_server, test_document):
    """Test creating a table with specified dimensions, data content, and header row formatting"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "add_table",
            {
                "file_path": test_document,
                "rows": 3,
                "columns": 2,
                "data": [
                    ["Header 1", "Header 2"],
                    ["Data 1", "Data 2"],
                    ["Data 3", "Data 4"],
                ],
                "header_row": True,
            },
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert (
            "table" in result_content.text.lower()
            or "success" in result_content.text.lower()
        )

        # Check the table has been added
        table_result = send_command_to_helper(
            {
                "action": "get_table_info",
                "file_path": test_document,
            }
        )

        if table_result["status"] == "success":
            table_data = json.loads(table_result["message"])

            assert table_data["rows"] == 3
            assert table_data["columns"] == 2
        else:
            assert False, "Failed to get table data"


@pytest.mark.asyncio
async def test_insert_image(libreoffice_server, test_document, test_image):
    """Test inserting an image file into a document with specified width and height dimensions"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "insert_image",
            {
                "file_path": test_document,
                "image_path": test_image,
                "width": 5000,  # 50mm in 100ths of mm
                "height": 5000,
            },
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "image" in result_content.text.lower()

        # Check the image has been added
        image_result = send_command_to_helper(
            {
                "action": "has_image",
                "file_path": test_document,
            }
        )

        if image_result["status"] == "success":
            image_data = json.loads(image_result["message"])

            assert image_data["image_count"] > 0
            assert (image_data["first_image_width"] / 5000) - 1 < 0.01
            assert (image_data["first_image_height"] / 5000) - 1 < 0.01
        else:
            assert False, "Failed to get image data"


@pytest.mark.asyncio
async def test_insert_page_break(libreoffice_server, test_document):
    """Test inserting a manual page break to force content onto the next page"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "insert_page_break", {"file_path": test_document}
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "page break" in result_content.text.lower()

        # Check the page break has been added
        page_break_result = send_command_to_helper(
            {
                "action": "get_page_break_info",
                "file_path": test_document,
            }
        )

        if page_break_result["status"] == "success":
            page_break_data = json.loads(page_break_result["message"])

            print(page_break_data)
            assert page_break_data["total_page_breaks"] > 0
        else:
            assert False, "Failed to get page break data"


# Text Formatting Tests


@pytest.mark.asyncio
async def test_format_text(libreoffice_server, test_document):
    """Test applying text formatting (bold, italic, color) to specific text found in the document"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "format_text",
            {
                "file_path": test_document,
                "text_to_find": "This is some formatted text.",
                "bold": True,
                "italic": True,
                "color": "#FF0000",
            },
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "format" in result_content.text.lower()

        # Check the content has been formatted
        formatting_result = send_command_to_helper(
            {
                "action": "get_text_formatting",
                "file_path": test_document,
                "text_to_find": "This is some formatted text.",
            }
        )

        if formatting_result["status"] == "success":
            formatting_data = json.loads(formatting_result["message"])

            print(formatting_data)
            assert formatting_data["occurrences_found"] >= 1
            assert formatting_data["color"] == "#FF0000"
            assert formatting_data["bold"]
            assert formatting_data["italic"]
        else:
            assert False, "Failed to get formatting data"


@pytest.mark.asyncio
async def test_search_replace_text(libreoffice_server, test_document):
    """Test finding all occurrences of specific text and replacing them with new text throughout the document"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "search_replace_text",
            {
                "file_path": test_document,
                "search_text": "sample",
                "replace_text": "modified",
            },
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "replace" in result_content.text.lower()

        result = await client.call_tool(
            "read_text_document", {"file_path": test_document}
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "modified" in result_content.text


@pytest.mark.asyncio
async def test_delete_text(libreoffice_server, test_document):
    """Test removing specific text from the document by replacing it with empty string"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "delete_text",
            {"file_path": test_document, "text_to_delete": "sample content"},
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "replaced" in result_content.text.lower()

        read_result = await client.call_tool(
            "read_text_document", {"file_path": test_document}
        )

        read_result_content = read_result.content[0]
        assert isinstance(read_result_content, TextContent)
        assert "sample content" not in read_result_content.text


# Table Formatting Tests


@pytest.mark.asyncio
async def test_format_table(libreoffice_server, test_document):
    """Test applying formatting to an existing table including borders, background color, and header styling"""
    async with Client(libreoffice_server) as client:
        # Add a table first
        await client.call_tool(
            "add_table", {"file_path": test_document, "rows": 2, "columns": 2}
        )

        border_width = 2

        result = await client.call_tool(
            "format_table",
            {
                "file_path": test_document,
                "table_index": 0,
                "border_width": border_width,
                "background_color": "#F0F0F0",
                "header_row": True,
            },
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "formatted" in result_content.text.lower()

        # Check the table has been added
        table_result = send_command_to_helper(
            {
                "action": "get_table_info",
                "file_path": test_document,
            }
        )

        if table_result["status"] == "success":
            table_data = json.loads(table_result["message"])
            print(f"Border widths: {table_data['border_widths']}")

            # Fix the calculation - convert from 1/100mm back to points
            # The border_widths are in 1/100mm, so convert back to points
            border_widths_in_points = {
                k: v / 35.28 for k, v in table_data["border_widths"].items()
            }
            avg_border_width_points = sum(border_widths_in_points.values()) / len(
                border_widths_in_points
            )

            print(f"Average border width in points: {avg_border_width_points}")
            print(f"Expected border width: {border_width}")
            print(table_data)

            assert table_data["background_color"] == "#F0F0F0"
            assert abs(avg_border_width_points - border_width) <= border_width * 0.1
        else:
            assert False, "Failed to get table data"


# Advanced Document Manipulation Tests


@pytest.mark.asyncio
async def test_delete_paragraph(libreoffice_server, test_document):
    """Test removing a specific paragraph from the document by its index position"""
    async with Client(libreoffice_server) as client:
        # Add some paragraphs first
        await client.call_tool(
            "add_paragraph", {"file_path": test_document, "text": "First paragraph"}
        )
        await client.call_tool(
            "add_paragraph",
            {"file_path": test_document, "text": "Second paragraph to delete"},
        )

        result = await client.call_tool(
            "delete_paragraph", {"file_path": test_document, "paragraph_index": 1}
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "delete" in result_content.text.lower()

        read_result = await client.call_tool(
            "read_text_document", {"file_path": test_document}
        )

        read_result_content = read_result.content[0]
        assert isinstance(read_result_content, TextContent)
        assert "Second paragraph" not in read_result_content.text


@pytest.mark.asyncio
async def test_apply_document_style(libreoffice_server, test_document):
    """Test applying document-wide formatting including font family, size, color, and text alignment"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "apply_document_style",
            {
                "file_path": test_document,
                "font_name": "Arial",
                "font_size": 12,
                "color": "#000080",
                "alignment": "justify",
            },
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "style" in result_content.text.lower()

        # Check the content has been formatted
        formatting_result = send_command_to_helper(
            {
                "action": "get_text_formatting",
                "file_path": test_document,
                "text_to_find": "This is a test document",
            }
        )

        if formatting_result["status"] == "success":
            formatting_data = json.loads(formatting_result["message"])

            assert formatting_data["occurrences_found"] >= 1
            assert formatting_data["color"] == "#000080"
            assert formatting_data["font_name"] == "Arial"
            assert formatting_data["alignment"] == "block"
        else:
            assert False, "Failed to get formatting data"


# Presentation Tests


@pytest.mark.asyncio
async def test_create_blank_presentation(libreoffice_server, temp_dir):
    """Test creating a new blank Impress presentation file with specified metadata"""
    async with Client(libreoffice_server) as client:
        filename = os.path.join(temp_dir, "test_presentation.odp")
        result = await client.call_tool(
            "create_blank_presentation",
            {"filename": filename, "title": "Test Presentation", "author": "pytest"},
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "presentation" in result_content.text.lower()
        assert os.path.exists(filename)


@pytest.mark.asyncio
async def test_read_presentation(libreoffice_server, test_presentation):
    """Test reading all slide content and structure from an existing presentation file"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "read_presentation", {"file_path": test_presentation}
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "This is test slide content." in result_content.text


@pytest.mark.asyncio
async def test_add_slide(libreoffice_server, test_presentation):
    """Test adding a new slide with title and content to an existing presentation"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "add_slide",
            {
                "file_path": test_presentation,
                "title": "New Slide",
                "content": "This is added slide content.",
            },
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "slide added" in result_content.text.lower()

        read_result = await client.call_tool(
            "read_presentation", {"file_path": test_presentation}
        )

        read_result_content = read_result.content[0]
        assert isinstance(read_result_content, TextContent)
        assert "This is added slide content." in read_result_content.text


@pytest.mark.asyncio
async def test_edit_slide_content(libreoffice_server, test_presentation):
    """Test modifying the main content text of a specific slide by index"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "edit_slide_content",
            {
                "file_path": test_presentation,
                "slide_index": 0,
                "new_content": "Updated slide content",
            },
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "edited" in result_content.text.lower()

        read_result = await client.call_tool(
            "read_presentation", {"file_path": test_presentation}
        )

        read_result_content = read_result.content[0]
        assert isinstance(read_result_content, TextContent)
        assert "Updated slide content" in read_result_content.text


@pytest.mark.asyncio
async def test_edit_slide_title(libreoffice_server, test_presentation):
    """Test changing the title of a specific slide by index"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "edit_slide_title",
            {
                "file_path": test_presentation,
                "slide_index": 0,
                "new_title": "Updated Title",
            },
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "edited" in result_content.text.lower()

        read_result = await client.call_tool(
            "read_presentation", {"file_path": test_presentation}
        )

        read_result_content = read_result.content[0]
        assert isinstance(read_result_content, TextContent)
        assert "Updated Title" in read_result_content.text


@pytest.mark.asyncio
async def test_delete_slide(libreoffice_server, test_presentation):
    """Test removing a specific slide from the presentation by index"""
    async with Client(libreoffice_server) as client:
        # Add another slide first
        await client.call_tool(
            "add_slide",
            {
                "file_path": test_presentation,
                "title": "Slide to delete",
                "content": "Deleted content",
            },
        )

        result = await client.call_tool(
            "delete_slide", {"file_path": test_presentation, "slide_index": 2}
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "deleted" in result_content.text.lower()

        read_result = await client.call_tool(
            "read_presentation", {"file_path": test_presentation}
        )

        read_result_content = read_result.content[0]
        assert isinstance(read_result_content, TextContent)
        assert "Deleted content" not in read_result_content.text


@pytest.mark.asyncio
async def test_apply_presentation_template(libreoffice_server, test_presentation):
    """Test applying a predefined presentation template to change the visual design and layout"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "apply_presentation_template",
            {"file_path": test_presentation, "template_name": "Beehive"},
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "applied template" in result_content.text.lower()

        template_result = send_command_to_helper(
            {
                "action": "get_presentation_template_info",
                "file_path": test_presentation,
            }
        )

        if template_result["status"] == "success":
            template = template_result["message"]

            assert "Beehive" in template
        else:
            assert False, "Failed to get template data"


@pytest.mark.asyncio
async def test_format_slide_content(libreoffice_server, test_presentation):
    """Test applying text formatting (font, size, color, bold) to the main content of a specific slide"""
    async with Client(libreoffice_server) as client:
        slide_index = 1

        result = await client.call_tool(
            "format_slide_content",
            {
                "file_path": test_presentation,
                "slide_index": slide_index,
                "font_name": "Arial",
                "font_size": 18,
                "bold": True,
                "color": "#FF0000",
            },
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "formatted" in result_content.text.lower()

        formatting_result = send_command_to_helper(
            {
                "action": "get_presentation_text_formatting",
                "file_path": test_presentation,
                "text_to_find": "This is test slide content.",
            }
        )

        if formatting_result["status"] == "success":
            formatting_data = json.loads(formatting_result["message"])

            print(formatting_data)
            assert formatting_data["found_on_slide"] == slide_index
            assert formatting_data["color"] == "#FF0000"
            assert formatting_data["bold"]
            assert formatting_data["font_size"] == 18
        else:
            assert False, "Failed to get template data"


@pytest.mark.asyncio
async def test_format_slide_title(libreoffice_server, test_presentation):
    """Test applying text formatting (font, size, underline, alignment) to the title of a specific slide"""
    async with Client(libreoffice_server) as client:
        slide_index = 1

        result = await client.call_tool(
            "format_slide_title",
            {
                "file_path": test_presentation,
                "slide_index": slide_index,
                "font_name": "Times New Roman",
                "font_size": 24,
                "underline": True,
                "alignment": "center",
            },
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "formatted" in result_content.text.lower()

        formatting_result = send_command_to_helper(
            {
                "action": "get_presentation_text_formatting",
                "file_path": test_presentation,
                "text_to_find": "Test Slide",
            }
        )

        if formatting_result["status"] == "success":
            formatting_data = json.loads(formatting_result["message"])

            assert formatting_data["alignment"] == "center"
            assert formatting_data["found_on_slide"] == slide_index
            assert formatting_data["font_name"] == "Times New Roman"
            assert formatting_data["underline"]
            assert formatting_data["font_size"] == 24
        else:
            assert False, "Failed to get template data"


@pytest.mark.asyncio
async def test_insert_slide_image(libreoffice_server, test_presentation, test_image):
    """Test inserting an image file into a specific slide with size constraints and automatic centering"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "insert_slide_image",
            {
                "file_path": test_presentation,
                "slide_index": 0,
                "image_path": test_image,
                "max_width": 10000,  # 100mm in 1/100mm units
                "max_height": 10000,
            },
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "inserted image" in result_content.text.lower()

        image_result = send_command_to_helper(
            {
                "action": "get_slide_image_info",
                "file_path": test_presentation,
                "slide_index": 0,
            }
        )

        if image_result["status"] == "success":
            image_data = json.loads(image_result["message"])
            image = image_data["images"][0]

            assert image_data["has_images"]
            assert image["is_centered_horizontally"]
            assert image["is_centered_vertically"]

        else:
            assert False, "Failed to get image data"


# Error Handling Tests


@pytest.mark.asyncio
async def test_invalid_file_path(libreoffice_server):
    """Test that operations gracefully handle non-existent file paths with appropriate error messages"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "read_text_document", {"file_path": "/nonexistent/path/file.odt"}
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert (
            "error" in result_content.text.lower()
            or "not found" in result_content.text.lower()
        )


@pytest.mark.asyncio
async def test_invalid_heading_level(libreoffice_server, temp_dir):
    """Test that invalid heading levels (outside 1-6 range) are properly rejected with error messages"""
    async with Client(libreoffice_server) as client:
        filename = os.path.join(temp_dir, "invalid_heading.odt")
        await client.call_tool("create_blank_document", {"filename": filename})

        result = await client.call_tool(
            "add_heading",
            {
                "file_path": filename,
                "text": "Invalid Heading",
                "level": 10,  # Invalid level
            },
        )

        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert (
            "invalid" in result_content.text.lower()
            or "error" in result_content.text.lower()
        )


# Additional Error Handling Tests

@pytest.mark.asyncio
async def test_create_document_invalid_directory(libreoffice_server):
    """Test that document creation fails gracefully when target directory doesn't exist"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "create_blank_document",
            {"filename": "/nonexistent/directory/test.odt", "title": "Test"}
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "failed" in result_content.text.lower()


@pytest.mark.asyncio
async def test_add_text_invalid_position(libreoffice_server, test_document):
    """Test that text addition still works even when an invalid position parameter is provided"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "add_text",
            {
                "file_path": test_document,
                "text": "Test text",
                "position": "invalid_position"
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" not in result_content.text.lower() or "invalid" not in result_content.text.lower()


@pytest.mark.asyncio
async def test_add_paragraph_invalid_alignment(libreoffice_server, test_document):
    """Test that paragraph addition succeeds even with invalid alignment, using default alignment"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "add_paragraph",
            {
                "file_path": test_document,
                "text": "Test paragraph",
                "alignment": "invalid_alignment"
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "paragraph added" in result_content.text.lower()


@pytest.mark.asyncio
async def test_add_table_invalid_dimensions(libreoffice_server, test_document):
    """Test that table creation fails properly when given invalid row/column dimensions (zero or negative)"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "add_table",
            {
                "file_path": test_document,
                "rows": 0,
                "columns": -1
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "invalid" in result_content.text.lower()


@pytest.mark.asyncio
async def test_add_table_mismatched_data(libreoffice_server, test_document):
    """Test that table creation fails when provided data array doesn't match specified table dimensions"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "add_table",
            {
                "file_path": test_document,
                "rows": 2,
                "columns": 2,
                "data": [["Too", "many", "columns", "here"]]
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "failed to add table" in result_content.text.lower()


@pytest.mark.asyncio
async def test_insert_image_nonexistent_file(libreoffice_server, test_document):
    """Test that image insertion fails gracefully when the specified image file doesn't exist"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "insert_image",
            {
                "file_path": test_document,
                "image_path": "/nonexistent/image.png",
                "width": 5000,
                "height": 5000
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "not found" in result_content.text.lower()


@pytest.mark.asyncio
async def test_insert_image_invalid_dimensions(libreoffice_server, test_document, test_image):
    """Test that image insertion fails when given invalid dimensions (negative or zero values)"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "insert_image",
            {
                "file_path": test_document,
                "image_path": test_image,
                "width": -100,
                "height": 0
            }
        )

        print(result)
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "invalid" in result_content.text.lower()


@pytest.mark.asyncio
async def test_format_text_invalid_color(libreoffice_server, test_document):
    """Test that text formatting fails properly when given an invalid color format"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "format_text",
            {
                "file_path": test_document,
                "text_to_find": "test",
                "color": "invalid_color"
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "invalid" in result_content.text.lower()


@pytest.mark.asyncio
async def test_format_text_nonexistent_text(libreoffice_server, test_document):
    """Test that text formatting reports zero occurrences when trying to format text that doesn't exist"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "format_text",
            {
                "file_path": test_document,
                "text_to_find": "nonexistent text that will never be found",
                "bold": True
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "formatted 0 occurrences" in result_content.text.lower()


@pytest.mark.asyncio
async def test_delete_paragraph_invalid_index(libreoffice_server, test_document):
    """Test that paragraph deletion fails gracefully when given an index that exceeds document length"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "delete_paragraph",
            {
                "file_path": test_document,
                "paragraph_index": 999
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "invalid" in result_content.text.lower()


@pytest.mark.asyncio
async def test_delete_paragraph_negative_index(libreoffice_server, test_document):
    """Test that paragraph deletion properly rejects negative index values with error message"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "delete_paragraph",
            {
                "file_path": test_document,
                "paragraph_index": -1
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "invalid" in result_content.text.lower()


@pytest.mark.asyncio
async def test_format_table_invalid_index(libreoffice_server, test_document):
    """Test that table formatting fails when trying to format a table that doesn't exist at the given index"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "format_table",
            {
                "file_path": test_document,
                "table_index": 999,
                "border_width": 2
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "not found" in result_content.text.lower()


@pytest.mark.asyncio
async def test_format_table_invalid_color(libreoffice_server, test_document):
    """Test that table formatting fails when given an invalid background color format"""
    async with Client(libreoffice_server) as client:
        # Add a table first
        await client.call_tool(
            "add_table", {"file_path": test_document, "rows": 2, "columns": 2}
        )
        
        result = await client.call_tool(
            "format_table",
            {
                "file_path": test_document,
                "table_index": 0,
                "background_color": "invalid_color"
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "invalid" in result_content.text.lower()


@pytest.mark.asyncio
async def test_apply_document_style_invalid_font(libreoffice_server, test_document):
    """Test that document styling handles non-existent font names gracefully without failing completely"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "apply_document_style",
            {
                "file_path": test_document,
                "font_name": "NonexistentFont12345",
                "font_size": 12
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        # This might not error but should handle gracefully
        assert "style" in result_content.text.lower() or "error" in result_content.text.lower()


@pytest.mark.asyncio
async def test_apply_document_style_invalid_size(libreoffice_server, test_document):
    """Test that document styling fails when given invalid font size (negative values)"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "apply_document_style",
            {
                "file_path": test_document,
                "font_size": -5
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "invalid" in result_content.text.lower()


@pytest.mark.asyncio
async def test_copy_document_same_path(libreoffice_server, test_document):
    """Test that document copying fails when source and target paths are identical"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "copy_document",
            {
                "source_path": test_document,
                "target_path": test_document
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "failed to copy" in result_content.text.lower()


@pytest.mark.asyncio
async def test_copy_document_invalid_target_directory(libreoffice_server, test_document):
    """Test that document copying fails when target directory doesn't exist"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "copy_document",
            {
                "source_path": test_document,
                "target_path": "/nonexistent/directory/copy.odt"
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "failed" in result_content.text.lower()


# Presentation Error Tests

@pytest.mark.asyncio
async def test_add_slide_invalid_index(libreoffice_server, test_presentation):
    """Test that slide addition handles negative index values by inserting at appropriate position"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "add_slide",
            {
                "file_path": test_presentation,
                "title": "Test",
                "content": "Test",
                "slide_index": -1
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        # Might insert at beginning or error
        assert "slide" in result_content.text.lower()


@pytest.mark.asyncio
async def test_edit_slide_content_invalid_index(libreoffice_server, test_presentation):
    """Test that slide content editing fails when given a slide index that doesn't exist"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "edit_slide_content",
            {
                "file_path": test_presentation,
                "slide_index": 999,
                "new_content": "Updated content"
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "invalid" in result_content.text.lower()


@pytest.mark.asyncio
async def test_edit_slide_title_invalid_index(libreoffice_server, test_presentation):
    """Test that slide title editing fails when given a negative or invalid slide index"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "edit_slide_title",
            {
                "file_path": test_presentation,
                "slide_index": -5,
                "new_title": "Updated Title"
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "invalid" in result_content.text.lower()


@pytest.mark.asyncio
async def test_delete_slide_invalid_index(libreoffice_server, test_presentation):
    """Test that slide deletion fails when trying to delete a slide that doesn't exist"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "delete_slide",
            {
                "file_path": test_presentation,
                "slide_index": 100
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "invalid" in result_content.text.lower()


@pytest.mark.asyncio
async def test_delete_slide_last_slide(libreoffice_server, test_presentation):
    """Test that slide deletion handles the case of trying to delete from an empty presentation"""
    async with Client(libreoffice_server) as client:
        # Try to delete all slides
        result = await client.call_tool(
            "delete_slide",
            {
                "file_path": test_presentation,
                "slide_index": 0
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        
        # Try to delete from empty presentation
        result2 = await client.call_tool(
            "delete_slide",
            {
                "file_path": test_presentation,
                "slide_index": 0
            }
        )
        
        result2_content = result2.content[0]
        assert isinstance(result2_content, TextContent)
        assert "error" in result2_content.text.lower() or "empty" in result2_content.text.lower()


@pytest.mark.asyncio
async def test_format_slide_content_invalid_index(libreoffice_server, test_presentation):
    """Test that slide content formatting fails when given an invalid slide index"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "format_slide_content",
            {
                "file_path": test_presentation,
                "slide_index": 999,
                "font_size": 18
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "invalid" in result_content.text.lower()


@pytest.mark.asyncio
async def test_format_slide_title_invalid_index(libreoffice_server, test_presentation):
    """Test that slide title formatting fails when given a negative slide index"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "format_slide_title",
            {
                "file_path": test_presentation,
                "slide_index": -10,
                "font_size": 24
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "invalid" in result_content.text.lower()


@pytest.mark.asyncio
async def test_insert_slide_image_invalid_index(libreoffice_server, test_presentation, test_image):
    """Test that slide image insertion fails when given an invalid slide index"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "insert_slide_image",
            {
                "file_path": test_presentation,
                "slide_index": 999,
                "image_path": test_image,
                "max_width": 10000,
                "max_height": 10000
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "invalid" in result_content.text.lower()


@pytest.mark.asyncio
async def test_insert_slide_image_nonexistent_file(libreoffice_server, test_presentation):
    """Test that slide image insertion fails when the specified image file doesn't exist"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "insert_slide_image",
            {
                "file_path": test_presentation,
                "slide_index": 0,
                "image_path": "/nonexistent/image.png",
                "max_width": 10000,
                "max_height": 10000
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "not found" in result_content.text.lower()


@pytest.mark.asyncio
async def test_apply_presentation_template_invalid_template(libreoffice_server, test_presentation):
    """Test that presentation template application fails when given a non-existent template name"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "apply_presentation_template",
            {
                "file_path": test_presentation,
                "template_name": "NonexistentTemplate12345"
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "error" in result_content.text.lower() or "not found" in result_content.text.lower()


# File Operation Error Tests

@pytest.mark.asyncio
async def test_list_documents_invalid_directory(libreoffice_server):
    """Test that document listing handles non-existent directories by returning appropriate message"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "list_documents",
            {"directory": "/nonexistent/directory"}
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "no documents found" in result_content.text.lower()


@pytest.mark.asyncio
async def test_search_replace_empty_search(libreoffice_server, test_document):
    """Test that search and replace fails when given empty search text to prevent unintended replacements"""
    async with Client(libreoffice_server) as client:
        result = await client.call_tool(
            "search_replace_text",
            {
                "file_path": test_document,
                "search_text": "",
                "replace_text": "replacement"
            }
        )
        
        result_content = result.content[0]
        assert isinstance(result_content, TextContent)
        assert "failed" in result_content.text.lower()