"""
Utility for reading text files from disk.
"""

from app.core.exceptions.exception import ParsingError
from app.core.interfaces.file_reader import IFileReader



class FileReader(IFileReader):
    """
    Reads text files from disk and handles file errors.
    """

    def read_file(self, file_path: str) -> str:
        """
        Read the contents of a text file. Raises ParsingError on failure.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError as exc:
            raise ParsingError(f"File not found: {file_path}") from exc
        except IOError as e:
            raise ParsingError(f"Error reading file {file_path}: {str(e)}") from e
        except UnicodeDecodeError as e:
            raise ParsingError(f"Error decoding file {file_path}: {str(e)}") from e
