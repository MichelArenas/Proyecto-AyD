from abc import ABC, abstractmethod


class IFileReader(ABC):
    """Interface for file reading

    This interface defines the contract for reading files. It ensures that any
    implementation provides a method to read the content of a file given its path.
    """

    @abstractmethod
    def read_file(self, file_path: str) -> str:
        """Reads the content of a file"""
