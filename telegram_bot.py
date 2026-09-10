#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛵 VespaCare Telegram Bot & Proactive Alert Engine
Homelands Labs by Pedro Díaz (Fables Infrastructure)
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime

BOT_TOKEN = "8980881287:AAEsQm3gwbX4dT6vZBksBbyzlZHILkTFgl0"
ADMIN_CHAT_ID = "129347404"
DATA_FILE = "/var/www/html/vespa/data.json"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading data.json: {e}")
    return {}

def send_message(text, chat_id=ADMIN_CHAT_ID, parse_mode="HTML"):
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error sending telegram message: {e}")
        return None

def build_status_report(data):
    odo = data.get("odometer", 0)
    fuel_stock = data.get("homeFuelStock", 0)
    docs = data.get("documentacion", {})
    itv = docs.get("itv", {})
    seguro = docs.get("seguro", {})
    
    # Calcular autonomía
    repostajes = data.get("repostajes", [])
    autonomia_txt = "No calculada"
    if len(repostajes) >= 2:
        sorted_fuel = sorted(repostajes, key=lambda x: x.get('date', ''), reverse=True)
        last = sorted_fuel[0]
        total_km = 0
        total_l = 0
        for i in range(len(sorted_fuel) - 1):
            diff = sorted_fuel[i].get('km', 0) - sorted_fuel[i+1].get('km', 0)
            if diff > 0 and sorted_fuel[i].get('litros', 0) > 0:
                total_km += diff
                total_l += sorted_fuel[i].get('litros', 0)
        if total_l > 0:
            avg = total_km / total_l
            max_range = last.get('litros', 0) * avg
            traveled = odo - last.get('km', 0)
            remaining = max(0, max_range - traveled)
            autonomia_txt = f"~{remaining:.0f} km ({avg:.2f} km/L)"

    # Próxima bujía
    spark = next((m for m in data.get('mantenimientos', []) if m.get('id') in ['bujia', 'aceite']), None)
    spark_txt = f"{spark['ultimo'] + spark['intervalo'] - odo} km" if spark else "OK"

    # ITV y Seguro
    now = datetime.now()
    itv_txt = "Sin configurar"
    if itv.get("expiry"):
        try:
            exp = datetime.strptime(itv["expiry"], "%Y-%m-%d")
            diff = (exp - now).days
            itv_txt = f"{itv['expiry']} ({'Vence en ' + str(diff) + 'd' if diff >= 0 else '¡Caducada hace ' + str(abs(diff)) + 'd!'})"
        except:
            itv_txt = itv["expiry"]

    seguro_txt = "Sin configurar"
    if seguro.get("expiry"):
        try:
            exp = datetime.strptime(seguro["expiry"], "%Y-%m-%d")
            diff = (exp - now).days
            seguro_txt = f"{seguro['expiry']} ({'Vence en ' + str(diff) + 'd' if diff >= 0 else '¡Caducado hace ' + str(abs(diff)) + 'd!'})"
        except:
            seguro_txt = seguro["expiry"]

    msg = f"""🛵 <b>VespaCare — Estado General</b>
🏛️ <i>Homelands Labs by Pedro Díaz</i>
━━━━━━━━━━━━━━━━━━
📍 <b>Odómetro:</b> <code>{odo} km</code>
⛽ <b>Autonomía estimada:</b> <code>{autonomia_txt}</code>
🏠 <b>Garrafa en Casa:</b> <code>{fuel_stock:.1f} L</code>
🔌 <b>Próx. Bujía (NGK B7HS):</b> <code>{spark_txt}</code>

📋 <b>Control Legal:</b>
• <b>ITV:</b> <code>{itv_txt}</code>
• <b>Seguro:</b> <code>{seguro_txt}</code>
━━━━━━━━━━━━━━━━━━
🔗 <a href="https://vespa.pedrodiaz.eu">Abrir VespaCare PWA</a>"""
    return msg

def check_proactive_alerts(data):
    now = datetime.now()
    alerts = []
    odo = data.get("odometer", 0)

    # 1. ITV
    itv = data.get("documentacion", {}).get("itv", {})
    if itv.get("expiry"):
        try:
            exp = datetime.strptime(itv["expiry"], "%Y-%m-%d")
            diff = (exp - now).days
            if diff < 0:
                alerts.append(f"🚨 <b>ITV Caducada</b>: Venció el {itv['expiry']} (hace {abs(diff)} días).")
            elif diff <= 30:
                alerts.append(f"⚠️ <b>ITV Próxima</b>: Vence el {itv['expiry']} (quedan {diff} días).")
        except:
            pass

    # 2. Seguro
    seguro = data.get("documentacion", {}).get("seguro", {})
    if seguro.get("expiry"):
        try:
            exp = datetime.strptime(seguro["expiry"], "%Y-%m-%d")
            diff = (exp - now).days
            if diff < 0:
                alerts.append(f"🚨 <b>Seguro Caducado</b>: Venció el {seguro['expiry']} (hace {abs(diff)} días).")
            elif diff <= 30:
                alerts.append(f"⚠️ <b>Seguro Próximo</b>: Vence el {seguro['expiry']} (quedan {diff} días).")
        except:
            pass

    # 3. Mantenimientos por Km
    for m in data.get("mantenimientos", []):
        inter = m.get("intervalo", 0)
        ultimo = m.get("ultimo", 0)
        if inter > 0:
            rest = inter - (odo - ultimo)
            if rest <= 0:
                alerts.append(f"🔧 <b>Mantenimiento Vencido</b>: {m['nombre']} excedido por {abs(rest)} km.")
            elif rest <= 250:
                alerts.append(f"⚠️ <b>Mantenimiento Próximo</b>: {m['nombre']} toca en {rest} km.")

    if alerts:
        msg = f"""🔔 <b>VespaCare — Alertas Activas</b>
━━━━━━━━━━━━━━━━━━
""" + "\n\n".join(alerts) + f"""
━━━━━━━━━━━━━━━━━━
🔗 <a href="https://vespa.pedrodiaz.eu">Gestionar en VespaCare</a>"""
        send_message(msg)

if __name__ == "__main__":
    data = load_data()
    action = sys.argv[1] if len(sys.argv) > 1 else "welcome"

    if action == "welcome":
        welcome_msg = f"""👋 ¡Hola <b>Pedro</b>!

El bot oficial de <b>VespaCare</b> está enlazado correctamente con tu servidor en <b>Homelands Labs</b> (nodo <code>blue</code>).

🛵 <b>Vespa PK 125 S Elestart (1984)</b>
A partir de ahora recibirás alertas automáticas de ITV, Seguro, revisiones y estado de la moto.

Pulsa /estado para ver la telemetría actual o /ayuda."""
        send_message(welcome_msg)
    elif action == "status":
        send_message(build_status_report(data))
    elif action == "check":
        check_proactive_alerts(data)
