#!/usr/bin/env python3
"""
Basic validation tests for LLM Simulation Service
"""
import sys
import os
import json

# Add project root to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from src.config import Config
        print("✓ Config module imported")
        
        from src.logging_utils import get_logger
        print("✓ Logging utils imported")
        
        from src.openai_wrapper import OpenAIWrapper
        print("✓ OpenAI wrapper imported")
        
        from src.webhook_manager import WebhookManager
        print("✓ Webhook manager imported")
        
        from src.tool_emulator import ToolEmulator
        print("✓ Tool emulator imported")
        
        from src.conversation_engine import ConversationEngine
        print("✓ Conversation engine imported")
        
        from src.evaluator import ConversationEvaluator
        print("✓ Evaluator imported")
        
        from src.batch_processor import BatchProcessor
        print("✓ Batch processor imported")
        
        from src.result_storage import ResultStorage
        print("✓ Result storage imported")
        
        from src.routes.batch_routes import batch_bp
        print("✓ Batch routes imported")
        
        print("All imports successful!")
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        from src.config import Config
        
        # Test basic config attributes
        assert hasattr(Config, 'OPENAI_MODEL')
        assert hasattr(Config, 'MAX_TURNS')
        assert hasattr(Config, 'CONCURRENCY')
        print("✓ Config attributes exist")
        
        # Test directory creation
        Config.ensure_directories()
        print("✓ Directory creation works")
        
        # Test prompt path generation
        prompt_path = Config.get_prompt_path("agent_system")
        assert prompt_path.endswith("agent_system.txt")
        print("✓ Prompt path generation works")
        
        print("Configuration tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        return False

def test_scenario_loading():
    """Test scenario file loading"""
    print("\nTesting scenario loading...")
    
    try:
        scenario_file = os.path.join(BASE_DIR, "scenarios", "sample_scenarios.json")
        
        if os.path.exists(scenario_file):
            with open(scenario_file, 'r', encoding='utf-8') as f:
                scenarios = json.load(f)
            
            assert isinstance(scenarios, list)
            assert len(scenarios) > 0
            
            # Validate scenario structure
            for scenario in scenarios:
                assert 'name' in scenario
                assert 'variables' in scenario
                assert isinstance(scenario['variables'], dict)
            
            print(f"✓ Loaded {len(scenarios)} scenarios successfully")
            print("Scenario loading tests passed!")
            return True
        else:
            print(f"✗ Scenario file not found: {scenario_file}")
            return False
            
    except Exception as e:
        print(f"✗ Scenario loading test failed: {e}")
        return False

def test_prompt_templates():
    """Test prompt template loading"""
    print("\nTesting prompt templates...")
    
    try:
        prompt_files = [
            os.path.join(BASE_DIR, "prompts", "agent_system.txt"),
            os.path.join(BASE_DIR, "prompts", "client_system.txt"),
            os.path.join(BASE_DIR, "prompts", "evaluator_system.txt")
        ]
        
        for prompt_file in prompt_files:
            if os.path.exists(prompt_file):
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                assert len(content) > 0
                print(f"✓ {prompt_file} loaded successfully")
            else:
                print(f"✗ Prompt file not found: {prompt_file}")
                return False
        
        print("Prompt template tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Prompt template test failed: {e}")
        return False

def test_flask_app():
    """Test Flask app creation"""
    print("\nTesting Flask app...")
    
    try:
        from src.main import app
        
        # Test app creation
        assert app is not None
        print("✓ Flask app created")
        
        # Test routes are registered
        routes = [str(rule) for rule in app.url_map.iter_rules()]
        
        expected_routes = ['/api/batches', '/api/health']
        for route in expected_routes:
            if any(route in r for r in routes):
                print(f"✓ Route {route} registered")
            else:
                print(f"✗ Route {route} not found")
                return False
        
        print("Flask app tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Flask app test failed: {e}")
        return False

def test_cli_structure():
    """Test CLI script structure"""
    print("\nTesting CLI structure...")
    
    try:
        # Test CLI script exists and is executable
        cli_script = os.path.join(BASE_DIR, "simulate.py")
        
        if os.path.exists(cli_script):
            # Check if file is executable
            if os.access(cli_script, os.X_OK):
                print("✓ CLI script is executable")
            else:
                print("✗ CLI script is not executable")
                return False
            
            # Test basic structure by reading file
            with open(cli_script, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for main components
            required_components = [
                'SimulateCLI',
                'run_batch_local',
                'run_single_scenario',
                'get_batch_status_via_api',
                'fetch_batch_results_via_api'
            ]
            
            for component in required_components:
                if component in content:
                    print(f"✓ CLI component {component} found")
                else:
                    print(f"✗ CLI component {component} missing")
                    return False
            
            print("CLI structure tests passed!")
            return True
        else:
            print(f"✗ CLI script not found: {cli_script}")
            return False
            
    except Exception as e:
        print(f"✗ CLI structure test failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("=" * 60)
    print("LLM Simulation Service - Validation Tests")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_config,
        test_scenario_loading,
        test_prompt_templates,
        test_flask_app,
        test_cli_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All validation tests passed!")
        return True
    else:
        print("❌ Some tests failed. Please check the output above.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

