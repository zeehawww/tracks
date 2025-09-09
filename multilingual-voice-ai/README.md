🚀 How to Run the AI Voice Calling Bot (Windows Version)
1. Clone/download the project and open in VS Code
2. Prepare Python Environment
powershell
python -m venv venv
.\venv\Scripts\activate
3. Install Dependencies
powershell
pip install --upgrade pip
pip install -r requirements.txt
4. Set Environment Variables
Create a .env file in your project folder.

Add your Twilio credentials:

text
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
5. Start the FastAPI Server
powershell
python main.py
OR, if using uvicorn:

powershell
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
6. Test Locally
Open browser or terminal and check:

powershell
curl http://localhost:8000/test
You should get a JSON confirming the server is up.

7. Expose with ngrok
Download ngrok from https://ngrok.com/download

Run:

powershell
.\ngrok.exe http 8000
Copy the HTTPS forwarding URL (https://xxxx.ngrok.io)

8. Set Twilio Webhook
Go to Twilio Console > Phone Numbers > Your Number

Under "A CALL COMES IN", set webhook to:

text
https://<your-ngrok-url>/voice
Select POST method and save.

9. Call or Trigger a Call
Manual: Call the Twilio number from any phone.

Automatic: Use Python with Twilio SDK to initiate outbound calls:

python
from twilio.rest import Client

account_sid = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
auth_token = "yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
client = Client(account_sid, auth_token)
call = client.calls.create(
    to="+91XXXXXXXXXX",
    from_="+1XXXXXXXXXX",
    url="https://<your-ngrok-url>/voice"
)
print(f"Call initiated! SID: {call.sid}")
10. Listen and Interact
When call connects, speak your query in Hindi, English, or local language.

AI will reply by voice in the appropriate language.

Follow logs for debugging if needed.

Note:

All steps are Windows-friendly (use PowerShell, not Bash).

The AI can reply in Hindi, English, and with extra code, other Indian languages (see tts_handler.py for configuration).

For more languages or model upgrades, see demo code sections.
