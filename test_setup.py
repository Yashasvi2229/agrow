#!/usr/bin/env python3
"""
Simple test script to verify Twilio server setup.
Run this before starting the actual server to catch configuration issues early.
"""

import os
import sys
from pathlib import Path

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_mark(passed):
    return f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"

def test_imports():
    """Test that all required packages are installed"""
    print(f"\n{BLUE}Testing imports...{RESET}")
    
    checks = []
    
    try:
        import flask
        print(f"  {check_mark(True)} Flask installed (v{flask.__version__})")
        checks.append(True)
    except ImportError:
        print(f"  {check_mark(False)} Flask not installed - run: pip3 install flask")
        checks.append(False)
    
    try:
        import twilio
        print(f"  {check_mark(True)} Twilio SDK installed (v{twilio.__version__})")
        checks.append(True)
    except ImportError:
        print(f"  {check_mark(False)} Twilio SDK not installed - run: pip3 install twilio")
        checks.append(False)
    
    try:
        import requests
        print(f"  {check_mark(True)} Requests installed")
        checks.append(True)
    except ImportError:
        print(f"  {check_mark(False)} Requests not installed - run: pip3 install requests")
        checks.append(False)
    
    try:
        import dotenv
        print(f"  {check_mark(True)} Python-dotenv installed")
        checks.append(True)
    except ImportError:
        print(f"  {check_mark(False)} Python-dotenv not installed - run: pip3 install python-dotenv")
        checks.append(False)
    
    return all(checks)

def test_pipeline():
    """Test that the AI pipeline can be imported"""
    print(f"\n{BLUE}Testing AI pipeline...{RESET}")
    
    try:
        # Add ai-helpline-pipeline directory to path
        pipeline_dir = Path(__file__).parent / "ai-helpline-pipeline"
        sys.path.insert(0, str(pipeline_dir))
        
        from config import load_config
        from pipeline import HelplinePipeline
        print(f"  {check_mark(True)} Pipeline modules can be imported")
        
        # Try to load config
        try:
            config = load_config()
            print(f"  {check_mark(True)} Config loaded successfully")
            return True
        except Exception as e:
            print(f"  {check_mark(False)} Config load failed: {e}")
            print(f"     {YELLOW}Make sure .env file has all required API keys{RESET}")
            return False
            
    except ImportError as e:
        print(f"  {check_mark(False)} Cannot import pipeline: {e}")
        return False

def test_env_vars():
    """Check for required environment variables"""
    print(f"\n{BLUE}Checking environment variables...{RESET}")
    
    from dotenv import load_dotenv
    
    # Try to load from both locations
    env_file = Path("ai-helpline-pipeline/.env")
    if env_file.exists():
        load_dotenv(env_file)
        print(f"  {check_mark(True)} Found .env at ai-helpline-pipeline/.env")
    
    env_file2 = Path(".env")
    if env_file2.exists():
        load_dotenv(env_file2)
        print(f"  {check_mark(True)} Found .env at ./.env")
    
    required_vars = {
        "ELEVENLABS_API_KEY": "ElevenLabs API key",
        "SARVAM_API_KEY": "Sarvam API key",
        "GROQ_API_KEY": "Groq API key"
    }
    
    optional_vars = {
        "TWILIO_ACCOUNT_SID": "Twilio Account SID",
        "TWILIO_AUTH_TOKEN": "Twilio Auth Token",
        "TWILIO_PHONE_NUMBER": "Twilio Phone Number"
    }
    
    all_present = True
    
    print(f"\n  Required for AI pipeline:")
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask the key for security
            masked = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
            print(f"    {check_mark(True)} {description}: {masked}")
        else:
            print(f"    {check_mark(False)} {description}: NOT SET")
            all_present = False
    
    print(f"\n  Required for Twilio (can be set later):")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            masked = f"{value[:8]}..." if len(value) > 8 else "***"
            print(f"    {check_mark(True)} {description}: {masked}")
        else:
            print(f"    {YELLOW}○{RESET} {description}: Not set yet")
    
    return all_present

def test_directories():
    """Check if required directories exist"""
    print(f"\n{BLUE}Checking directories...{RESET}")
    
    dirs = ["temp_uploads", "output_audio"]
    for dirname in dirs:
        path = Path(dirname)
        if not path.exists():
            path.mkdir(exist_ok=True)
            print(f"  {check_mark(True)} Created {dirname}/")
        else:
            print(f"  {check_mark(True)} {dirname}/ exists")
    
    return True

def main():
    print(f"\n{'='*60}")
    print(f"  {BLUE}Agrow Twilio Server - Configuration Test{RESET}")
    print(f"{'='*60}")
    
    results = {
        "Imports": test_imports(),
        "AI Pipeline": test_pipeline(),
        "Environment Variables": test_env_vars(),
        "Directories": test_directories()
    }
    
    print(f"\n{'='*60}")
    print(f"  {BLUE}Test Summary{RESET}")
    print(f"{'='*60}\n")
    
    for test_name, passed in results.items():
        print(f"  {check_mark(passed)} {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print(f"\n{GREEN}✓ All checks passed! Ready to start the server.{RESET}")
        print(f"\n{BLUE}Next steps:{RESET}")
        print(f"  1. Set Twilio credentials in .env (if not already set)")
        print(f"  2. Start ngrok: {YELLOW}ngrok http 5000{RESET}")
        print(f"  3. Start server: {YELLOW}python3 server.py{RESET}")
        return 0
    else:
        print(f"\n{RED}✗ Some checks failed. Please fix the issues above.{RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
