#!/usr/bin/env python3
"""
Simple test script for multi-agent functionality
"""

import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from prompt_specification import PromptSpecificationManager
from tools_specification import ToolsSpecification

def test_multi_agent_setup():
    """Test that multi-agent prompt specification loads correctly"""
    print("Testing multi-agent setup...")
    
    try:
        # Load prompt specification
        manager = PromptSpecificationManager()
        spec = manager.load_specification('default_prompts')
        
        print(f"✓ Loaded specification: {spec.name}")
        print(f"✓ Available agents: {list(spec.agents.keys())}")
        
        # Check for support agent
        if 'support' in spec.agents:
            print("✓ Support agent found")
            support_agent = spec.agents['support']
            print(f"✓ Support agent name: {support_agent.name}")
            
            # Check handoffs
            if support_agent.handoffs:
                print(f"✓ Support agent handoffs: {list(support_agent.handoffs.keys())}")
            else:
                print("⚠ Support agent has no handoffs configured")
        else:
            print("✗ Support agent not found")
        
        # Check main agent handoffs
        if 'agent' in spec.agents:
            main_agent = spec.agents['agent']
            if main_agent.handoffs:
                print(f"✓ Main agent handoffs: {list(main_agent.handoffs.keys())}")
                
                # Test handoff tool generation
                tools = main_agent.get_tool_schemas()
                handoff_tools = [tool for tool in tools if tool['function']['name'].startswith('handoff_')]
                print(f"✓ Generated handoff tools: {[tool['function']['name'] for tool in handoff_tools]}")
            else:
                print("⚠ Main agent has no handoffs configured")
        
        # Validate specification
        issues = manager.validate_specification(spec)
        if issues:
            print(f"⚠ Validation issues: {issues}")
        else:
            print("✓ Specification validation passed")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_handoff_tools():
    """Test handoff tool generation"""
    print("\nTesting handoff tool generation...")
    
    try:
        # Test with handoffs
        handoffs = {"support": "Transfer to support", "manager": "Transfer to manager"}
        tools = ToolsSpecification.get_tools_by_names(["rag_find_products", "handoff_support", "handoff_manager"], handoffs)
        
        # Check if handoff tools are generated
        tool_names = [tool['function']['name'] for tool in tools]
        print(f"✓ Generated tools: {tool_names}")
        
        if 'handoff_support' in tool_names:
            print("✓ handoff_support tool generated")
        else:
            print("✗ handoff_support tool not generated")
        
        if 'handoff_manager' in tool_names:
            print("✓ handoff_manager tool generated")
        else:
            print("✗ handoff_manager tool not generated")
        
        # Test tool utility functions
        assert ToolsSpecification.is_handoff_tool('handoff_support') == True
        assert ToolsSpecification.is_handoff_tool('rag_find_products') == False
        assert ToolsSpecification.get_handoff_target_agent('handoff_support') == 'support'
        assert ToolsSpecification.get_handoff_target_agent('rag_find_products') == None
        
        print("✓ Tool utility functions work correctly")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("Multi-Agent Functionality Test Suite")
    print("=" * 40)
    
    test_results = []
    
    # Run tests
    test_results.append(test_multi_agent_setup())
    test_results.append(test_handoff_tools())
    
    # Summary
    print("\n" + "=" * 40)
    passed = sum(test_results)
    total = len(test_results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! Multi-agent functionality is working.")
    else:
        print("✗ Some tests failed. Check the output above.")
    
    return passed == total

if __name__ == "__main__":
    main() 