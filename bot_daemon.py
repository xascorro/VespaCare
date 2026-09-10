#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛵 VespaCare Telegram Daemon & Intelligent Assistant (v2.1)
Homelands Labs by Pedro Díaz

Features:
1. 🔘 Interactive Inline & Reply Keyboards.
2. ⛽ Natural Language & Slash Command parsing for fuel, oil, expenses & odometer.
3. 📦 Smart Workshop Stock & Purchase intake (e.g. 'Compra bombilla freno 10w por 1.5€ en Recambios Ruiz').
4. 📸 Receipt/Ticket/Photo intake & secure archival in /var/www/html/vespa/docs/.
5. 🎙️ Voice memo intake & audio logging in /var/www/html/vespa/docs/voice/.
"""

import json
import os
import re
import sys
import time
import shutil
import urllib.request
import urllib.parse
from datetime import datetime

BOT_TOKEN = "8980881287:AAEsQm3gwbX4dT6vZBksBbyzlZHILkTFgl0"
ADMIN_CHAT_ID = 129347404
DATA_FILE = "/var/www/html/vespa/data.json"
BACKUP_DIR = "/var/www/html/vespa/backups"
DOCS_DIR = "/var/www/html/vespa/docs"
VOICE_DIR = "/var/www/html/vespa/docs/voice"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
FILE_BASE_URL = f"https://api.telegram.org/file/bot{BOT_TOKEN}"

# Asegurar directorios
for d in [BACKUP_DIR, DOCS_DIR, VOICE_DIR]:
    os.makedirs(d, exist_ok=True)

# ---------------------------------------------------------
# DATA MANAGEMENT
# ---------------------------------------------------------

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading data.json: {e}", flush=True)
    return {}

def save_data(data):
    try:
        if os.path.exists(DATA_FILE):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snap_file = os.path.join(BACKUP_DIR, f"data_autosave_{timestamp}.json")
            shutil.copyfile(DATA_FILE, snap_file)
            
            # Limpiar backups antiguos dejando los 15 más recientes
            snaps = sorted(
                [os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.startswith("data_autosave_")],
                key=os.path.getmtime
            )
            if len(snaps) > 15:
                for s in snaps[:-15]:
                    try:
                        os.remove(s)
                    except Exception:
                        pass
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving data.json: {e}", flush=True)
        return False

# ---------------------------------------------------------
# TELEGRAM API HELPERS
# ---------------------------------------------------------

def tg_api_call(method, payload):
    url = f"{BASE_URL}/{method}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "HomelandsLabs-VespaCareBot/2.1"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Telegram API Error ({method}): {e}", flush=True)
        return None

def send_message(text, chat_id=ADMIN_CHAT_ID, parse_mode="HTML", reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_api_call("sendMessage", payload)

def edit_message_text(text, chat_id, message_id, parse_mode="HTML", reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_api_call("editMessageText", payload)

def answer_callback_query(callback_query_id, text=None, show_alert=False):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
        payload["show_alert"] = show_alert
    return tg_api_call("answerCallbackQuery", payload)

def get_file_info(file_id):
    res = tg_api_call("getFile", {"file_id": file_id})
    if res and res.get("ok"):
        return res.get("result", {})
    return None

def download_telegram_file(file_path, dest_local_path):
    url = f"{FILE_BASE_URL}/{file_path}"
    req = urllib.request.Request(url, headers={"User-Agent": "HomelandsLabs-VespaCareBot/2.1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response, open(dest_local_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        os.chmod(dest_local_path, 0o664)
        return True
    except Exception as e:
        print(f"Error downloading Telegram file {file_path}: {e}", flush=True)
        return False

# ---------------------------------------------------------
# KEYBOARDS & MENUS
# ---------------------------------------------------------

def get_persistent_reply_keyboard():
    return {
        "keyboard": [
            [{"text": "📊 Estado"}, {"text": "📦 Stock Taller"}],
            [{"text": "🛞 Presiones"}, {"text": "⛽ Repostar"}, {"text": "💶 Añadir Gasto"}],
            [{"text": "🌐 Abrir VespaCare PWA"}, {"text": "❓ Ayuda"}]
        ],
        "resize_keyboard": True,
        "is_persistent": True
    }

def get_status_inline_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "🔄 Actualizar", "callback_data": "cmd_estado"},
                {"text": "🛞 Presiones", "callback_data": "cmd_presion"}
            ],
            [
                {"text": "📦 Stock Garaje", "callback_data": "cmd_stock"},
                {"text": "🌐 Abrir PWA", "url": "https://vespa.pedrodiaz.eu"}
            ]
        ]
    }

def get_pressure_inline_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Marcar Revisadas Hoy", "callback_data": "act_presion_ok"},
                {"text": "📊 Ver Estado", "callback_data": "cmd_estado"}
            ]
        ]
    }

def get_stock_inline_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "🔄 Refrescar Stock", "callback_data": "cmd_stock"},
                {"text": "📊 Estado General", "callback_data": "cmd_estado"}
            ],
            [
                {"text": "🌐 Gestionar en PWA", "url": "https://vespa.pedrodiaz.eu"}
            ]
        ]
    }

def get_photo_inline_keyboard(doc_filename):
    return {
        "inline_keyboard": [
            [
                {"text": "⛽ Ticket Repostaje", "callback_data": f"doccat_{doc_filename}_repostaje"},
                {"text": "💶 Factura / Recambio", "callback_data": f"doccat_{doc_filename}_recambio"}
            ],
            [
                {"text": "📋 ITV / Seguro Legal", "callback_data": f"doccat_{doc_filename}_legal"},
                {"text": "🛵 Foto Vespa / Bitácora", "callback_data": f"doccat_{doc_filename}_foto"}
            ]
        ]
    }

# ---------------------------------------------------------
# VIEW GENERATORS
# ---------------------------------------------------------

def get_status_text():
    data = load_data()
    odo = data.get("odometer", 0)
    fuel_stock = data.get("homeFuelStock", 0)
    
    docs = data.get("documentacion", {})
    if not isinstance(docs, dict):
        docs = {}
    itv = docs.get("itv", {})
    seguro = docs.get("seguro", {})
    
    repostajes = data.get("repostajes", [])
    last_rep_txt = "Ninguno registrado"
    if repostajes:
        last = repostajes[-1]
        last_rep_txt = f"{last.get('litros', 0)} L ({last.get('km', 0)} km) • {last.get('date', '')[:10]}"
        
    last_presion = data.get("presionTracker", "No registrado")
    if last_presion and "T" in str(last_presion):
        last_presion = str(last_presion)[:10]

    return f"""🛵 <b>Vespa PK 125 S Elestart (1984)</b>
