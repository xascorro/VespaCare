# 🛵 VespaCare — PWA Telemetry & Maintenance

**VespaCare** es una Progressive Web App (PWA) moderna, ligera y autosuficiente diseñada específicamente para el seguimiento de mantenimiento, telemetría de combustible, gestión eléctrica y control legal de una **Vespa PK 125 S Elestart (1984)**.

![VespaCare](icon-192.png)

---

## ⚡ Características Principales

1. **🔒 Zero-Trust App Lock & Gestión Dinámica de PIN:**
   - **Pantalla de bloqueo nativa en PWA** con teclado numérico táctil y feedback háptico/visual.
   - **Gestión directa desde la App:** Cambio de PIN o activación/desactivación del bloqueo desde el menú de Ajustes sin tocar código ni reiniciar servicios.
   - **Acceso Directo Opcional:** Si se desactiva la protección por PIN, la app omite la pantalla de bloqueo y la API opera sin exigir cabecera de autenticación.
   - **Almacenamiento Aislado:** Configuración del PIN guardada en el servidor (`pin_config.json`, protegido por `.gitignore`).

2. **📂 Guantera Digital & Gestión Documental:**
   - **Almacenamiento Seguro:** Directorio `/docs/` protegido con streaming autenticado Zero-Trust (sin acceso directo por URL).
   - **Enlace Legal:** Adjunta pólizas de Seguro e informes de ITV directamente a sus registros con botón "Ver Doc".
   - **Manuales & Esquemas:** Sube y visualiza manuales de taller (PDF), esquemas eléctricos, fichas técnicas o facturas de recambios.
   - **Visor Integrado:** Modal para previsualizar PDFs e imágenes o descargarlos directamente al dispositivo.

3. **⛽ Telemetría de Combustible & Mezcla:**
   - Estimación reactiva de autonomía restante en tiempo real basada en el histórico de consumos.
   - Calculadora instantánea de mezcla 2T (2.0%, 2.5%, 3.0%).
   - Control de stock de gasolina en garrafa doméstica (*Home Fuel Stock*).
   - Métricas clave: coste por cada 100 km, precio medio por litro y consumo medio `km/L`.

4. **🛠️ Subsistemas Mecánicos & Mantenimiento:**
   - **Motor & Transmisión:** Ficha técnica de carburación (SHBC 19/19 E), aceite de cárter (SAE 30) y diagnóstico visual de color de bujía (NGK B7HS).
   - **Sistema Eléctrico 12V Ducati:** Registro rápido de batería 12V 9Ah (YB9-B) y regulador de tensión.
   - **Iluminación (8 casquillos):** Catálogo completo de bombillas diferenciadas por circuito AC (motor) y DC (batería).
   - **Chasis & Neumáticos (3.00 - 10"):** Presiones recomendadas en frío (solo/acompañante) con recordatorio periódico por tiempo (cada 3 semanas) y kilometraje.

5. **📋 Control Legal (ITV & Seguro):**
   - Seguimiento dinámico de fechas de vencimiento y fecha de emisión/trámite con alertas preventivas en el checklist pre-rodaje de *Garaje*.
   - Integración automática de gastos al renovar.

6. **📊 Gráficas & Histórico:**
   - Gráficas interactivas con Chart.js (evolución de kilometraje, rendimiento `km/L` y precio de gasolina).

---

## 🚀 Despliegue Rápido

1. Clonar el repositorio en tu servidor web (Nginx / Apache + PHP 8.x):
   ```bash
   git clone https://github.com/xascorro/VespaCare.git
   cd VespaCare
   ```

2. Copiar el archivo de datos de ejemplo:
   ```bash
   cp data.json.example data.json
   chmod 664 data.json
   ```

3. **Configuración de Seguridad (PIN):**
   - Por defecto el PIN inicial es `1984`.
   - Puedes cambiarlo o desactivarlo en cualquier momento directamente desde la sección **Ajustes > Seguridad & Acceso (PIN)** dentro de la propia aplicación.

4. Abrir en tu navegador o instalar como **PWA** en iOS / Android.

---

## 👨‍💻 Autor & Ecosistema
Desarrollado para **Homelands Labs by Pedro Díaz** (Fables Infrastructure).
