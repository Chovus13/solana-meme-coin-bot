#!/usr/bin/env python3
"""
Installation Test Script for Solana Memecoin Trading Bot
Author: MiniMax Agent

This script tests the bot installation and configuration.
"""

import sys
import os
import sqlite3
from pathlib import Path
import importlib.util
from typing import List


def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_test(name, status, details=""):
    """Print test result"""
    status_icon = "✅" if status else "❌"
    print(f"{status_icon} {name}")
    if details:
        print(f"   {details}")


def test_python_version():
    """Test Python version compatibility"""
    version = sys.version_info
    compatible = version.major >= 3 and version.minor >= 8
    
    print_test(
        "Python Version", 
        compatible,
        f"Python {version.major}.{version.minor}.{version.micro} ({'Compatible' if compatible else 'Requires 3.8+'})"
    )
    return compatible


def test_directory_structure():
    """Test if required directories exist"""
    required_dirs = [
        "bot_code",
        "bot_code/social_media",
        "bot_code/token_analysis",
        "bot_code/trading",
        "bot_code/utils",
        "bot_code/web_interface",
        "bot_code/web_interface/templates"
    ]
    
    all_exist = True
    for directory in required_dirs:
        exists = Path(directory).exists()
        if not exists:
            all_exist = False
        print_test(f"Directory: {directory}", exists)
    
    return all_exist


def test_core_files():
    """Test if core files exist"""
    required_files = [
        "main.py",
        "setup.py",
        ".env.template",
        "bot_code/config.py",
        "bot_code/solana_memecoin_bot.py",
        "bot_code/requirements.txt"
    ]
    
    all_exist = True
    for file_path in required_files:
        exists = Path(file_path).exists()
        if not exists:
            all_exist = False
        print_test(f"File: {file_path}", exists)
    
    return all_exist


def test_python_imports():
    """Test if core modules can be imported"""
    test_modules = [
        ("config", "bot_code/config.py"),
        ("solana_memecoin_bot", "bot_code/solana_memecoin_bot.py"),
        ("utils.database", "bot_code/utils/database.py"),
        ("utils.logger", "bot_code/utils/logger.py")
    ]
    
    # Add code directory to path
    sys.path.insert(0, str(Path.cwd() / "bot_code"))
    
    all_imported = True
    for module_name, file_path in test_modules:
        try:
            if Path(file_path).exists():
                __import__(module_name)
                print_test(f"Import: {module_name}", True)
            else:
                print_test(f"Import: {module_name}", False, "File not found")
                all_imported = False
        except ImportError as e:
            print_test(f"Import: {module_name}", False, str(e))
            all_imported = False
        except Exception as e:
            print_test(f"Import: {module_name}", False, f"Error: {e}")
            all_imported = False
    
    return all_imported


def test_dependencies():
    """Test if required packages are available"""
    required_packages = [
        "flask", "flask_socketio", "requests", "tweepy", "praw", 
        "discord.py", "python-telegram-bot", "solders", "asyncio",
        "sqlite3", "json", "logging", "datetime", "threading"
    ]
    
    all_available = True
    for package in required_packages:
        try:
            if package == "sqlite3":
                import sqlite3
            elif package == "json":
                import json
            elif package == "logging":
                import logging
            elif package == "datetime":
                import datetime
            elif package == "threading":
                import threading
            elif package == "asyncio":
                import asyncio
            else:
                __import__(package)
            print_test(f"Package: {package}", True)
        except ImportError:
            print_test(f"Package: {package}", False, "Not installed")
            all_available = False
        except Exception as e:
            print_test(f"Package: {package}", False, str(e))
            all_available = False
    
    return all_available


