"""
Test script to verify WhatsApp client functionality without making actual calls.
"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "ai-helpline-pipeline"))
sys.path.insert(0, str(Path(__file__).parent / "ai-helpline-pipeline" / "api_clients"))

def test_imports():
    """Test if all imports work correctly"""
    print("Testing imports...")
    
    try:
        from whatsapp_client import WhatsAppClient, send_summary_via_whatsapp
        print("✅ WhatsApp client imports successful")
    except Exception as e:
        print(f"❌ WhatsApp client import failed: {e}")
        return False
    
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv(".env")
        
        # Check environment variables
        required_vars = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM"]
        for var in required_vars:
            value = os.getenv(var)
            if value:
                masked = value[:8] + "..." if len(value) > 8 else "***"
                print(f"✅ {var}: {masked}")
            else:
                print(f"❌ {var}: NOT SET")
        
        return True
        
    except Exception as e:
        print(f"❌ Config check failed: {e}")
        return False

def test_client_initialization():
    """Test if WhatsApp client can be initialized"""
    print("\nTesting WhatsApp client initialization...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent / "ai-helpline-pipeline" / ".env")
        
        from whatsapp_client import WhatsAppClient
        client = WhatsAppClient()
        print("✅ WhatsApp client initialized successfully")
        print(f"   - Twilio Account SID: {client.account_sid[:8]}...")
        print(f"   - WhatsApp From: {client.whatsapp_from}")
        print(f"   - Sarvam Client: {'✅ Ready' if client.sarvam_client else '❌ Not initialized'}")
        return True
    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("WhatsApp Client Test Suite")
    print("=" * 60)
    
    if test_imports():
        print()
        test_client_initialization()
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