🏢 <i>Homelands Labs by Pedro Díaz</i>

━━━━━━━━━━━━━━━━━━━━━━━━
📍 <b>Cuentakilómetros Actual:</b> <code>{odo} km</code>
⛽ <b>Stock Gasolina Garaje:</b> <code>{fuel_stock} L</code>
🛞 <b>Última revisión presiones:</b> <code>{last_presion}</code>
⛽ <b>Último repostaje:</b> {last_rep_txt}
━━━━━━━━━━━━━━━━━━━━━━━━
📋 <b>Control Legal & Vencimientos:</b>
• <b>ITV:</b> <code>{itv.get('fecha_vencimiento', 'No conf.')}</code> ({itv.get('estado', 'Vigente')})
• <b>Seguro:</b> <code>{seguro.get('fecha_vencimiento', 'No conf.')}</code> ({seguro.get('compania', 'Mutua Madrileña')})
• <b>Póliza:</b> <code>{seguro.get('poliza', 'S/N')}</code>
━━━━━━━━━━━━━━━━━━━━━━━━
🌐 <b>PWA Live:</b> https://vespa.pedrodiaz.eu"""

def get_stock_text():
    data = load_data()
    stock_items = data.get("stockCasa", [])
    fuel_stock = data.get("homeFuelStock", 0)
    
    lines = [
        "📦 <b>Stock de Taller & Recambios en Garaje</b>",
        f"⛽ <b>Gasolina Garrafa 2T:</b> <code>{fuel_stock} L</code>\n"
    ]
    if not stock_items:
        lines.append("<i>No hay recambios registrados en el inventario.</i>")
    else:
        for idx, item in enumerate(stock_items, 1):
            qty = item.get("qty", item.get("cantidad", 0))
            nom = item.get("name", item.get("nombre", "Ítem"))
            unit = item.get("unidad", "ud")
            cat = item.get("cat", item.get("categoria", "Recambio"))
            cost = float(item.get("price", item.get("precioUnitario", item.get("precio", 0.0))))
            status_icon = "🟢" if qty > 0 else "⚪"
            lines.append(f"{status_icon} <b>{nom}</b>\n   • Cantidad: <code>{qty} {unit}</code> | Precio: <code>{cost:.2f} €</code> | <i>{cat}</i>")
            
    return "\n".join(lines)

