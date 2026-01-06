#!/usr/bin/env python3
"""
Health check script for RAG Document Assistant
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.orchestrator import orchestrate_query

def health_check():
    """Perform a basic health check of the RAG system"""
    print("RAG Document Assistant - Health Check")
    print("=" * 35)
    
    try:
        # Test basic functionality
        test_query = "What is machine learning?"
        result = orchestrate_query(test_query, top_k=1)
        print("✓ Basic query functionality working")
        
        # Check if we got an answer
        if result.get('answer'):
            print("✓ Answer generation successful")
        else:
            print("⚠ No answer generated")
        
        # Check sources
        if result.get('sources'):
            print("✓ Document retrieval successful")
        else:
            print("⚠ No sources retrieved")
        
        print("\nHealth check completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

if __name__ == "__main__":
    success = health_check()
    sys.exit(0 if success else 1)