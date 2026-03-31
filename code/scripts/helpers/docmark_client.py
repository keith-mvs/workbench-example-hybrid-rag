"""
Client for docmark MCP server.
Handles document preprocessing before RAG ingestion.
"""

import os
import requests
from pathlib import Path
from typing import List, Dict, Optional, Literal
import json
import logging

logger = logging.getLogger(__name__)


class DocmarkClient:
    """
    Client for communicating with docmark MCP server.
    
    Usage:
        client = DocmarkClient(server_url="http://localhost:8001")
        result = client.convert_document(
            file_path="doc.pdf",
            rag_mode=True,
            rag_cleaning_level="medium"
        )
    """
    
    def __init__(
        self,
        server_url: str = None,
        timeout: int = 300,
        verify_ssl: bool = False
    ):
        """
        Initialize docmark client.
        
        Args:
            server_url: URL of docmark MCP HTTP bridge
                       Default: Read from DOCMARK_SERVER_URL env var or localhost:8001
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.server_url = server_url or os.getenv(
            'DOCMARK_SERVER_URL',
            'http://localhost:8001'
        )
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        
        # Remove trailing slash
        self.server_url = self.server_url.rstrip('/')
        
        logger.info(f"DocmarkClient initialized: {self.server_url}")
    
    def health_check(self) -> bool:
        """Check if docmark server is available."""
        try:
            response = requests.get(
                f"{self.server_url}/health",
                timeout=5,
                verify=self.verify_ssl
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def convert_document(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        enhanced_pdf: bool = True,
        preflight: bool = True,
        ocr: bool = False,
        rag_mode: bool = True,
        rag_cleaning_level: Literal["light", "medium", "aggressive"] = "medium",
        rag_chunk_hints: bool = True,
        rag_metadata: bool = True,
    ) -> Dict:
        """
        Convert a document using docmark MCP server.
        
        Args:
            file_path: Path to document to convert
            output_path: Optional output path for markdown
            enhanced_pdf: Use enhanced PDF processing
            preflight: Run PDF validation/repair
            ocr: Enable OCR for scanned pages
            rag_mode: Enable RAG optimization
            rag_cleaning_level: Cleaning intensity (light/medium/aggressive)
            rag_chunk_hints: Add chunk boundary markers
            rag_metadata: Add RAG-specific front-matter
        
        Returns:
            Dict with status, output_file, and metadata
        
        Raises:
            requests.RequestException: If server communication fails
            ValueError: If conversion fails
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Prepare request payload
        payload = {
            "file_path": str(file_path.absolute()),
            "enhanced_pdf": enhanced_pdf,
            "preflight": preflight,
            "ocr": ocr,
            "rag_mode": rag_mode,
            "rag_cleaning_level": rag_cleaning_level,
            "rag_chunk_hints": rag_chunk_hints,
            "rag_metadata": rag_metadata,
        }
        
        if output_path:
            payload["output_path"] = str(Path(output_path).absolute())
        
        # Call MCP server
        try:
            response = requests.post(
                f"{self.server_url}/convert",
                json=payload,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("status") == "error":
                raise ValueError(f"Conversion failed: {result.get('error')}")
            
            logger.info(f"Converted: {file_path.name} -> {result.get('output_file')}")
            return result
            
        except requests.RequestException as e:
            logger.error(f"MCP server request failed: {e}")
            raise
    
    def batch_convert_directory(
        self,
        root_dir: str,
        output_dir: str,
        file_types: List[str] = None,
        parallel: int = 4,
        rag_mode: bool = True,
        rag_cleaning_level: str = "medium",
    ) -> Dict:
        """
        Batch convert all documents in a directory.
        
        Args:
            root_dir: Directory to scan for documents
            output_dir: Output directory for converted files
            file_types: List of extensions to process (default: pdf, docx, xlsx, csv)
            parallel: Number of parallel workers
            rag_mode: Enable RAG optimization
            rag_cleaning_level: Cleaning intensity
        
        Returns:
            Dict with conversion statistics and results
        """
        if file_types is None:
            file_types = ["pdf", "docx", "xlsx", "csv"]
        
        payload = {
            "root_dir": str(Path(root_dir).absolute()),
            "output_dir": str(Path(output_dir).absolute()),
            "file_types": file_types,
            "parallel": parallel,
            "rag_mode": rag_mode,
            "rag_cleaning_level": rag_cleaning_level,
        }
        
        try:
            response = requests.post(
                f"{self.server_url}/batch_convert",
                json=payload,
                timeout=self.timeout * 10,  # Longer timeout for batch
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(
                f"Batch conversion complete: {result.get('success', 0)}/{result.get('total', 0)} files"
            )
            return result
            
        except requests.RequestException as e:
            logger.error(f"Batch conversion failed: {e}")
            raise


# Convenience function for one-off conversions
def preprocess_for_rag(
    file_path: str,
    output_path: Optional[str] = None,
    cleaning_level: str = "medium",
    server_url: Optional[str] = None
) -> str:
    """
    Preprocess a single document for RAG.
    
    Args:
        file_path: Path to document
        output_path: Optional output path
        cleaning_level: light/medium/aggressive
        server_url: docmark server URL (default: env var or localhost)
    
    Returns:
        Path to preprocessed markdown file
    """
    client = DocmarkClient(server_url=server_url)
    
    # Check server availability
    if not client.health_check():
        raise ConnectionError(
            f"docmark server not available at {client.server_url}. "
            "Please start the MCP server (see docmark-mcp-server-setup.md)"
        )
    
    result = client.convert_document(
        file_path=file_path,
        output_path=output_path,
        rag_mode=True,
        rag_cleaning_level=cleaning_level,
        enhanced_pdf=True,
        preflight=True,
    )
    
    return result["output_file"]


if __name__ == "__main__":
    # Test the client
    import sys
    
    client = DocmarkClient()
    
    print(f"Testing connection to: {client.server_url}")
    if client.health_check():
        print("✅ Server is healthy!")
    else:
        print("❌ Server not available")
        print("   Start the docmark MCP server first:")
        print("   Windows: python -m docmark.mcp_http_server")
        sys.exit(1)
    
    # Test conversion if file provided
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        print(f"\nTesting conversion: {test_file}")
        
        try:
            result = preprocess_for_rag(test_file, cleaning_level="medium")
            print(f"✅ Conversion successful!")
            print(f"   Output: {result}")
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
            sys.exit(1)