def get_pressure_text():
    return """🛞 <b>Presiones en Frío Recomendadas (3.00 - 10"):</b>

🛵 <b>Conductor Solo (Uso Normal):</b>
• Delante: <code>1.25 bar (18 PSI)</code>
• Detrás: <code>1.80 bar (26 PSI)</code>

👥 <b>Con Pasajero / Carga Máxima:</b>
• Delante: <code>1.25 bar (18 PSI)</code>
• Detrás: <code>2.50 bar (36 PSI)</code>

⏱️ <i>Revisión periódica recomendada cada 3 semanas (21 días).</i>"""

def get_help_text():
    return """🛵 <b>Comandos y Opciones de VespaCare:</b>

📊 <b>Consultas Rápidas:</b>
• /estado — Telemetría actual, cuentakilómetros y legal
• /stock — Recambios y gasolina en garaje
• /presion — Presiones recomendadas en frío
• /web — Enlace directo a la PWA

✍️ <b>Registro Rápido & Lenguaje Natural:</b>
Puedes registrar directamente con lenguaje natural o comandos:
• <code>Compra bombilla freno 10w por 1.5€ en Recambios Ruiz</code>
• <code>repostaje de 3L de aceite a un precio de 4.10€</code>
• <code>/repostar 5.2L 8.50€ 145km</code>
• <code>/gasto 12.30€ Bujía y bombilla piloto</code>
• <code>/km 150</code> (actualiza el cuentakilómetros)
• <code>/garrafa 5L</code> (actualiza stock de gasolina)

📸 <b>Fotos & Facturas:</b>
Envía una foto o PDF de un ticket o factura (con o sin texto explicativo) y se guardará y clasificará en tu expediente.

🎙️ <b>Notas de Voz:</b>
Envía audios en ruta para registrarlos en tu bitácora."""

# ---------------------------------------------------------
# NATURAL LANGUAGE & COMMAND PARSER
# ---------------------------------------------------------

