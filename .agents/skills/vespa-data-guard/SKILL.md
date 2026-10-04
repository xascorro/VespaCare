---
name: vespa-data-guard
description: Procedimientos seguros para consultar, modificar y respaldar los ficheros clave de datos en VespaCare (data.json y pin_config.json) evitando corrupción de datos.
---

# Vespa Data Guard Skill

Esta skill define el protocolo de seguridad para la manipulación de datos en VespaCare (`/home/ubuntu/VespaCare`).

## Archivos Críticos
1. `data.json`: Contiene el historial de mantenimientos, repostajes y estado de los vehículos.
2. `pin_config.json`: Contiene la configuración de seguridad y credenciales/PIN de acceso.

## 1. Protocolo de Backup Obligatorio
Antes de modificar cualquiera de estos archivos, SIEMPRE crear una copia de seguridad con timestamp:
```bash
cd /home/ubuntu/VespaCare
cp data.json data.json.bak.$(date +%Y%m%d_%H%M%S)
cp pin_config.json pin_config.json.bak.$(date +%Y%m%d_%H%M%S)
```

## 2. Validación de JSON tras Modificaciones
Nunca dejar un JSON sin validar sintácticamente:
```bash
python3 -m json.tool data.json > /dev/null && echo "data.json válido" || echo "ERROR en data.json"
python3 -m json.tool pin_config.json > /dev/null && echo "pin_config.json válido" || echo "ERROR en pin_config.json"
```

## 3. Cache-Busting en Frontend
Si se modifican scripts JS o CSS que consumen estos archivos, actualizar la query string de versión en el HTML:
```html
<script src="app.js?v=20260929"></script>
```
