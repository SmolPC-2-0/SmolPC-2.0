#!/usr/bin/env python
import os
import time
import traceback
import logging
import sys
from contextlib import contextmanager

# Set up logging immediately when this module is imported
def _setup_module_logging():
    """Internal function to set up logging for this module."""
    try:
        # Get the directory of this file
        module_dir = os.path.dirname(__file__)
        log_path = os.path.join(module_dir, "helper.log")
        
        # Clear existing handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # Configure logging
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            force=True,
            filemode='a'
        )
        
        # Test logging
        logging.info("="*50)
        logging.info(f"helper_utils module loaded - logging to: {log_path}")
        
    except Exception as e:
        print(f"Failed to set up logging in helper_utils: {e}")
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            stream=sys.stdout
        )

# Call the setup function
_setup_module_logging()

try:
    print("Importing UNO...")
    logging.info("Importing UNO...")
    import uno
    from com.sun.star.beans import PropertyValue
    from com.sun.star.connection import NoConnectException

    print("UNO imported successfully!")
    logging.info("UNO imported successfully!")
except ImportError as e:
    print(f"UNO Import Error: {e}")
    logging.error(f"UNO Import Error: {e}")
    print("This script must be run with LibreOffice's Python.")
    logging.error("This script must be run with LibreOffice's Python.")
    sys.exit(1)


class HelperError(Exception):
    pass


@contextmanager
def managed_document(file_path, read_only=False):
    doc, message = open_document(file_path, read_only)
    if not doc:
        raise HelperError(message)
    try:
        yield doc
    finally:
        try:
            doc.close(True)
        except Exception:
            pass


# Helper functions


def ensure_directory_exists(file_path):
    """Ensure the directory for a file exists, creating it if necessary."""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")
        except Exception as e:
            print(f"Failed to create directory {directory}: {str(e)}")
            return False
    return True


def normalize_path(file_path):
    """Convert a relative path to an absolute path."""
    if not file_path:
        return None

    # If file path is already complete, return it
    if file_path.startswith(("file://", "http://", "https://", "ftp://")):
        return file_path

    # Expand user directory if path starts with ~
    if file_path.startswith("~"):
        file_path = os.path.expanduser(file_path)

    # Make absolute if relative
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)

    print(f"Normalized path: {file_path}")
    return file_path


def get_uno_desktop():
    """Get LibreOffice desktop object."""
    try:
        local_context = uno.getComponentContext()
        resolver = local_context.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", local_context
        )

        # Try both localhost and 127.0.0.1
        try:
            context = resolver.resolve(
                "uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext"
            )
        except NoConnectException:
            context = resolver.resolve(
                "uno:socket,host=127.0.0.1,port=2002;urp;StarOffice.ComponentContext"
            )

        desktop = context.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", context
        )
        return desktop
    except Exception as e:
        print(f"Failed to get UNO desktop: {str(e)}")
        print(traceback.format_exc())
        return None


def create_property_value(name, value):
    """Create a PropertyValue with given name and value."""
    prop = PropertyValue()
    prop.Name = name
    prop.Value = value
    return prop


def open_document(file_path, read_only=False, retries=3, delay=0.5):
    print(f"Opening document: {file_path} (read_only: {read_only})")
    normalized_path = normalize_path(file_path)
    if not normalized_path.startswith(("file://", "http://", "https://", "ftp://")):
        if not os.path.exists(normalized_path):
            raise HelperError(f"Document not found: {normalized_path}")
        file_url = uno.systemPathToFileUrl(normalized_path)
    else:
        file_url = normalized_path

    desktop = get_uno_desktop()
    if not desktop:
        raise HelperError("Failed to connect to LibreOffice desktop")

    last_exception = None
    for attempt in range(retries):
        try:
            props = [
                create_property_value("Hidden", True),
                create_property_value("ReadOnly", read_only),
            ]
            doc = desktop.loadComponentFromURL(file_url, "_blank", 0, tuple(props))
            if not doc:
                raise HelperError(f"Failed to load document: {file_path}")
            return doc, "Success"
        except Exception as e:
            last_exception = e
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(delay)
    raise last_exception
