#!/usr/bin/env python3
"""
Smoke Tests for Football Match Tracking System

This module provides a set of core smoke tests to verify the basic functionality
of the Football Match Tracking System before making any significant changes.

Usage:
    python -m tests.smoke_tests
"""

import os
import sys
import unittest
import json
import asyncio
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Set non-strict logging for tests
os.environ['LOG_STRICT'] = '0'

# Import key modules
from log_config import get_logger, get_summary_logger
import pure_json_fetch_cache
import merge_logic
from orchestrate_complete import write_summary_json

# Set up test logger
logger = get_logger("smoke_tests")

class FootballTrackingSystemSmokeTests(unittest.TestCase):
    """Core smoke tests for the Football Match Tracking System."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures and sample data."""
        # Create sample data for testing
        cls.sample_match_data = [{
            "id": "test_match_1",
            "status": "IN_PROGRESS",
            "homeTeam": {"name": "Team A", "score": 1},
            "awayTeam": {"name": "Team B", "score": 0},
            "competition": {"name": "Test League"},
            "startTime": "2025-05-18T01:00:00Z",
            "minute": 45
        }]
        
        # Path for test output files
        cls.test_dir = Path(__file__).parent / "test_output"
        cls.test_dir.mkdir(exist_ok=True)
        
    def test_1_logging_system(self):
        """Test that the logging system is properly initialized."""
        # Test standard logger
        test_logger = get_logger("test_component")
        self.assertEqual(test_logger.name, "test_component")
        
        # Test summary logger
        # line 62: Update test to use required name parameter
        summary_logger = get_summary_logger("smoke_test")
        self.assertEqual(summary_logger.name, "summary")
        
        # Log some test messages
        test_logger.info("Standard logger test message")
        summary_logger.info("Summary logger test message")
        
        logger.info("✓ Logging system passed basic initialization")
    
    def test_2_json_cache_functionality(self):
        """Test basic functionality of the JSON cache module."""
        # Test that we can initialize the cache
        cache = pure_json_fetch_cache.init_cache()
        self.assertIsNotNone(cache)
        
        # Test save and load operations
        test_data = {"test": "data", "timestamp": "2025-05-18T01:00:00Z"}
        test_cache_file = self.test_dir / "test_cache.json"
        
        with open(test_cache_file, "w") as f:
            json.dump(test_data, f)
            
        loaded_data = pure_json_fetch_cache.load_json_file(test_cache_file)
        self.assertEqual(loaded_data, test_data)
        
        logger.info("✓ JSON cache module passed basic functionality tests")
    
    def test_3_merge_logic(self):
        """Test that the merge logic functions correctly."""
        # Test the enrichment process
        enriched_data = merge_logic.enrich_match_data(self.sample_match_data)
        self.assertIsNotNone(enriched_data)
        
        # Verify key fields are present after enrichment
        match = enriched_data[0]
        self.assertIn("id", match)
        self.assertIn("status", match)
        self.assertIn("homeTeam", match)
        self.assertIn("awayTeam", match)
        
        logger.info("✓ Merge logic passed basic functionality tests")
    
    def test_4_summary_generation(self):
        """Test that the summary generation works."""
        # Generate a summary from our test data
        summary = write_summary_json(self.sample_match_data)
        self.assertIsNotNone(summary)
        
        # Verify the summary structure
        self.assertIn("matches", summary)
        self.assertIn("generated_at", summary)
        
        logger.info("✓ Summary generation passed basic functionality tests")
    
    @unittest.skip("Integration test requires full environment")
    def test_5_full_pipeline_integration(self):
        """
        Integration test for the full pipeline.
        
        This test is skipped by default as it requires the full environment.
        Remove the @unittest.skip decorator to run it.
        """
        from orchestrate_complete import run_complete_pipeline
        
        # Run the pipeline and verify it completes without errors
        result = asyncio.run(run_complete_pipeline())
        self.assertTrue(result)

def run_all_tests():
    """Run all smoke tests and report results."""
    print("\n📋 Running Football Match Tracking System Smoke Tests...")
    suite = unittest.TestLoader().loadTestsFromTestCase(FootballTrackingSystemSmokeTests)
    
    # Create a test runner that will output to console
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n✅ All smoke tests passed successfully!")
        return 0
    else:
        print("\n❌ Some smoke tests failed! Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
