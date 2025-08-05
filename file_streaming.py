"""
File handling utilities for the Essay Revision Application
Provides streaming capabilities for large file uploads and processing
"""
import os
import io
import logging
from typing import Generator, Union, BinaryIO, TextIO
from werkzeug.datastructures import FileStorage
from config import Config

logger = logging.getLogger(__name__)

class FileStreamer:
    """
    File streaming utility for handling large file uploads efficiently
    """
    
    def __init__(self, chunk_size: int = None, memory_threshold: int = None):
        """
        Initialize FileStreamer
        
        Args:
            chunk_size (int): Size of chunks for streaming (default from config)
            memory_threshold (int): Threshold for switching to streaming (default from config)
        """
        self.chunk_size = chunk_size or Config.PERFORMANCE.get('file_chunk_size', 8192)
        self.memory_threshold = memory_threshold or Config.PERFORMANCE.get('file_memory_threshold', 1024 * 1024)
    
    def should_stream(self, file_size: int) -> bool:
        """
        Determine if a file should be streamed based on size
        
        Args:
            file_size (int): Size of the file in bytes
            
        Returns:
            bool: True if file should be streamed
        """
        return (Config.PERFORMANCE.get('file_streaming_enabled', True) and 
                file_size > self.memory_threshold)
    
    def stream_file_chunks(self, file_obj: Union[BinaryIO, TextIO, FileStorage]) -> Generator[bytes, None, None]:
        """
        Stream file content in chunks
        
        Args:
            file_obj: File object to stream
            
        Yields:
            bytes: File chunks
        """
        try:
            while True:
                chunk = file_obj.read(self.chunk_size)
                if not chunk:
                    break
                
                # Ensure we're yielding bytes
                if isinstance(chunk, str):
                    chunk = chunk.encode('utf-8')
                
                yield chunk
        except Exception as e:
            logger.error(f"Error streaming file: {e}")
            raise
    
    def read_file_streaming(self, file_path: str) -> Generator[str, None, None]:
        """
        Read a file in streaming mode, yielding text chunks
        
        Args:
            file_path (str): Path to the file
            
        Yields:
            str: Text chunks from the file
        """
        try:
            file_size = os.path.getsize(file_path)
            
            if not self.should_stream(file_size):
                # File is small, read entirely into memory
                with open(file_path, 'r', encoding='utf-8') as f:
                    yield f.read()
                return
            
            # Stream the file
            logger.info(f"Streaming file {file_path} (size: {file_size} bytes)")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise
    
    def save_uploaded_file_streaming(self, file_storage: FileStorage, save_path: str) -> bool:
        """
        Save an uploaded file using streaming to avoid loading into memory
        
        Args:
            file_storage (FileStorage): Uploaded file from Flask
            save_path (str): Path where to save the file
            
        Returns:
            bool: True if saved successfully
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Check if we should stream based on content length
            content_length = file_storage.content_length
            if content_length and self.should_stream(content_length):
                logger.info(f"Streaming upload to {save_path} (size: {content_length} bytes)")
                
                with open(save_path, 'wb') as output_file:
                    for chunk in self.stream_file_chunks(file_storage):
                        output_file.write(chunk)
            else:
                # Small file, save normally
                file_storage.save(save_path)
            
            logger.info(f"File saved successfully to {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving uploaded file to {save_path}: {e}")
            return False
    
    def extract_text_from_file_streaming(self, file_path: str, file_type: str = None) -> str:
        """
        Extract text from a file using streaming for large files
        
        Args:
            file_path (str): Path to the file
            file_type (str): Type of file ('txt', 'docx', etc.)
            
        Returns:
            str: Extracted text content
        """
        if not file_type:
            file_type = os.path.splitext(file_path)[1].lower().lstrip('.')
        
        try:
            if file_type == 'txt':
                return self._extract_txt_streaming(file_path)
            elif file_type == 'docx':
                return self._extract_docx_streaming(file_path)
            else:
                logger.warning(f"Unsupported file type: {file_type}")
                return ""
                
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return ""
    
    def _extract_txt_streaming(self, file_path: str) -> str:
        """
        Extract text from a .txt file using streaming
        
        Args:
            file_path (str): Path to the text file
            
        Returns:
            str: File content
        """
        content_chunks = []
        total_length = 0
        max_length = Config.ERROR_HANDLING.get('file_max_text_length', 50000)
        
        for chunk in self.read_file_streaming(file_path):
            content_chunks.append(chunk)
            total_length += len(chunk)
            
            # Prevent reading extremely large files
            if total_length > max_length:
                logger.warning(f"File {file_path} too large, truncating at {max_length} characters")
                break
        
        return ''.join(content_chunks)[:max_length]
    
    def _extract_docx_streaming(self, file_path: str) -> str:
        """
        Extract text from a .docx file
        Note: python-docx doesn't support streaming, so we read the entire file
        
        Args:
            file_path (str): Path to the docx file
            
        Returns:
            str: Extracted text
        """
        try:
            from docx import Document
            
            file_size = os.path.getsize(file_path)
            
            # For very large DOCX files, we might want to implement additional checks
            if file_size > self.memory_threshold * 10:  # 10x the normal threshold
                logger.warning(f"DOCX file {file_path} is very large ({file_size} bytes), this may consume significant memory")
            
            doc = Document(file_path)
            
            paragraphs = []
            total_length = 0
            max_length = Config.ERROR_HANDLING.get('file_max_text_length', 50000)
            
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    paragraphs.append(text)
                    total_length += len(text)
                    
                    # Prevent processing extremely large documents
                    if total_length > max_length:
                        logger.warning(f"DOCX file {file_path} too large, truncating at {max_length} characters")
                        break
            
            content = '\n'.join(paragraphs)
            return content[:max_length]
            
        except ImportError:
            logger.error("python-docx library not available for DOCX file processing")
            return ""
        except Exception as e:
            logger.error(f"Error extracting text from DOCX file {file_path}: {e}")
            return ""

# Global file streamer instance
file_streamer = FileStreamer()

def should_stream_file(file_size: int) -> bool:
    """
    Check if a file should be streamed based on size
    
    Args:
        file_size (int): File size in bytes
        
    Returns:
        bool: True if file should be streamed
    """
    return file_streamer.should_stream(file_size)

def save_uploaded_file(file_storage: FileStorage, save_path: str) -> bool:
    """
    Save an uploaded file using streaming if appropriate
    
    Args:
        file_storage (FileStorage): Uploaded file
        save_path (str): Path to save the file
        
    Returns:
        bool: True if saved successfully
    """
    return file_streamer.save_uploaded_file_streaming(file_storage, save_path)

def extract_text_from_file(file_path: str, file_type: str = None) -> str:
    """
    Extract text from a file using streaming for large files
    
    Args:
        file_path (str): Path to the file
        file_type (str): Type of file
        
    Returns:
        str: Extracted text
    """
    return file_streamer.extract_text_from_file_streaming(file_path, file_type)

def get_file_streaming_stats() -> dict:
    """
    Get file streaming configuration and stats
    
    Returns:
        dict: File streaming information
    """
    return {
        'streaming_enabled': Config.PERFORMANCE.get('file_streaming_enabled', True),
        'chunk_size': file_streamer.chunk_size,
        'memory_threshold': file_streamer.memory_threshold,
        'memory_threshold_mb': file_streamer.memory_threshold / (1024 * 1024)
    }
