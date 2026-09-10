<?php
header('Content-Type: application/json');

$file = __DIR__ . '/data.json';
$configFile = __DIR__ . '/pin_config.json';
$backupDir = __DIR__ . '/backups';

if (!is_dir($backupDir)) {
    @mkdir($backupDir, 0775, true);
}

// Obtener configuración de PIN del servidor
function getPinConfig() {
    global $configFile;
    if (file_exists($configFile)) {
        $cfg = json_decode(file_get_contents($configFile), true);
        if (is_array($cfg)) return $cfg;
    }
    return ['pin' => '1960', 'enabled' => true];
}

function savePinConfig($cfg) {
    global $configFile;
    file_put_contents($configFile, json_encode($cfg, JSON_PRETTY_PRINT));
}

// Zero-Trust: Validación de PIN para lectura y escritura
function checkPin() {
    $cfg = getPinConfig();
    // Si la protección por PIN está desactivada en el servidor, permitir acceso
    if (!$cfg['enabled'] || empty($cfg['pin'])) {
        return true;
    }
    $clientPin = $_SERVER['HTTP_X_VESPA_PIN'] ?? $_GET['pin'] ?? '';
    if ($clientPin !== (string)$cfg['pin']) {
        http_response_code(401);
        echo json_encode(['status' => 'error', 'message' => 'PIN de seguridad no válido']);
        exit;
    }
    return true;
}

$action = $_GET['action'] ?? '';

// Endpoint público para que la app sepa si el PIN está activado
if ($action === 'pin_status') {
    $cfg = getPinConfig();
    echo json_encode([
        'status' => 'success',
        'enabled' => !empty($cfg['enabled']) && !empty($cfg['pin'])
    ]);
    exit;
}

// Verificación rápida de PIN
if ($action === 'verify_pin') {
    checkPin();
    echo json_encode(['status' => 'success', 'message' => 'PIN verificado']);
    exit;
}

// Cambiar o desactivar PIN (requiere autenticación con el PIN actual si estaba activo)
if ($action === 'change_pin') {
    checkPin();
    $body = json_decode(file_get_contents('php://input'), true);
    $newPin = trim((string)($body['new_pin'] ?? ''));
    $enabled = !empty($body['enabled']);

    if ($enabled && (strlen($newPin) !== 4 || !ctype_digit($newPin))) {
        http_response_code(400);
        echo json_encode(['status' => 'error', 'message' => 'El PIN debe contener exactamente 4 dígitos numéricos']);
        exit;
    }

    savePinConfig([
        'pin' => $enabled ? $newPin : '',
        'enabled' => $enabled
    ]);

    echo json_encode([
        'status' => 'success',
        'message' => $enabled ? 'PIN de seguridad actualizado correctamente' : 'Protección por PIN desactivada',
        'enabled' => $enabled
    ]);
    exit;
}

// Bloqueo Zero-Trust para cualquier petición
checkPin();

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    if (file_exists($file)) {
        echo file_get_contents($file);
    } else {
        echo json_encode(['odometer' => 0, 'mantenimientos' => [], 'repostajes' => [], 'inventario' => [], 'bombillas' => [], 'homeFuelStock' => 0]);
    }
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Crear snapshot en servidor
    if ($action === 'snapshot') {
        if (file_exists($file)) {
            $timestamp = date('Ymd_His');
            $snapFile = "{$backupDir}/data_snap_{$timestamp}.json";
            copy($file, $snapFile);
            echo json_encode(['status' => 'success', 'snapshot' => basename($snapFile)]);
        } else {
            http_response_code(404);
            echo json_encode(['status' => 'error', 'message' => 'data.json no encontrado']);
        }
        exit;
    }

    $data = file_get_contents('php://input');
    if ($decoded = json_decode($data, true)) {
        // Auto-crear snapshot previo al guardar
        if (file_exists($file)) {
            $timestamp = date('Ymd_His');
            @copy($file, "{$backupDir}/data_autosave_{$timestamp}.json");
            
            // Mantener solo los últimos 15 autosaves
            $files = glob("{$backupDir}/data_autosave_*.json");
            if (count($files) > 15) {
                usort($files, function($a, $b) { return filemtime($a) - filemtime($b); });
                $toDelete = array_slice($files, 0, count($files) - 15);
                foreach ($toDelete as $f) @unlink($f);
            }
        }
        
        file_put_contents($file, json_encode($decoded, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
        echo json_encode(['status' => 'success']);
    } else {
        http_response_code(400);
        echo json_encode(['status' => 'error', 'message' => 'JSON inválido']);
    }
    exit;
}
