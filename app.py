from flask import Flask, render_template, request, jsonify
import serial
import time
import threading
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

serial_lock = threading.Lock()  
#elhj ngip iwmy whss
# Configurare email
EMAIL_FROM = "stefanpaul31@gmail.com"
EMAIL_TO = "stefanpaul31@gmail.com"
EMAIL_SUBJECT = "ALERTĂ INUNDAȚIE!"
EMAIL_PASSWORD = "elhj ngip iwmy whss"  # app password, nu parola normală

ultima_alerta = datetime.min

def trimite_email(mesaj):   
    global ultima_alerta
    if datetime.now() - ultima_alerta < timedelta(minutes=2):
        print("↪️ Email deja trimis recent. Nu retrimit.")
        return

    try:
        email = EmailMessage()
        email["From"] = EMAIL_FROM
        email["To"] = EMAIL_TO
        email["Subject"] = EMAIL_SUBJECT
        email.set_content(mesaj)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
            smtp.send_message(email)
            ultima_alerta = datetime.now()
            print("✅ Email trimis cu succes.")
    except Exception as e:
        print(f"❌ Eroare la trimitere email: {e}")

PORT = 'COM6'
BAUD_RATE = 9600

app = Flask(__name__)

# Deschidem conexiunea o singură dată la pornirea aplicației
try:
    print("→ Încercăm conectarea la Arduino...")
    arduino = serial.Serial(PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    arduino.reset_input_buffer()
    print("✓ Conectare reușită la COM6")
except Exception as e:
    print(f"✗ Eroare la conectare Arduino: {e}")
    arduino = None

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", raspuns="", mesaje=[])

@app.route("/comanda", methods=["POST"])
def comanda():
    cmd = request.form.get("cmd", "")
    raspuns = "Nicio conexiune"
    mesaje = []

    if arduino:
        try:
            with serial_lock:  # asigurăm accesul exclusiv la portul serial
                arduino.reset_input_buffer()
                arduino.write(cmd.encode())
                time.sleep(1)

                if cmd == 'M':
                    # Citim până la 10 mesaje sau până expiră timpul
                    start_time = time.time()
                    while time.time() - start_time < 2:
                        if arduino.in_waiting:
                            linie = arduino.readline().decode().strip()
                            if linie and linie != "Ultimele mesaje:":
                                mesaje.append(linie)
                        if len(mesaje) >= 10:
                            break
                    raspuns = "Ultimele comenzi primite:"
                else:
                    raspuns_raw = arduino.readline().decode().strip()
                    raspuns = raspuns_raw if raspuns_raw else "Niciun răspuns de la Arduino"

        except Exception as e:
            raspuns = f"Eroare comunicare: {e}"
    else:
        raspuns = "Arduino nu este conectat."

    return render_template("index.html", raspuns=raspuns, mesaje=mesaje)

@app.route("/verifica_inundatie", methods=["GET"])
def verifica_inundatie():
    if arduino:
        try:
            with serial_lock:
                arduino.reset_input_buffer()
                arduino.write(b'I')
                time.sleep(1)

                start_time = time.time()
                while time.time() - start_time < 2:
                    if arduino.in_waiting:
                        raspuns = arduino.readline().decode(errors='ignore').strip()
                        if "INUNDATIE" in raspuns:
                            trimite_email(f"Alertă de inundație: {raspuns}")
                            return jsonify({"inundatie": True, "mesaj": raspuns})
                        elif "Valoare senzor" in raspuns:
                            return jsonify({"inundatie": False, "mesaj": raspuns})
            return jsonify({"inundatie": False, "mesaj": "Niciun răspuns de la Arduino"})
        except Exception as e:
            return jsonify({"inundatie": False, "mesaj": f"Eroare: {e}"})
    else:
        return jsonify({"inundatie": False, "mesaj": "Arduino nu este conectat"})


import os

if __name__ == "__main__":
    print("→ Pornim aplicația Flask pe Azure...")
    port = int(os.environ.get("PORT", 5000))
    host = '0.0.0.0' if "PORT" in os.environ else '127.0.0.1'
    app.run(host=host, port=port, debug=True, use_reloader=False)
