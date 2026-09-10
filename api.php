<?php
header('Content-Type: application/json');

$file = __DIR__ . '/data.json';
$configFile = __DIR__ . '/pin_config.json';
$backupDir = __DIR__ . '/backups';
$docsDir = __DIR__ . '/docs';

if (!is_dir($backupDir)) {
    @mkdir($backupDir, 0775, true);
}
if (!is_dir($docsDir)) {
    @mkdir($docsDir, 0775, true);
    // Proteger acceso directo con .htaccess en Apache
    @file_put_contents($docsDir . '/.htaccess', "Deny from all\n");
}

// Obtener configuración de PIN del servidor
function getPinConfig() {
    global $configFile;
    if (file_exists($configFile)) {
        $cfg = json_decode(file_get_contents($configFile), true);
        if (is_array($cfg)) return $cfg;
    }
    return ['pin' => '1984', 'enabled' => true];
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
    $clientPin = $_SERVER['HTTP_X_VESPA_PIN'] ?? $_GET['pin'] ?? $_POST['pin'] ?? '';
    if ($clientPin !== (string)$cfg['pin']) {
        http_response_code(401);
        echo json_encode(['status' => 'error', 'message' => 'PIN de seguridad no válido']);
        exit;
    }
    return true;
}

$action = $_GET['action'] ?? $_POST['action'] ?? '';

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

// --- GESTIÓN DOCUMENTAL ZERO-TRUST ---

// 1. Ver / Servir Documento Seguro (Streaming)
if ($action === 'view_doc') {
    checkPin();
    $filename = basename($_GET['file'] ?? '');
    $filePath = $docsDir . '/' . $filename;
    if (empty($filename) || !file_exists($filePath)) {
        http_response_code(404);
        header('Content-Type: application/json');
        echo json_encode(['status' => 'error', 'message' => 'Documento no encontrado']);
        exit;
    }

    $ext = strtolower(pathinfo($filePath, PATHINFO_EXTENSION));
    $mimeTypes = [
        'pdf'  => 'application/pdf',
        'jpg'  => 'image/jpeg',
        'jpeg' => 'image/jpeg',
        'png'  => 'image/png',
        'webp' => 'image/webp',
        'txt'  => 'text/plain'
    ];
    $contentType = $mimeTypes[$ext] ?? 'application/octet-stream';
    $download = !empty($_GET['download']);

    header('Content-Type: ' . $contentType);
    header('Content-Length: ' . filesize($filePath));
    if ($download) {
        header('Content-Disposition: attachment; filename="' . $filename . '"');
    } else {
        header('Content-Disposition: inline; filename="' . $filename . '"');
    }
    header('Cache-Control: private, max-age=3600');
    readfile($filePath);
    exit;
}

// 2. Subir Documento Seguro
if ($action === 'upload_doc') {
    checkPin();
    if (!isset($_FILES['file']) || $_FILES['file']['error'] !== UPLOAD_ERR_OK) {
        http_response_code(400);
        echo json_encode(['status' => 'error', 'message' => 'Error al recibir el archivo']);
        exit;
    }

    $uploaded = $_FILES['file'];
    $ext = strtolower(pathinfo($uploaded['name'], PATHINFO_EXTENSION));
    $allowed = ['pdf', 'jpg', 'jpeg', 'png', 'webp', 'txt'];
    if (!in_array($ext, $allowed)) {
        http_response_code(400);
        echo json_encode(['status' => 'error', 'message' => 'Tipo de archivo no permitido. Solo PDF o imágenes (JPG/PNG).']);
        exit;
    }

    // Sanitizar nombre y añadir timestamp único
    $category = preg_replace('/[^a-zA-Z0-9_-]/', '', $_POST['category'] ?? 'doc');
    $safeName = preg_replace('/[^a-zA-Z0-9._-]/', '_', pathinfo($uploaded['name'], PATHINFO_FILENAME));
    $finalFilename = $category . '_' . date('Ymd_His') . '_' . substr(md5(uniqid()), 0, 6) . '.' . $ext;
    $dest = $docsDir . '/' . $finalFilename;

    if (move_uploaded_file($uploaded['tmp_name'], $dest)) {
        chmod($dest, 0664);
        echo json_encode([
            'status' => 'success',
            'message' => 'Documento guardado correctamente',
            'filename' => $finalFilename,
            'original_name' => $uploaded['name'],
            'size' => filesize($dest),
            'ext' => $ext,
            'uploaded_at' => date('Y-m-d H:i:s')
        ]);
    } else {
        http_response_code(500);
        echo json_encode(['status' => 'error', 'message' => 'No se pudo mover el archivo al almacenamiento']);
    }
    exit;
}

// 3. Borrar Documento
if ($action === 'delete_doc') {
    checkPin();
    $body = json_decode(file_get_contents('php://input'), true);
    $filename = basename($body['filename'] ?? '');
    $filePath = $docsDir . '/' . $filename;
    if ($filename && file_exists($filePath)) {
        @unlink($filePath);
        echo json_encode(['status' => 'success', 'message' => 'Documento eliminado']);
    } else {
        http_response_code(404);
        echo json_encode(['status' => 'error', 'message' => 'Archivo no encontrado']);
    }
    exit;
}

// Bloqueo Zero-Trust para cualquier petición regular
checkPin();

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    if (file_exists($file)) {
        echo file_get_contents($file);
    } else {
        echo json_encode([
            'odometer' => 0,
            'mantenimientos' => [],
            'repostajes' => [],
            'inventario' => [],
            'bombillas' => [],
            'documentos' => [],
            'documentacion' => [],
            'homeFuelStock' => 0
        ]);
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
