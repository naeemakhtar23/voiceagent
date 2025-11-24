"""
Setup script for Voice Call System
Helps verify installation and configuration
"""
import os
import sys
import subprocess

def check_python_version():
    """Check if Python version is 3.8+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("[ERROR] Python 3.8+ required. Current version:", sys.version)
        return False
    print(f"[OK] Python version: {sys.version.split()[0]}")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'flask',
        'flask_cors',
        'twilio',
        'dotenv',
        'pyodbc'
    ]
    
    missing = []
    for package in required_packages:
        try:
            if package == 'dotenv':
                __import__('dotenv')
            elif package == 'flask_cors':
                __import__('flask_cors')
            else:
                __import__(package)
            print(f"[OK] {package} installed")
        except ImportError:
            print(f"[ERROR] {package} not installed")
            missing.append(package)
    
    return missing

def check_env_file():
    """Check if .env file exists"""
    if os.path.exists('.env'):
        print("[OK] .env file exists")
        return True
    else:
        print("[ERROR] .env file not found")
        print("   Create .env file from .env.example template")
        return False

def check_database_connection():
    """Test database connection"""
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
        from database import Database
        db = Database()
        if db.test_connection():
            print("[OK] Database connection successful")
            return True
        else:
            print("[ERROR] Database connection failed")
            return False
    except Exception as e:
        print(f"[ERROR] Database connection error: {str(e)}")
        return False

def check_twilio_config():
    """Check if Twilio is configured"""
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
        from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
        
        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER:
            print("[OK] Twilio configuration found")
            return True
        else:
            print("[WARNING] Twilio not fully configured in .env file")
            print("   Set: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER")
            return False
    except Exception as e:
        print(f"[WARNING] Could not check Twilio config: {str(e)}")
        return False

def main():
    """Run all checks"""
    print("=" * 50)
    print("Voice Call System - Setup Verification")
    print("=" * 50)
    print()
    
    all_ok = True
    
    # Check Python version
    if not check_python_version():
        all_ok = False
    print()
    
    # Check dependencies
    print("Checking dependencies...")
    missing = check_dependencies()
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("   Install with: pip install -r backend/requirements.txt")
        all_ok = False
    print()
    
    # Check .env file
    if not check_env_file():
        all_ok = False
    print()
    
    # Check database
    print("Checking database connection...")
    if not check_database_connection():
        all_ok = False
    print()
    
    # Check Twilio
    print("Checking Twilio configuration...")
    if not check_twilio_config():
        all_ok = False
    print()
    
    # Summary
    print("=" * 50)
    if all_ok:
        print("[SUCCESS] All checks passed! System is ready.")
        print("\nNext steps:")
        print("1. Start ngrok: ngrok http 5000")
        print("2. Update WEBHOOK_BASE_URL in .env with ngrok URL")
        print("3. Configure Twilio webhook URL")
        print("4. Start server: python backend/app.py")
        print("5. Open browser: http://localhost:5000")
    else:
        print("[WARNING] Some checks failed. Please fix the issues above.")
    print("=" * 50)

if __name__ == '__main__':
    main()

