"""
Unit tests for the RAG Document Assistant
"""

import unittest
from unittest.mock import patch, MagicMock

class TestOrchestrator(unittest.TestCase):
    
    @patch('src.orchestrator.pinecone_search')
    @patch('src.orchestrator.call_llm')
    def test_orchestrate_query_success(self, mock_call_llm, mock_pinecone_search):
        """Test successful query orchestration"""
        # Mock the retrieval function
        mock_pinecone_search.return_value = [
            {
                "id": "doc1",
                "score": 0.85,
                "text": "This is a sample document chunk about GDPR regulations.",
                "metadata": {"source": "gdpr.pdf"}
            }
        ]
        
        # Mock the LLM function
        mock_call_llm.return_value = {
            "text": "GDPR is a regulation about data protection.",
            "meta": {"provider": "gemini", "model": "gemini-1.5-flash"}
        }
        
        # Import after mocking
        from src.orchestrator import orchestrate_query
        
        # Test the function
        result = orchestrate_query("What is GDPR?", top_k=1)
        
        # Assertions
        self.assertIn('answer', result)
        self.assertIn('sources', result)
        self.assertIn('citations', result)
        self.assertEqual(result['answer'], "GDPR is a regulation about data protection.")
        
        # Verify mocks were called
        mock_pinecone_search.assert_called_once()
        mock_call_llm.assert_called_once()

    def test_orchestrate_query_invalid_input(self):
        """Test query orchestration with invalid input"""
        from src.orchestrator import orchestrate_query
        
        # Test with empty query
        result = orchestrate_query("")
        self.assertEqual(result['answer'], "")
        
        # Test with None query
        result = orchestrate_query(None)
        self.assertEqual(result['answer'], "")

if __name__ == '__main__':
    unittest.main()