def test_configuration():
    """Test configuration setup"""
    env_template_exists = Path(".env.template").exists()
    env_exists = Path(".env").exists()
    
    print_test("Environment template", env_template_exists)
    print_test("Environment file", env_exists, 
               "Create from .env.template" if not env_exists else "")
    
    if env_template_exists:
        # Test if we can read the template
        try:
            with open(".env.template", 'r') as f:
                content = f.read()
                has_solana_config = "SOLANA_RPC_URL" in content
                has_api_config = "TWITTER_BEARER_TOKEN" in content
                print_test("Template has Solana config", has_solana_config)
                print_test("Template has API config", has_api_config)
                return has_solana_config and has_api_config
        except Exception as e:
            print_test("Template validation", False, str(e))
            return False
    
    return env_template_exists


def test_database_setup():
    """Test database initialization"""
    try:
        # Test if we can create and initialize database
        sys.path.insert(0, str(Path.cwd() / "bot_code"))
        
        # Create data directory if it doesn't exist
        Path("data").mkdir(exist_ok=True)
        
        # Test database creation
        test_db_path = "data/test_database.db"
        
        # Remove test database if it exists
        if Path(test_db_path).exists():
            os.remove(test_db_path)
        
        # Test SQLite connection
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        
        # Clean up
        os.remove(test_db_path)
        
        print_test("Database creation", True)
        return True
        
    except Exception as e:
        print_test("Database creation", False, str(e))
        return False


def test_web_interface():
    """Test web interface files"""
    template_files = [
        "bot_code/web_interface/templates/base.html",
        "bot_code/web_interface/templates/dashboard.html",
        "bot_code/web_interface/templates/positions.html",
        "bot_code/web_interface/templates/discoveries.html",
        "bot_code/web_interface/templates/settings.html"
    ]
    
    app_file = "bot_code/web_interface/app.py"
    
    all_exist = True
    
    # Test Flask app file
    app_exists = Path(app_file).exists()
    print_test("Flask app file", app_exists)
    if not app_exists:
        all_exist = False
    
    # Test template files
    for template in template_files:
        exists = Path(template).exists()
        print_test(f"Template: {Path(template).name}", exists)
        if not exists:
            all_exist = False
    
    return all_exist


def test_documentation():
    """Test documentation files"""
    doc_files = [
        ("README.md", "Main documentation"),
        ("DEPLOYMENT_GUIDE.md", "Deployment guide"), 
        (".env.template", "Environment template")
    ]
    
    all_exist = True
    for file_path, description in doc_files:
        exists = Path(file_path).exists()
        print_test(f"{description}", exists)
        if not exists:
            all_exist = False
    
    return all_exist


def run_comprehensive_test():
    """Run all tests and provide summary"""
    print_header("🧪 SOLANA MEMECOIN BOT INSTALLATION TEST")
    
    tests = [
        ("Python Version", test_python_version),
        ("Directory Structure", test_directory_structure),
        ("Core Files", test_core_files),
        ("Python Imports", test_python_imports),
        ("Dependencies", test_dependencies),
        ("Configuration", test_configuration),
        ("Database Setup", test_database_setup),
        ("Web Interface", test_web_interface),
        ("Documentation", test_documentation)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print_header(f"Testing: {test_name}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print_test(test_name, False, f"Test failed with error: {e}")
            results[test_name] = False
    
    # Summary
    print_header("📊 TEST SUMMARY")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        print_test(test_name, result)
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your installation looks good.")
        print("\n📋 Next Steps:")
        print("   1. Copy .env.template to .env")
        print("   2. Fill in your API keys in .env")
        print("   3. Run: python main.py")
        print("   4. Access web interface: http://localhost:8080")
        return True
    else:
        print(f"\n❌ {total - passed} tests failed. Please resolve issues before running the bot.")
        print("\n🔧 Common solutions:")
        print("   • Install missing dependencies: pip install -r bot_code/requirements.txt")
        print("   • Check file permissions")
        print("   • Verify Python version (3.8+ required)")
        return False


def main():
    """Main test function"""
    try:
        success = run_comprehensive_test()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test failed with unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