def parse_and_execute_user_input(text, chat_id, attached_doc=None):
    raw = text.strip()
    lower = raw.lower()
    data = load_data()
    now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M")
    now_ts = int(time.time() * 1000)

    # 1. ACTUALIZAR CUENTAKILÓMETROS (/km 150 o km 150)
    km_match = re.search(r'(?:^/km|^km|^actualizar\s*km|odometro)\s*[:=]?\s*(\d+)', lower)
    if km_match:
        new_km = int(km_match.group(1))
        data["odometer"] = new_km
        save_data(data)
        send_message(
            f"✅ <b>Cuentakilómetros actualizado:</b> <code>{new_km} km</code>\n\nSincronizado con la PWA.",
            chat_id,
            reply_markup=get_status_inline_keyboard()
        )
        return True

    # 2. ACTUALIZAR GARRAFA / STOCK GASOLINA (/garrafa 5L o /stockgasolina 5)
    garrafa_match = re.search(r'(?:^/garrafa|^garrafa|^gasolina garaje|^stock gasolina)\s*[:=]?\s*([\d\.,]+)\s*l?', lower)
    if garrafa_match:
        new_fuel = float(garrafa_match.group(1).replace(',', '.'))
        data["homeFuelStock"] = new_fuel
        save_data(data)
        send_message(
            f"⛽ <b>Stock de Gasolina en Garaje actualizado:</b> <code>{new_fuel} L</code>",
            chat_id,
            reply_markup=get_stock_inline_keyboard()
        )
        return True

    # 3. DETECTAR REPOSTAJES O COMPRA DE FLUIDOS (Gasolina / Aceite 2T)
    is_repostaje_intent = any(k in lower for k in ["repostaje", "repostar", "litros de aceite", "l de aceite", "litro de aceite"]) or lower.startswith("/repostar")
    if not is_repostaje_intent and "gasolina" in lower and any(k in lower for k in ["l", "litros", "€", "euros"]):
        is_repostaje_intent = True

    if is_repostaje_intent:
        # Extraer litros
        litros = None
        lit_match = re.search(r'([\d\.,]+)\s*(?:l(?:itros?)?|litro)\b', lower)
        if lit_match:
            litros = float(lit_match.group(1).replace(',', '.'))
        
        # Extraer precio en euros
        precio = 0.0
        price_match = re.search(r'([\d\.,]+)\s*(?:€|euros?|eur)\b', lower)
        if not price_match:
            price_match = re.search(r'(?:precio\s*(?:de|por)?|total\s*(?:de)?|importe\s*(?:de)?|por)\s*[:=]?\s*([\d\.,]+)', lower)
        if price_match:
            precio = float(price_match.group(1).replace(',', '.'))

        # Extraer kilometraje
        km = data.get("odometer", 0)
        km_custom = re.search(r'([\d]+)\s*(?:km|kms|kilometros)\b', lower)
        if km_custom:
            km = int(km_custom.group(1))
            if km > data.get("odometer", 0):
                data["odometer"] = km

        # Detectar si es Aceite 2T o Gasolina
        is_oil = any(k in lower for k in ["aceite", "castrol", "motul", "2t", "lubricante"])
        
        if is_oil:
            title = f"Aceite 2T ({litros or 1}L)" if litros else "Aceite 2T Mezcla"
            notes = f"Registrado vía Telegram Bot • {raw}"
            if attached_doc:
                notes += f" • Doc: {attached_doc}"

            item_exp = {
                "id": f"l_tg_{now_ts}",
                "logType": "pieza",
                "date": now_iso,
                "title": title,
                "price": precio,
                "km": km,
                "notes": notes
            }
            if "inventario" not in data or not isinstance(data["inventario"], list):
                data["inventario"] = []
            data["inventario"].append(item_exp)

            # Actualizar stock si existe ítem de aceite
            stock_list = data.get("stockCasa", [])
            for st in stock_list:
                if "aceite" in st.get("name", st.get("nombre", "")).lower():
                    if litros:
                        cur_q = st.get("qty", st.get("cantidad", 0))
                        st["qty"] = round(cur_q + litros, 2)
                    break
            
            save_data(data)

            send_message(
                f"""✅ <b>Aceite 2T Registrado con Éxito:</b>

🛢️ <b>Concepto:</b> {title}
💶 <b>Coste Total:</b> <code>{precio:.2f} €</code>
📍 <b>Kilometraje:</b> <code>{km} km</code>
📝 <i>{raw}</i>

Sincronizado en el módulo de <b>Gastos & Salud</b> de la PWA.""",
                chat_id,
                reply_markup=get_status_inline_keyboard()
            )
            return True
        else:
            litros = litros or 5.0
            price_per_l = round(precio / litros, 3) if (precio > 0 and litros > 0) else 0.0
            
            rep_entry = {
                "id": f"r_tg_{now_ts}",
                "logType": "repostaje",
                "date": now_iso,
                "title": "Gasolina",
                "price": precio,
                "km": km,
                "litros": litros,
                "notes": f"Registrado vía Telegram Bot • {raw}" + (f" • Ticket: {attached_doc}" if attached_doc else "")
            }
            if "repostajes" not in data or not isinstance(data["repostajes"], list):
                data["repostajes"] = []
            data["repostajes"].append(rep_entry)
            save_data(data)

            send_message(
                f"""⛽ <b>Repostaje Registrado con Éxito:</b>

⛽ <b>Volumen:</b> <code>{litros:.2f} L</code>
💶 <b>Coste Total:</b> <code>{precio:.2f} €</code> {f'({price_per_l:.3f} €/L)' if price_per_l else ''}
📍 <b>Kilometraje:</b> <code>{km} km</code>
🧪 <b>Mezcla 2% sugerida:</b> <code>{int(litros * 20)} ml</code> de Aceite 2T

Sincronizado en vivo con <b>VespaCare PWA</b>.""",
                chat_id,
                reply_markup=get_status_inline_keyboard()
            )
            return True

    # 4. DETECTAR COMPRAS / RECAMBIOS / GASTOS (Ej: 'Compra bombilla freno 10w por 1.5€ en Recambios Ruiz')
    is_purchase_or_expense = (
        lower.startswith("/gasto") or
        lower.startswith("gasto") or
        lower.startswith("compra") or
        lower.startswith("comprado") or
        lower.startswith("compré") or
        "he comprado" in lower or
        "compra de" in lower or
        "factura" in lower or
        ("bombilla" in lower and any(k in lower for k in ["€", "euros", "por", "en"]))
    )

    if is_purchase_or_expense:
        # Extraer precio
        precio = 0.0
        price_match = re.search(r'([\d\.,]+)\s*(?:€|euros?|eur)\b', lower)
        if not price_match:
            price_match = re.search(r'(?:por|precio|importe|total|gasto)\s*[:=]?\s*([\d\.,]+)', lower)
        if price_match:
            precio = float(price_match.group(1).replace(',', '.'))

        # Extraer tienda / proveedor (ej: "en Recambios Ruiz")
        tienda_match = re.search(r'\b(?:en|de|tienda)\s+([A-ZÁÉÍÓÚa-záéíóú0-9\s\.\-_]+?)(?:\s*(?:por|el|a|\.|$))', raw)
        tienda = tienda_match.group(1).strip() if tienda_match else ""

        # Extraer concepto limpio
        concepto = raw
        # Quitar palabras clave iniciales
        concepto = re.sub(r'^(?:/gasto|gasto|compra(?:do)?|compré|he comprado)\s*(?:de)?', '', concepto, flags=re.IGNORECASE).strip()
        # Quitar importe
        concepto = re.sub(r'(?:por\s*)?[\d\.,]+\s*(?:€|euros?|eur)\b', '', concepto, flags=re.IGNORECASE).strip()
        concepto = re.sub(r'^[,\s:-]+|[,\s:-]+$', '', concepto) or "Recambio Vespa"

        km = data.get("odometer", 0)
        km_custom = re.search(r'([\d]+)\s*(?:km|kms)\b', lower)
        if km_custom:
            km = int(km_custom.group(1))

        # Registrar en inventario de Gastos
        if "inventario" not in data or not isinstance(data["inventario"], list):
            data["inventario"] = []

        gasto_id = f"l_tg_{now_ts}"
        note_str = f"Compra: {raw}"
        if tienda:
            note_str += f" • Proveedor: {tienda}"
        if attached_doc:
            note_str += f" • Archivo: {attached_doc}"

        data["inventario"].append({
            "id": gasto_id,
            "logType": "pieza",
            "date": now_iso,
            "title": f"Compra Recambio: {concepto[:50]}",
            "price": precio,
            "km": km,
            "notes": note_str
        })

        # Smart Stock Match: Comprobar si existe en stockCasa para actualizar cantidad y precio
        matched_stock = None
        stock_list = data.get("stockCasa", [])
        
        # Palabras clave de búsqueda
        keywords = [k for k in re.split(r'[\s,]+', lower) if len(k) > 2 and k not in ["por", "para", "con", "del", "las", "los", "recambios", "compra", "gasto", "euros"]]
        
        for item in stock_list:
            item_name = item.get("name", item.get("nombre", "")).lower()
            item_id = item.get("id", "").lower()
            # Si coinciden 2 palabras clave o el ID específico
            matches = sum(1 for kw in keywords if kw in item_name or kw in item_id)
            if matches >= 2 or (len(keywords) == 1 and keywords[0] in item_name):
                matched_stock = item
                break

        if matched_stock:
            cur_qty = matched_stock.get("qty", matched_stock.get("cantidad", 0))
            matched_stock["qty"] = cur_qty + 1
            matched_stock["price"] = precio
            if tienda:
                matched_stock["notes"] = f"Comprada en {tienda} ({precio:.2f}€) • En estantería garaje"
            stock_msg = f"\n📦 <b>Stock Actualizado:</b> {matched_stock.get('name')} (+1 ud -> Total: <code>{matched_stock['qty']} ud</code>)"
        else:
            # Añadir nuevo ítem a stock si no existe
            new_item_id = f"stk_tg_{int(time.time()%10000)}"
            cat = "Iluminación" if any(k in lower for k in ["bombilla", "faro", "piloto", "led", "luz"]) else "Recambio"
            stock_list.append({
                "id": new_item_id,
                "name": concepto,
                "cat": cat,
                "qty": 1,
                "price": precio,
                "icon": "fa-wrench",
                "color": "text-purple-600",
                "notes": f"Comprado en {tienda or 'tienda'} ({precio:.2f}€) • En estantería"
            })
            data["stockCasa"] = stock_list
            stock_msg = f"\n📦 <b>Nuevo Ítem Creado en Stock:</b> {concepto} (1 ud)"

        save_data(data)

        send_message(
            f"""🛒 <b>Compra Registrada con Éxito:</b>

🏷️ <b>Artículo:</b> {concepto}
💶 <b>Importe:</b> <code>{precio:.2f} €</code>
🏪 <b>Tienda:</b> {tienda or 'Registrado en Garaje'}
📍 <b>Kilometraje:</b> <code>{km} km</code>{stock_msg}

Sincronizado en <b>Gastos</b> y <b>Stock Taller</b> en la PWA.""",
            chat_id,
            reply_markup=get_stock_inline_keyboard()
        )
        return True

    return False

