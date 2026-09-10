<?php
header('Content-Type: application/json');

$file = __DIR__ . '/data.json';
$backupDir = __DIR__ . '/backups';

if (!is_dir($backupDir)) {
    @mkdir($backupDir, 0775, true);
}

// Zero-Trust: Validación de PIN para lectura y escritura
function checkPin() {
    $pin = $_SERVER['HTTP_X_VESPA_PIN'] ?? $_GET['pin'] ?? '';
    if ($pin !== '1960') {
        http_response_code(401);
        echo json_encode(['status' => 'error', 'message' => 'PIN de seguridad no válido']);
        exit;
    }
}

$action = $_GET['action'] ?? '';

// Verificación rápida de PIN
if ($action === 'verify_pin') {
    checkPin();
    echo json_encode(['status' => 'success', 'message' => 'PIN verificado']);
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
