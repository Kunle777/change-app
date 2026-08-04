import firebase_admin
from firebase_admin import credentials,messaging
import os
from dotenv import load_dotenv

load_dotenv()

cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS_PATH"))
firebase_admin.initialize_app(cred)

def send_push_notification(fcm_token: str, title: str, body: str):
    message= messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        token=fcm_token
    )
    response = messaging.send(message)
    return response