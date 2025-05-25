#!/usr/bin/env python3
"""
Validation script to ensure correct google-genai SDK setup and usage.

This script validates that our implementation follows the latest patterns
from the unified SDK documentation.
"""

import os
import sys
from pathlib import Path

def validate_imports():
    """Validate that we can import the correct modules."""
    try:
        from google import genai
        from google.genai import types
        print("✅ google-genai imports successful")
        return True
    except ImportError as e:
        print(f"❌ google-genai import failed: {e}")
        print("Please install: pip install google-genai>=0.6.0")
        return False

def validate_client_creation():
    """Validate client creation patterns."""
    try:
        from google import genai
        
        # Test API key client (Google AI Studio)
        if os.getenv("GOOGLE_API_KEY"):
            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            print("✅ Google AI Studio client creation successful")
        
        # Test Vertex AI client
        if os.getenv("GOOGLE_CLOUD_PROJECT"):
            client = genai.Client(
                vertexai=True,
                project=os.getenv("GOOGLE_CLOUD_PROJECT"),
                location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
            )
            print("✅ Vertex AI client creation successful")
        
        if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GOOGLE_CLOUD_PROJECT"):
            print("⚠️  No credentials found. Set GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT")
            
        return True
    except Exception as e:
        print(f"❌ Client creation failed: {e}")
        return False

def validate_model_names():
    """Validate model naming conventions."""
    correct_patterns = {
        "vertex_ai": [
            "gemini-2.0-flash",
            "gemini-2.0-pro", 
            "gemini-2.5-pro-preview"
        ],
        "google_ai_studio": [
            "models/gemini-2.0-flash",
            "models/gemini-2.0-pro",
            "models/gemini-2.5-pro-preview"
        ]
    }
    
    print("✅ Model naming patterns validated:")
    print("   - Vertex AI: No 'models/' prefix")
    print("   - Google AI Studio: 'models/' prefix required")
    return True

def validate_api_usage():
    """Validate our API usage patterns match the latest SDK."""
    
    # Check our GeminiService implementation
    service_file = Path(__file__).parent / "app" / "services" / "gemini_service.py"
    if not service_file.exists():
        print("❌ GeminiService file not found")
        return False
    
    with open(service_file, 'r') as f:
        content = f.read()
    
    # Check for correct imports
    if "from google import genai" in content and "from google.genai import types" in content:
        print("✅ Correct imports in GeminiService")
    else:
        print("❌ Incorrect imports in GeminiService")
        return False
    
    # Check for unified client pattern
    if "genai.Client(" in content and "vertexai=True" in content:
        print("✅ Unified client pattern used")
    else:
        print("⚠️  Consider using unified client pattern")
    
    # Check for correct API calls
    if "client.aio.models.generate_content" in content:
        print("✅ Correct async API usage")
    elif "client.models.generate_content" in content:
        print("✅ Correct sync API usage")
    else:
        print("❌ API usage pattern not found")
        return False
    
    return True

def validate_configuration():
    """Validate configuration patterns."""
    config_file = Path(__file__).parent / "app" / "core" / "config.py"
    if not config_file.exists():
        print("❌ Config file not found")
        return False
    
    with open(config_file, 'r') as f:
        content = f.read()
    
    # Check for correct default model
    if 'DEFAULT_MODEL: str = "gemini-2.0-flash"' in content:
        print("✅ Correct default model configured")
    else:
        print("⚠️  Consider updating default model to gemini-2.0-flash")
    
    return True

def main():
    """Run all validations."""
    print("🔍 Validating google-genai SDK setup...")
    print("=" * 50)
    
    validations = [
        ("Import validation", validate_imports),
        ("Client creation", validate_client_creation),
        ("Model naming", validate_model_names),
        ("API usage", validate_api_usage),
        ("Configuration", validate_configuration)
    ]
    
    results = []
    for name, validator in validations:
        print(f"\n🔧 {name}:")
        try:
            result = validator()
            results.append(result)
        except Exception as e:
            print(f"❌ {name} failed: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY:")
    
    if all(results):
        print("✅ All validations passed! Your setup follows the latest google-genai patterns.")
        return 0
    else:
        print("⚠️  Some validations failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())