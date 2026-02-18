<?php

// 引入ApiManager类
require_once 'api_manager.php';

// 设置响应头
header('Content-Type: application/json; charset=utf-8');

// 允许跨域请求
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

// 处理OPTIONS请求
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

// 创建ApiManager实例
$apiManager = new ApiManager();

// 管理员认证信息
$ADMIN_USERNAME = 'admin';
$ADMIN_PASSWORD = '127127sun';

// 获取请求方法和路径
$method = $_SERVER['REQUEST_METHOD'];
$path = $_GET['path'] ?? '';

// 认证函数
function authenticate() {
    global $ADMIN_USERNAME, $ADMIN_PASSWORD;
    
    // 获取Authorization头
    $authHeader = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    
    if (empty($authHeader)) {
        return false;
    }
    
    // 解析Basic Auth
    list($authType, $authCredentials) = explode(' ', $authHeader, 2);
    if (strtolower($authType) !== 'basic') {
        return false;
    }
    
    // 解码凭证
    $credentials = base64_decode($authCredentials);
    list($username, $password) = explode(':', $credentials, 2);
    
    // 验证用户名和密码
    return $username === $ADMIN_USERNAME && $password === $ADMIN_PASSWORD;
}

// 需要认证的路径列表
$protectedPaths = [
    'models',
    'get_models_with_index',
    'preferred_model',
    'preferred_model_config',
    'delete_model'
];

// 检查是否需要认证
if (in_array($path, $protectedPaths)) {
    if (!authenticate()) {
        header('WWW-Authenticate: Basic realm="API Manager"');
        sendResponse(['error' => '未授权访问'], 401);
    }
}

// 处理请求
switch ($method) {
    case 'GET':
        handleGetRequest($apiManager, $path);
        break;
    case 'POST':
        handlePostRequest($apiManager, $path);
        break;
    default:
        sendResponse(['error' => '不支持的请求方法'], 405);
}

// 处理GET请求
function handleGetRequest($apiManager, $path) {
    switch ($path) {
        case 'models':
            // 获取所有模型
            $models = $apiManager->getAllModels();
            sendResponse(['models' => $models]);
            break;
        case 'get_models_with_index':
            // 获取带序号的模型列表
            $modelDetails = $apiManager->getAllModelsWithDetails();
            sendResponse(['models' => $modelDetails]);
            break;
        case 'preferred_model':
            // 获取首选模型
            $preferredModel = $apiManager->getPreferredModel();
            sendResponse(['preferred_model' => $preferredModel]);
            break;
        case 'preferred_model_config':
            // 获取首选模型配置
            $config = $apiManager->getPreferredModelConfig();
            sendResponse(['config' => $config]);
            break;
        default:
            sendResponse(['error' => '无效的API路径'], 404);
    }
}

// 处理POST请求
function handlePostRequest($apiManager, $path) {
    $data = json_decode(file_get_contents('php://input'), true);
    
    switch ($path) {
        case 'add_api':
            // 添加API信息
            $model = $data['model'] ?? '';
            $baseUrl = $data['base_url'] ?? '';
            $apiKey = $data['api_key'] ?? '';
            
            if (empty($model) || empty($baseUrl) || empty($apiKey)) {
                sendResponse(['error' => '缺少必要参数'], 400);
            }
            
            $result = $apiManager->addApiInfo($model, $baseUrl, $apiKey);
            sendResponse(['success' => $result]);
            break;
        case 'set_preferred_model':
            // 设置首选模型
            $model = $data['model'] ?? '';
            
            if (empty($model)) {
                sendResponse(['error' => '缺少模型参数'], 400);
            }
            
            $result = $apiManager->setPreferredModel($model);
            sendResponse(['success' => $result]);
            break;
        case 'delete_model':
            // 删除模型
            $index = $data['index'] ?? null;
            $model = $data['model'] ?? '';
            $baseUrl = $data['base_url'] ?? '';
            $apiKey = $data['api_key'] ?? '';
            
            if ($index !== null) {
                // 通过序号删除
                $result = $apiManager->deleteModelByIndex($index);
                sendResponse(['success' => $result]);
            } elseif (!empty($model) && !empty($baseUrl) && !empty($apiKey)) {
                // 通过模型信息删除
                $result = $apiManager->removeModel($baseUrl, $apiKey, $model);
                sendResponse(['success' => $result]);
            } else {
                sendResponse(['error' => '缺少必要参数'], 400);
            }
            break;
        default:
            sendResponse(['error' => '无效的API路径'], 404);
    }
}

// 发送响应
function sendResponse($data, $statusCode = 200) {
    http_response_code($statusCode);
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit();
}