# ---------------------------------------------------------
# HANDLERS
# ---------------------------------------------------------

def handle_callback_query(cq):
    cq_id = cq.get("id")
    from_user = cq.get("from", {})
    chat_id = cq.get("message", {}).get("chat", {}).get("id", ADMIN_CHAT_ID)
    msg_id = cq.get("message", {}).get("message_id")
    data_cb = cq.get("data", "")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Callback Query: '{data_cb}' from {from_user.get('id')}", flush=True)

    if data_cb == "cmd_estado":
        answer_callback_query(cq_id, "Actualizando estado...")
        edit_message_text(get_status_text(), chat_id, msg_id, reply_markup=get_status_inline_keyboard())

    elif data_cb == "cmd_stock":
        answer_callback_query(cq_id, "Consultando stock de garaje...")
        edit_message_text(get_stock_text(), chat_id, msg_id, reply_markup=get_stock_inline_keyboard())

    elif data_cb == "cmd_presion":
        answer_callback_query(cq_id, "Presiones en frío")
        edit_message_text(get_pressure_text(), chat_id, msg_id, reply_markup=get_pressure_inline_keyboard())

    elif data_cb == "act_presion_ok":
        data = load_data()
        today_str = datetime.now().strftime("%Y-%m-%d")
        data["presionTracker"] = today_str
        save_data(data)
        answer_callback_query(cq_id, "✅ Presiones marcadas como revisadas hoy", show_alert=True)
        edit_message_text(
            f"✅ <b>Revisión de Presiones Registrada:</b> <code>{today_str}</code>\n\nPróxima revisión en 21 días.\n\n" + get_pressure_text(),
            chat_id,
            msg_id,
            reply_markup=get_status_inline_keyboard()
        )

    elif data_cb.startswith("doccat_"):
        parts = data_cb.split("_")
        if len(parts) >= 3:
            doc_file = parts[1]
            cat = parts[2]
            answer_callback_query(cq_id, f"Documento clasificado como {cat}")
            
            data = load_data()
            if "documentos" not in data or not isinstance(data["documentos"], list):
                data["documentos"] = []
            
            data["documentos"].append({
                "id": f"doc_{int(time.time()*1000)}",
                "title": f"Archivo adjunto ({cat.capitalize()})",
                "category": cat,
                "filename": doc_file,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "notes": "Subido vía Telegram Bot"
            })
            save_data(data)
            
            edit_message_text(
                f"✅ <b>Documento Clasificado:</b> <code>{doc_file}</code>\n📂 <b>Categoría:</b> {cat.upper()}\n\nGuardado en el expediente documental de VespaCare.",
                chat_id,
                msg_id,
                reply_markup=get_status_inline_keyboard()
            )

