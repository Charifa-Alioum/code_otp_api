from flask import Flask, request, jsonify
import random
import smtplib
from email.mime.text import MIMEText
import datetime
import os
import json

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, auth as admin_auth

app = Flask(__name__)

# In-memory OTP store
otp_store = {}

# Firebase Admin init
# Récupère le contenu de la variable d’environnement (copié depuis ton fichier .json)
cred_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
if not cred_json:
    raise Exception("FIREBASE_CREDENTIALS_JSON n'est pas défini dans les variables d'environnement")

cred_dict = json.loads(cred_json)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)

# OTP generator
def generate_otp():
    return str(random.randint(1000, 9999))

# Email sender
# Email sender (avec adresse et mot de passe en dur)
def send_email_otp(receiver_email, otp):
    # ⚠️ Mot de passe d'application Gmail (PAS le mot de passe normal)
    sender_email = "djenaboucharifaalioum@gmail.com"
    password = "qkzetdoucvdmvcmj"  # <- Ceci doit être un mot de passe d'application (via ton compte Google)

    subject = "Code de vérification - DjosAll"
    body = f"""
Bonjour,

Voici votre code de vérification : {otp}
Ce code expirera dans 5 minutes.

L’équipe DjosAll.
"""

    # Préparation de l'e-mail
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender_email, password)
            smtp.sendmail(sender_email, receiver_email, msg.as_string())
        print(f"[OK] Mail envoyé à {receiver_email}")
    except smtplib.SMTPAuthenticationError:
        print("❌ Erreur : Échec de l'authentification SMTP. Vérifie ton mot de passe d'application.")
        raise
    except Exception as e:
        print(f"❌ Erreur SMTP : {e}")
        raise

# Vérifie si l'email est enregistré dans Firebase Auth
def is_user_exist(email):
    try:
        user = admin_auth.get_user_by_email(email)
        return True
    except firebase_admin.auth.UserNotFoundError:
        return False
    except Exception as e:
        print(f"Erreur Firebase : {e}")
        return False

# API route
@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')

    if not email:
        return jsonify({"error": "Email manquant"}), 400

    if not is_user_exist(email):
        return jsonify({"error": "Email non trouvé"}), 404

    otp = generate_otp()
    expiration = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    otp_store[email] = {"otp": otp, "expires_at": expiration}

    try:
        send_email_otp(email, otp)
        return jsonify({"message": "OTP envoyé par email"}), 200
    except Exception as e:
        return jsonify({"error": f"Erreur d'envoi d'email : {str(e)}"}), 500

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    otp_received = data.get('otp')

    if not email or not otp_received:
        return jsonify({"error": "Email ou OTP manquant"}), 400

    otp_info = otp_store.get(email)
    if not otp_info:
        return jsonify({"error": "Aucun OTP trouvé pour cet email"}), 404

    if datetime.datetime.utcnow() > otp_info["expires_at"]:
        return jsonify({"error": "OTP expiré"}), 403

    if otp_received != otp_info["otp"]:
        return jsonify({"error": "OTP incorrect"}), 401

    return jsonify({"message": "OTP validé avec succès"}), 200

# Pour voir les OTP générés (dev seulement)
@app.route('/debug-otp', methods=['GET'])
def debug():
    return jsonify(otp_store)

@app.route('/')
def home():
    return "Bienvenue sur l’API DjosAll OTP 🎉"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
