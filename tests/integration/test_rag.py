"""
Integration tests for the RAG Document Assistant
"""

import unittest
import os

class TestRAGIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment before each test method."""
        # Add the parent directory to the path
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
    
    def test_embedding_generation(self):
        """Test embedding generation functionality"""
        try:
            from src.ingestion.embeddings import get_embedding
            
            # Test with a simple text
            text = "This is a test sentence for embedding."
            embedding = get_embedding(text)
            
            # Check that we got a list of floats
            self.assertIsInstance(embedding, list)
            self.assertGreater(len(embedding), 0)
            self.assertIsInstance(embedding[0], float)
            
        except ImportError:
            # Skip if dependencies are not available
            self.skipTest("Embedding dependencies not available")
    
    def test_chunking_functionality(self):
        """Test text chunking functionality"""
        try:
            from src.ingestion.chunker import chunk_text
            
            # Test with a longer text
            text = "This is the first sentence. " * 200  # Create a long text
            chunks = chunk_text(text, chunk_size=100, overlap=10)
            
            # Check that we got chunks
            self.assertIsInstance(chunks, list)
            self.assertGreater(len(chunks), 0)
            self.assertIsInstance(chunks[0], str)
            
        except ImportError:
            # Skip if dependencies are not available
            self.skipTest("Chunking dependencies not available")

if __name__ == '__main__':
    unittest.main()