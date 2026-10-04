# VespaCare — Directrices de Desarrollo y Despliegue Obligatorio

Este archivo contiene las reglas permanentes de infraestructura, arquitectura y despliegue de **VespaCare**. Se cargan automáticamente en el contexto del asistente.

---

## 🏛️ 1. Arquitectura y Servidor Único de Producción

VespaCare reside y opera de forma oficial y única en el nodo **`blue`**:

| Entorno | Servidor / Nodo | Ubicación | Función |
| :--- | :--- | :--- | :--- |
| **Producción Oficial** | `blue` (`10.0.0.104`) | `/var/www/html/vespa` | Servidor Nginx + PHP 8.3 que sirve `https://vespa.pedrodiaz.eu`. |
| **Repositorio Remoto** | GitHub | `git@github.com:xascorro/VespaCare.git` | Control de versiones (rama `main`). |
| **Bot Daemon Telegram** | `blue` (`10.0.0.104`) | `vespacare-bot.service` | Servicio systemd activo 24/7 en el nodo `blue`. |

---

## 🚀 2. Protocolo Obligatorio de Despliegue en Vivo

Cualquier cambio realizado en el código (`index.html`, `sw.js`, `api.php`, `telegram_bot.py`, `bot_daemon.py`, etc.) se DEBE desplegar **inmediata y automáticamente** al servidor `blue`:

### Paso 1: Incrementar versión de Service Worker / Caché
* Incrementar `CACHE_NAME` en `sw.js` (ej: `vespacare-v40`, `vespacare-v41`).
* Actualizar el registro en `index.html` (`/sw.js?v=XX`) y el indicador de versión en la pestaña de Ajustes.

### Paso 2: Commit y Push a GitHub
```bash
git add .
git commit -m "feat/fix: descripción de los cambios"
git push origin main
```

### Paso 3: Sincronizar archivos al servidor `blue`
```bash
scp index.html sw.js api.php telegram_bot.py bot_daemon.py blue:/var/www/html/vespa/
```

### Paso 4: Ajustar permisos y reiniciar daemon en `blue`
```bash
ssh blue "sudo systemctl restart vespacare-bot.service && sudo chown -R www-data:www-data /var/www/html/vespa/"
```

### Paso 5: Verificación en vivo
```bash
curl -IL https://vespa.pedrodiaz.eu
```

---

## ⛽ 3. Parámetros Técnicos de la Vespa PK 125 S Elestart (1984)

* **Capacidad del depósito (`tankCapacity`):** **5.0 Litros** (incluye reserva manual de ~1.2L).
* **Consumo medio habitual:** ~16.5 km/L (autonomía depósito lleno: ~83 km).
* **Bujía recomendada:** NGK B7HS (rosca corta), galga 0.5 - 0.6 mm, intervalo cada 2.000 km.
* **Presiones de neumáticos (3.00 - 10"):**
  * Delantera: **1.25 bar** (18 PSI)
  * Trasera solo: **1.80 bar** (26 PSI)
  * Trasera con pasajero: **2.50 bar** (36 PSI)
  * Intervalo de comprobación: cada 3 semanas (21 días).
* **Aceite de cárter/caja:** 250 ml de SAE 30 Mineral.
* **Mezcla 2T:** 2.0% (1:50) con aceite sintético JASO FD.

---

## 🤖 4. Reglas de Trabajo para AGY
1. **Directorio Raíz**: Toda consulta, análisis o modificación debe tomar como referencia el directorio `/home/ubuntu/VespaCare`.
2. **Seguridad y Persistencia de Datos**:
   - `data.json` es la fuente principal de datos. Respeta siempre su estructura JSON y permisos `664`.
   - `pin_config.json` contiene la clave de acceso Zero-Trust. Nunca exponer ni alterar credenciales sin orden explícita.
3. **Control de Versiones y Despliegue**:
   - Cada cambio en `index.html` o `sw.js` requiere actualizar el número de versión de caché para que los dispositivos móviles/PWA descarguen la última versión sin quedar bloqueados en caché.
4. **Auto-resumen de sesión por desconexiones**:
   - Al finalizar un trabajo o bloque importante en este directorio, crea/actualiza el archivo `.last_session_summary.txt` en la raíz del proyecto con un resumen muy breve de los cambios realizados, archivos modificados y estado del proyecto. Esto permitirá al usuario ver de un vistazo qué se hizo si se le corta la conexión SSH en el móvil.
