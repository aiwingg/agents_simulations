#!/usr/bin/env python3
"""
Test script for prompt specification management functionality
"""
import pytest
pytest.skip("legacy integration script", allow_module_level=True)

import os
import sys
import json
import tempfile
import shutil

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from prompt_specification import PromptSpecificationManager

def test_prompt_specification_manager():
    """Test the PromptSpecificationManager functionality"""
    print("Testing PromptSpecificationManager...")
    
    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp()
    print(f"Using test directory: {test_dir}")
    
    try:
        # Initialize manager with test directory
        manager = PromptSpecificationManager()
        original_dir = manager.prompts_dir
        manager.prompts_dir = test_dir
        
        # Test 1: Create a sample specification
        print("\n1. Testing specification creation...")
        sample_spec = {
            "name": "Test Specification",
            "version": "1.0.0",
            "description": "Test configuration",
            "agents": {
                "agent": {
                    "name": "Test Agent",
                    "prompt": "You are a test agent.",
                    "tools": ["rag_find_products", "add_to_cart"],
                    "description": "Agent for testing"
                },
                "client": {
                    "name": "Test Client",
                    "prompt": "You are a test client.",
                    "tools": [],
                    "description": "Client for testing"
                },
                "evaluator": {
                    "name": "Test Evaluator",
                    "prompt": "You are a test evaluator.",
                    "tools": [],
                    "description": "Evaluator for testing"
                }
            }
        }
        
        manager.save_specification("test_spec", sample_spec)
        print("✓ Specification saved successfully")
        
        # Test 2: Check if specification exists
        print("\n2. Testing specification existence check...")
        assert manager.specification_exists("test_spec"), "Specification should exist"
        assert not manager.specification_exists("non_existent"), "Non-existent specification should not exist"
        print("✓ Existence check works correctly")
        
        # Test 3: Retrieve specification contents
        print("\n3. Testing specification retrieval...")
        retrieved_spec = manager.get_specification_contents("test_spec")
        assert retrieved_spec["name"] == "Test Specification", "Retrieved name should match"
        assert retrieved_spec["version"] == "1.0.0", "Retrieved version should match"
        assert "agent" in retrieved_spec["agents"], "Agent should be present"
        print("✓ Specification retrieved successfully")
        
        # Test 4: List available specifications
        print("\n4. Testing specification listing...")
        specs_list = manager.list_available_specifications()
        assert len(specs_list) == 1, "Should have one specification"
        assert specs_list[0]["name"] == "test_spec", "Specification name should match"
        print("✓ Specification listing works correctly")
        
        # Test 5: Create another specification
        print("\n5. Testing multiple specifications...")
        sample_spec2 = sample_spec.copy()
        sample_spec2["name"] = "Second Test Specification"
        sample_spec2["version"] = "2.0.0"
        
        manager.save_specification("test_spec2", sample_spec2)
        
        specs_list = manager.list_available_specifications()
        assert len(specs_list) == 2, "Should have two specifications"
        print("✓ Multiple specifications handled correctly")
        
        # Test 6: Validation
        print("\n6. Testing specification validation...")
        issues = manager.validate_specification(manager.load_specification("test_spec"))
        assert len(issues) == 0, f"Valid specification should have no issues, got: {issues}"
        
        # Test invalid specification (don't save it, just validate)
        invalid_spec = sample_spec.copy()
        del invalid_spec["agents"]["evaluator"]  # Remove required agent
        invalid_spec["agents"]["agent"]["tools"].append("non_existent_tool")  # Add invalid tool
        
        from src.prompt_specification import SystemPromptSpecification
        invalid_specification = SystemPromptSpecification.from_dict(invalid_spec)
        issues = manager.validate_specification(invalid_specification)
        assert len(issues) > 0, "Invalid specification should have issues"
        print(f"✓ Validation found {len(issues)} issues as expected")
        
        # Test 7: Delete specification
        print("\n7. Testing specification deletion...")
        manager.delete_specification("test_spec2")
        assert not manager.specification_exists("test_spec2"), "Deleted specification should not exist"
        
        specs_list = manager.list_available_specifications()
        assert len(specs_list) == 1, "Should have one specification left (test_spec)"
        print("✓ Specification deletion works correctly")
        
        # Test 8: Prevent deletion of default specification
        print("\n8. Testing default specification protection...")
        try:
            manager.delete_specification("default_prompts")
            assert False, "Should not allow deletion of default specification"
        except ValueError as e:
            assert "Cannot delete the default prompt specification" in str(e)
            print("✓ Default specification is protected from deletion")
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up test directory
        shutil.rmtree(test_dir)
        print(f"Cleaned up test directory: {test_dir}")

def test_api_simulation():
    """Test basic API simulation (without actual HTTP requests)"""
    print("\nTesting API simulation...")
    
    try:
        # Initialize manager
        manager = PromptSpecificationManager()
        
        # Test listing (this should work with default prompts)
        specs = manager.list_available_specifications()
        print(f"✓ Found {len(specs)} specifications")
        
        if len(specs) > 0:
            # Test getting a specification
            first_spec = specs[0]
            contents = manager.get_specification_contents(first_spec['name'])
            print(f"✓ Retrieved specification: {first_spec['name']}")
            
            # Validate the structure
            required_keys = ['name', 'version', 'agents']
            for key in required_keys:
                assert key in contents, f"Missing required key: {key}"
            
            print("✓ Specification structure is valid")
        
        print("✅ API simulation tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ API simulation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Prompt Specification Management Tests ===")
    
    # Test 1: Core functionality
    success1 = test_prompt_specification_manager()
    
    # Test 2: API simulation
    success2 = test_api_simulation()
    
    # Final result
    if success1 and success2:
        print("\n🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1) 