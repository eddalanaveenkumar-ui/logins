import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, auth

logger = logging.getLogger("uvicorn")

def initialize_firebase():
    """
    Initializes the Firebase Admin SDK.
    Automatically fixes the common '\n' issue in private keys from Render env vars.
    """
    try:
        # Check if already initialized to avoid "App already exists" error
        if firebase_admin._apps:
            return

        cred = None
        
        # 1. Try loading from FIREBASE_CREDENTIALS (JSON string) - Recommended for Render
        firebase_creds_json = os.getenv("FIREBASE_CREDENTIALS")
        if firebase_creds_json:
            try:
                creds_dict = json.loads(firebase_creds_json)
                # FIX: Replace literal \n with actual newlines
                if "private_key" in creds_dict:
                    key = creds_dict["private_key"].replace("\\n", "\n")
                    creds_dict["private_key"] = key
                    logger.info(f"🔑 Loaded Private Key from JSON (starts with): {key[:35]}...")
                
                # Remove universe_domain if present, as it can cause issues with some lib versions
                if "universe_domain" in creds_dict:
                    del creds_dict["universe_domain"]

                cred = credentials.Certificate(creds_dict)
            except Exception as e:
                logger.error(f"Error parsing FIREBASE_CREDENTIALS: {e}")

        # 2. Fallback: Try loading from individual environment variables
        if not cred:
            private_key = os.getenv("FIREBASE_PRIVATE_KEY")
            if private_key:
                # FIX: Replace literal \n with actual newlines
                private_key = private_key.replace("\\n", "\n")
                logger.info(f"🔑 Loaded Private Key from Env Var (starts with): {private_key[:35]}...")
                
            # Construct dict from env vars
            creds_dict = {
                "type": "service_account",
                "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": private_key,
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
            }
            
            # Remove None values and check if we have the minimum required fields
            creds_dict = {k: v for k, v in creds_dict.items() if v is not None}
            
            if "project_id" in creds_dict and "private_key" in creds_dict:
                cred = credentials.Certificate(creds_dict)

        if cred:
            firebase_admin.initialize_app(cred)
            logger.info("✅ Firebase Admin SDK initialized successfully.")
        else:
            logger.warning("⚠️ Firebase credentials not found. Google Login will fail.")

    except Exception as e:
        logger.error(f"❌ Failed to initialize Firebase: {e}")

# Initialize immediately on import
initialize_firebase()

def verify_token(id_token):
    """
    Verifies a Firebase ID token and returns the decoded token dictionary.
    """
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return None