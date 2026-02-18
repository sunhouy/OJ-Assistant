<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// 处理OPTIONS请求
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// 加载配置和核心文件
try {
    $config = require 'config.php';
    require 'db.php';
    require 'user.php';
    require 'api_manager.php';
    
    // 初始化数据库连接和用户管理对象
    $db = new Database($config['db']);
    $user = new User($db, $config);
    $apiManager = new ApiManager();
} catch (Exception $e) {
    echo json_encode([
        'code' => 500,
        'message' => '服务器内部错误',
        'error' => $e->getMessage()
    ]);
    exit;
}

// 获取请求方法和参数
$method = $_SERVER['REQUEST_METHOD'];
$request = $_GET['action'] ?? '';

// 处理不同的API请求
try {
    switch ($request) {
        case 'login':
            // 用户登录
            if ($method !== 'POST') {
                throw new Exception('请求方法错误');
            }
            
            $data = json_decode(file_get_contents('php://input'), true);
            $username = $data['username'] ?? '';
            $password = $data['password'] ?? '';
            $machineCode = $data['machine_code'] ?? '';
            
            if (empty($username) || empty($password) || empty($machineCode)) {
                throw new Exception('缺少必要参数');
            }
            
            $result = $user->login($username, $password, $machineCode);
            echo json_encode($result, JSON_UNESCAPED_UNICODE);
            break;
            
        case 'register':
            // 用户注册
            if ($method !== 'POST') {
                throw new Exception('请求方法错误');
            }
            
            $data = json_decode(file_get_contents('php://input'), true);
            $username = $data['username'] ?? '';
            $password = $data['password'] ?? '';
            $machineCode = $data['machine_code'] ?? '';
            $inviteCode = $data['invite_code'] ?? null;
            
            if (empty($username) || empty($password) || empty($machineCode)) {
                throw new Exception('缺少必要参数');
            }
            
            $result = $user->register($username, $password, $machineCode, $inviteCode);
            echo json_encode($result, JSON_UNESCAPED_UNICODE);
            break;
            
        case 'check_member':
            // 查询会员状态
            if ($method !== 'POST') {
                throw new Exception('请求方法错误');
            }
            
            $data = json_decode(file_get_contents('php://input'), true);
            $username = $data['username'] ?? '';
            $machineCode = $data['machine_code'] ?? '';
            
            if (empty($username) || empty($machineCode)) {
                throw new Exception('缺少必要参数');
            }
            
            $result = $user->checkMemberStatus($username, $machineCode);
            echo json_encode($result, JSON_UNESCAPED_UNICODE);
            break;
            
        case 'admin_login':
            // 管理员登录
            if ($method !== 'POST') {
                throw new Exception('请求方法错误');
            }
            
            $data = json_decode(file_get_contents('php://input'), true);
            $username = $data['username'] ?? '';
            $password = $data['password'] ?? '';
            
            if (empty($username) || empty($password)) {
                throw new Exception('缺少必要参数');
            }
            
            $result = $user->adminLogin($username, $password);
            echo json_encode($result, JSON_UNESCAPED_UNICODE);
            break;
            
        case 'admin_get_users':
            // 管理员查询所有用户
            if ($method !== 'POST') {
                throw new Exception('请求方法错误');
            }
            
            $data = json_decode(file_get_contents('php://input'), true);
            $username = $data['username'] ?? '';
            $password = $data['password'] ?? '';
            
            // 验证管理员身份
            if ($username != $config['admin']['username'] || $password != $config['admin']['password']) {
                echo json_encode([
                    'code' => 401,
                    'message' => '管理员身份验证失败'
                ]);
                break;
            }
            
            $result = $user->getAllUsers();
            echo json_encode($result, JSON_UNESCAPED_UNICODE);
            break;
            
        case 'add_auth_code':
            // 添加授权码（管理员功能）
            if ($method !== 'POST') {
                throw new Exception('请求方法错误');
            }
            
            $data = json_decode(file_get_contents('php://input'), true);
            $adminUsername = $data['username'] ?? '';
            $adminPassword = $data['password'] ?? '';
            $code = $data['code'] ?? '';
            $memberDays = $data['member_days'] ?? '';
            
            if (empty($adminUsername) || empty($adminPassword) || empty($code) || empty($memberDays)) {
                throw new Exception('缺少必要参数');
            }
            
            $result = $user->addAuthorizationCode($adminUsername, $adminPassword, $code, $memberDays);
            echo json_encode($result, JSON_UNESCAPED_UNICODE);
            break;
            
        case 'activate_member':
            // 开通会员
            if ($method !== 'POST') {
                throw new Exception('请求方法错误');
            }
            
            $data = json_decode(file_get_contents('php://input'), true);
            $username = $data['username'] ?? '';
            $code = $data['code'] ?? '';
            
            if (empty($username) || empty($code)) {
                throw new Exception('缺少必要参数');
            }
            
            $result = $user->activateMember($username, $code);
            echo json_encode($result, JSON_UNESCAPED_UNICODE);
            break;
            
        case 'check_update':
            // 检查版本更新
            if ($method !== 'POST') {
                throw new Exception('请求方法错误');
            }
            
            $data = json_decode(file_get_contents('php://input'), true);
            $currentVersion = $data['current_version'] ?? '';
            
            if (empty($currentVersion)) {
                throw new Exception('缺少必要参数');
            }
            
            $result = $user->checkUpdate($currentVersion);
            echo json_encode($result, JSON_UNESCAPED_UNICODE);
            break;
            
        case 'admin_submit_update':
            // 管理员提交更新
            if ($method !== 'POST') {
                throw new Exception('请求方法错误');
            }
            
            $data = json_decode(file_get_contents('php://input'), true);
            $adminUsername = $data['username'] ?? '';
            $adminPassword = $data['password'] ?? '';
            $latestVersion = $data['latest_version'] ?? '';
            $updateContent = $data['update_content'] ?? '';
            $downloadUrl = $data['download_url'] ?? '';
            $minVersion = $data['min_version'] ?? '';
            
            if (empty($adminUsername) || empty($adminPassword) || empty($latestVersion) || empty($updateContent) || empty($downloadUrl) || empty($minVersion)) {
                throw new Exception('缺少必要参数');
            }
            
            $result = $user->submitUpdate($adminUsername, $adminPassword, $latestVersion, $updateContent, $downloadUrl, $minVersion);
            echo json_encode($result, JSON_UNESCAPED_UNICODE);
            break;
            
        case 'admin_add_api':
            // 管理员添加API信息
            if ($method !== 'POST') {
                throw new Exception('请求方法错误');
            }
            
            $data = json_decode(file_get_contents('php://input'), true);
            $adminUsername = $data['username'] ?? '';
            $adminPassword = $data['password'] ?? '';
            $model = $data['model'] ?? '';
            $baseUrl = $data['base_url'] ?? '';
            $apiKey = $data['api_key'] ?? '';
            
            // 验证管理员身份
            if ($adminUsername != $config['admin']['username'] || $adminPassword != $config['admin']['password']) {
                echo json_encode([
                    'code' => 401,
                    'message' => '管理员身份验证失败'
                ]);
                break;
            }
            
            if (empty($model) || empty($baseUrl) || empty($apiKey)) {
                throw new Exception('缺少必要参数');
            }
            
            $result = $apiManager->addApiInfo($model, $baseUrl, $apiKey);
            if ($result !== false) {
                echo json_encode([
                    'code' => 200,
                    'message' => 'API信息添加成功'
                ]);
            } else {
                echo json_encode([
                    'code' => 500,
                    'message' => 'API信息添加失败'
                ]);
            }
            break;
            
        case 'admin_delete_api':
            // 管理员删除API信息
            if ($method !== 'POST') {
                throw new Exception('请求方法错误');
            }
            
            $data = json_decode(file_get_contents('php://input'), true);
            $adminUsername = $data['username'] ?? '';
            $adminPassword = $data['password'] ?? '';
            $baseUrl = $data['base_url'] ?? '';
            $apiKey = $data['api_key'] ?? '';
            
            // 验证管理员身份
            if ($adminUsername != $config['admin']['username'] || $adminPassword != $config['admin']['password']) {
                echo json_encode([
                    'code' => 401,
                    'message' => '管理员身份验证失败'
                ]);
                break;
            }
            
            if (empty($baseUrl) || empty($apiKey)) {
                throw new Exception('缺少必要参数');
            }
            
            $result = $apiManager->deleteApiInfo($baseUrl, $apiKey);
            if ($result !== false) {
                echo json_encode([
                    'code' => 200,
                    'message' => 'API信息删除成功'
                ]);
            } else {
                echo json_encode([
                    'code' => 500,
                    'message' => 'API信息删除失败'
                ]);
            }
            break;
            
        case 'admin_remove_model':
            // 管理员移除模型
            if ($method !== 'POST') {
                throw new Exception('请求方法错误');
            }
            
            $data = json_decode(file_get_contents('php://input'), true);
            $adminUsername = $data['username'] ?? '';
            $adminPassword = $data['password'] ?? '';
            $baseUrl = $data['base_url'] ?? '';
            $apiKey = $data['api_key'] ?? '';
            $model = $data['model'] ?? '';
            
            // 验证管理员身份
            if ($adminUsername != $config['admin']['username'] || $adminPassword != $config['admin']['password']) {
                echo json_encode([
                    'code' => 401,
                    'message' => '管理员身份验证失败'
                ]);
                break;
            }
            
            if (empty($baseUrl) || empty($apiKey) || empty($model)) {
                throw new Exception('缺少必要参数');
            }
            
            $result = $apiManager->removeModel($baseUrl, $apiKey, $model);
            if ($result !== false) {
                echo json_encode([
                    'code' => 200,
                    'message' => '模型移除成功'
                ]);
            } else {
                echo json_encode([
                    'code' => 500,
                    'message' => '模型移除失败'
                ]);
            }
            break;
            
        case 'admin_get_all_api':
            // 管理员获取所有API信息
            if ($method !== 'POST') {
                throw new Exception('请求方法错误');
            }
            
            $data = json_decode(file_get_contents('php://input'), true);
            $adminUsername = $data['username'] ?? '';
            $adminPassword = $data['password'] ?? '';
            
            // 验证管理员身份
            if ($adminUsername != $config['admin']['username'] || $adminPassword != $config['admin']['password']) {
                echo json_encode([
                    'code' => 401,
                    'message' => '管理员身份验证失败'
                ]);
                break;
            }
            
            $apiInfo = $apiManager->getAllApiInfo();
            echo json_encode([
                'code' => 200,
                'message' => '获取API信息成功',
                'data' => $apiInfo
            ]);
            break;
            
        case 'get_available_models':
            // 用户获取可用模型
            if ($method !== 'POST') {
                throw new Exception('请求方法错误');
            }
            
            $data = json_decode(file_get_contents('php://input'), true);
            $username = $data['username'] ?? '';
            $password = $data['password'] ?? '';
            $machineCode = $data['machine_code'] ?? '';
            
            // 验证用户身份
            $loginResult = $user->login($username, $password, $machineCode);
            if ($loginResult['code'] != 200) {
                echo json_encode([
                    'code' => 401,
                    'message' => '用户身份验证失败'
                ]);
                break;
            }
            
            $models = $apiManager->getAllModels();
            echo json_encode([
                'code' => 200,
                'message' => '获取可用模型成功',
                'data' => [
                    'models' => $models
                ]
            ]);
            break;
            
        case 'get_model_config':
            // 获取特定模型的配置
            if ($method !== 'POST') {
                throw new Exception('请求方法错误');
            }
            
            $data = json_decode(file_get_contents('php://input'), true);
            $username = $data['username'] ?? '';
            $password = $data['password'] ?? '';
            $machineCode = $data['machine_code'] ?? '';
            $model = $data['model'] ?? '';
            
            // 验证用户身份
            $loginResult = $user->login($username, $password, $machineCode);
            if ($loginResult['code'] != 200) {
                echo json_encode([
                    'code' => 401,
                    'message' => '用户身份验证失败'
                ]);
                break;
            }
            
            if (empty($model)) {
                throw new Exception('缺少必要参数');
            }
            
            $config = $apiManager->getModelConfig($model);
            if ($config) {
                echo json_encode([
                    'code' => 200,
                    'message' => '获取模型配置成功',
                    'data' => $config
                ]);
            } else {
                echo json_encode([
                    'code' => 404,
                    'message' => '模型配置不存在'
                ]);
            }
            break;
            
        case 'upload_screenshot':
            // 上传截图（已修改：支持所有文件类型，每个用户单独文件夹）
            if ($method !== 'POST') {
                throw new Exception('请求方法错误');
            }
            
            // 验证请求是否包含文件
            if (!isset($_FILES['screenshot'])) {
                throw new Exception('缺少文件');
            }
            
            $file = $_FILES['screenshot'];
            $username = $_POST['username'] ?? '';
            $machine_code = $_POST['machine_code'] ?? '';
            
            if (empty($username) || empty($machine_code)) {
                throw new Exception('缺少必要参数');
            }
            
            // 验证文件大小 (限制为10MB)
            $maxSize = 10 * 1024 * 1024;
            if ($file['size'] > $maxSize) {
                throw new Exception('文件大小超过10MB限制');
            }
            
            // 安全检查：防止恶意文件名
            $originalFileName = basename($file['name']);
            $safeFileName = preg_replace('/[^a-zA-Z0-9._-]/', '_', $originalFileName);
            
            // 获取文件扩展名
            $fileExtension = strtolower(pathinfo($safeFileName, PATHINFO_EXTENSION));
            
            // 为每个用户创建单独的文件夹
            $userFolderName = 'user_' . $username; // 使用md5避免特殊字符问题
            $baseDir = '/www/wwwroot/yhsun/server/screenshots/';
            $userFolderPath = $baseDir . $userFolderName;
            
            // 确保用户目录存在
            if (!is_dir($userFolderPath)) {
                if (!mkdir($userFolderPath, 0755, true)) {
                    throw new Exception('无法创建用户目录');
                }
            }
            
            // 生成唯一文件名
            $fileName = uniqid($username . '_' . date('Ymd_')) . '.' . $fileExtension;
            $savePath = $userFolderPath . '/' . $fileName;
            $absolutePath = realpath($userFolderPath) . '/' . $fileName;
            
            // 移动上传的文件
            if (move_uploaded_file($file['tmp_name'], $absolutePath)) {
                // 返回相对路径和URL
                $relativePath = '../../screenshots/' . $userFolderName . '/' . $fileName;
                $fileUrl = 'http://yhsun.cn/server/screenshots/' . $userFolderName . '/' . $fileName;
                
                echo json_encode([
                    'code' => 200,
                    'message' => '文件上传成功',
                    'data' => [
                        'file_name' => $fileName,
                        'original_name' => $originalFileName,
                        'file_path' => $relativePath,
                        'file_url' => $fileUrl,
                        'user_folder' => $userFolderName,
                        'file_size' => $file['size'],
                        'file_type' => $file['type']
                    ]
                ]);
            } else {
                throw new Exception('文件保存失败');
            }
            break;
            
        default:
            throw new Exception('无效的API请求');
    }
} catch (Exception $e) {
    echo json_encode([
        'code' => 400,
        'message' => $e->getMessage()
    ]);
}

// 关闭数据库连接
$db->close();