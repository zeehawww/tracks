from dotenv import load_dotenv
import os

load_dotenv()

print("TWILIO_ACCOUNT_SID:", os.getenv("TWILIO_ACCOUNT_SID"))
print("TWILIO_AUTH_TOKEN:", os.getenv("TWILIO_AUTH_TOKEN"))
print("TWILIO_PHONE_NUMBER:", os.getenv("TWILIO_PHONE_NUMBER"))