def handle_message(msg):
    chat_id = msg.get("chat", {}).get("id")
    msg_id = msg.get("message_id")
    raw_text = msg.get("text") or msg.get("caption") or ""
    text = raw_text.strip().lower()

    if not chat_id:
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing message from {chat_id}: '{raw_text[:60]}'", flush=True)

    # 1. GESTIÓN DE NOTAS DE VOZ / AUDIO
    voice = msg.get("voice") or msg.get("audio")
    if voice:
        file_id = voice.get("file_id")
        duration = voice.get("duration", 0)
        file_info = get_file_info(file_id)
        if file_info and "file_path" in file_info:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            voice_filename = f"voice_{ts}_{file_id[:8]}.oga"
            local_path = os.path.join(VOICE_DIR, voice_filename)
            if download_telegram_file(file_info["file_path"], local_path):
                send_message(
                    f"""🎙️ <b>Nota de Voz Recibida & Archivada:</b>

⏱️ <b>Duración:</b> <code>{duration} s</code>
📁 <b>Archivo:</b> <code>{voice_filename}</code>
🔒 <b>Almacenamiento:</b> Guardado seguro en servidor <code>blue</code> (Zero-Trust).

<i>La nota de voz queda registrada en la bitácora técnica de VespaCare.</i>""",
                    chat_id,
                    reply_markup=get_status_inline_keyboard()
                )
                return

    # 2. GESTIÓN DE FOTOS / TICKETS / DOCUMENTOS
    photos = msg.get("photo")
    document = msg.get("document")
    if photos or document:
        file_id = photos[-1]["file_id"] if photos else document.get("file_id")
        orig_name = document.get("file_name", "ticket.jpg") if document else "foto_vespa.jpg"
        ext = orig_name.split(".")[-1].lower() if "." in orig_name else "jpg"
        if ext not in ["jpg", "jpeg", "png", "webp", "pdf"]:
            ext = "jpg"

        file_info = get_file_info(file_id)
        if file_info and "file_path" in file_info:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            doc_filename = f"doc_{ts}_{int(time.time()%10000)}.{ext}"
            local_path = os.path.join(DOCS_DIR, doc_filename)
            
            if download_telegram_file(file_info["file_path"], local_path):
                # Si viene con texto explicativo (caption), parsearlo
                if raw_text:
                    if parse_and_execute_user_input(raw_text, chat_id, attached_doc=doc_filename):
                        return
                
                # Si no viene con caption o no fue reconocido como comando específico, ofrecer botones de clasificación
                send_message(
                    f"""📸 <b>Imagen / Factura Recibida:</b>

📁 <b>Archivo:</b> <code>{doc_filename}</code>
🔒 <b>Estado:</b> Guardada en el expediente de VespaCare.

¿Cómo deseas clasificar este archivo?""",
                    chat_id,
                    reply_markup=get_photo_inline_keyboard(doc_filename)
                )
                return

    # 3. COMANDOS BÁSICOS & BOTONES DEL TECLADO
    if text.startswith("/start"):
        send_message(
            """👋 ¡Hola <b>Pedro</b>! Bienvenido al asistente inteligente <b>VespaCare</b>.

Gestiono la telemetría, mantenimiento, stock y bitácora de tu <b>Vespa PK 125 S Elestart (1984)</b>.

Puedes usar los botones táctiles inferiores o escribir directamente tus repostajes y compras.""",
            chat_id,
            reply_markup=get_persistent_reply_keyboard()
        )
        return

    if text in ["/estado", "estado", "📊 estado", "/resumen", "resumen"]:
        send_message(get_status_text(), chat_id, reply_markup=get_status_inline_keyboard())
        return

    if text in ["/stock", "stock", "📦 stock taller", "recambios"]:
        send_message(get_stock_text(), chat_id, reply_markup=get_stock_inline_keyboard())
        return

    if text in ["/presion", "presion", "presiones", "🛞 presiones"]:
        send_message(get_pressure_text(), chat_id, reply_markup=get_pressure_inline_keyboard())
        return

    if text in ["/web", "web", "🌐 abrir vespacare pwa", "pwa", "abrir web"]:
        send_message("🛵 <b>VespaCare PWA:</b> https://vespa.pedrodiaz.eu", chat_id, reply_markup=get_status_inline_keyboard())
        return

    if text in ["/ayuda", "/help", "ayuda", "help", "❓ ayuda"]:
        send_message(get_help_text(), chat_id, reply_markup=get_status_inline_keyboard())
        return

    if text in ["⛽ repostar", "repostar"]:
        send_message(
            "⛽ <b>Para registrar un repostaje escribe:</b>\n\n<code>repostaje 5.5L 8.90€ 140km</code>\n\nO envía la foto del ticket con el texto.",
            chat_id
        )
        return

    if text in ["💶 añadir gasto", "gasto"]:
        send_message(
            "💶 <b>Para registrar un gasto o compra escribe:</b>\n\n<code>Compra bombilla freno 10w por 1.5€ en Recambios Ruiz</code>\n\nO envía la foto de la factura.",
            chat_id
        )
        return

    # 4. INTENTAR PROCESAR COMO LENGUAJE NATURAL (Compras, Recambios, Gasolina, Km)
    if parse_and_execute_user_input(raw_text, chat_id):
        return

    # 5. MENSAJE POR DEFECTO
    send_message(
        f"Recibido: <i>'{raw_text}'</i>.\n\nPuedes usar los botones táctiles o consultar /ayuda para ver los formatos de registro rápido.",
        chat_id,
        reply_markup=get_persistent_reply_keyboard()
    )

def handle_update(update):
    if "callback_query" in update:
        handle_callback_query(update["callback_query"])
    elif "message" in update:
        handle_message(update["message"])

def main():
    print("=== VespaCare Telegram Intelligent Daemon (v2.1) Starting ===", flush=True)
    offset = None
    while True:
        try:
            url = f"{BASE_URL}/getUpdates?timeout=15"
            if offset:
                url += f"&offset={offset}"
            req = urllib.request.Request(url, headers={"User-Agent": "HomelandsLabs-VespaCareBot/2.1"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                res = json.loads(resp.read().decode())
                if res.get("ok"):
                    for update in res.get("result", []):
                        offset = update["update_id"] + 1
                        handle_update(update)
        except Exception as e:
            print(f"Polling loop notice: {e}", flush=True)
            time.sleep(2)

if __name__ == "__main__":
    main()
