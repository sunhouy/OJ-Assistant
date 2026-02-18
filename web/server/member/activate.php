<?php
/**
 * Educoder助手会员开通接口
 * 接收用户名和套餐类型，使用管理员账号生成授权码并开通会员
 * 将此文件保存为 activate.php 并放置在与HTML文件相同的目录下
 */

// 设置响应头
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// 如果是OPTIONS请求，直接返回
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

// 只接受POST请求
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode([
        'success' => false,
        'message' => '仅支持POST请求'
    ]);
    exit;
}

// 获取请求数据
$input = json_decode(file_get_contents('php://input'), true);
$username = $input['username'] ?? '';
$package = $input['package'] ?? 'month';

// 验证输入
if (empty($username)) {
    echo json_encode([
        'success' => false,
        'message' => '用户名不能为空'
    ]);
    exit;
}

// 验证用户名格式（3-20位字母数字）
if (!preg_match('/^[a-zA-Z0-9_]{3,20}$/', $username)) {
    echo json_encode([
        'success' => false,
        'message' => '用户名格式不正确，应为3-20位字母、数字或下划线'
    ]);
    exit;
}

// 根据套餐设置有效期和价格
$package_config = [
    'month' => [
        'name' => '月卡会员',
        'days' => 30,
        'price' => 29.9
    ],
    'season' => [
        'name' => '季卡会员',
        'days' => 90,
        'price' => 79.9
    ],
    'year' => [
        'name' => '年卡会员',
        'days' => 365,
        'price' => 299.9
    ]
];

if (!isset($package_config[$package])) {
    $package = 'month'; // 默认月卡
}

$package_info = $package_config[$package];

// 模拟成功响应（实际使用时请取消下面的注释，并修改为真实的API调用）
// 这里提供两种方案：实际API调用方案和模拟方案

// 方案1：模拟成功响应（用于测试，无需真实API）
if (false) { // 将此条件改为false以启用真实API调用
    // 模拟处理时间
    sleep(1);
    
    // 生成模拟的授权码
    $auth_code = 'EDU' . date('Ymd') . strtoupper(substr(md5(uniqid()), 0, 6));
    
    // 计算到期日期
    $expire_date = date('Y年m月d日', strtotime('+' . $package_info['days'] . ' days'));
    
    // 记录到日志文件（可选）
    $log_entry = date('Y-m-d H:i:s') . " | 用户: $username | 套餐: {$package_info['name']} | 授权码: $auth_code | 到期: $expire_date\n";
    @file_put_contents('activation_log.txt', $log_entry, FILE_APPEND);
    
    // 返回成功结果
    echo json_encode([
        'success' => true,
        'message' => '会员开通成功',
        'username' => $username,
        'package' => $package_info['name'],
        'auth_code' => $auth_code,
        'expire_date' => $expire_date,
        'price' => $package_info['price']
    ]);
    exit;
}

// 方案2：真实API调用（根据你的实际API调整）
// API基础URL
$api_base_url = 'http://yhsun.cn/server/index.php';

// 管理员账号信息（请在生产环境中使用安全的方式存储这些信息）
$admin_username = 'admin';
$admin_password = '127127sun';

// 生成一个唯一的授权码
function generate_auth_code() {
    $prefix = 'EDU';
    $date = date('Ymd');
    $random = strtoupper(substr(md5(uniqid(mt_rand(), true)), 0, 8));
    return $prefix . $date . $random;
}

// 调用API函数
function call_api($url, $data) {
    $ch = curl_init();
    
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json'
    ]);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    
    curl_close($ch);
    
    if ($http_code !== 200) {
        return [
            'code' => $http_code,
            'message' => 'API请求失败'
        ];
    }
    
    return json_decode($response, true);
}

try {
    // 步骤1：管理员登录
    $login_url = $api_base_url . '?action=admin_login';
    $login_data = [
        'username' => $admin_username,
        'password' => $admin_password
    ];
    
    $login_result = call_api($login_url, $login_data);
    
    if ($login_result['code'] !== 200) {
        throw new Exception('管理员登录失败: ' . ($login_result['message'] ?? '未知错误'));
    }
    
    // 步骤2：生成授权码
    $auth_code = generate_auth_code();
    
    // 计算到期日期
    $expire_date = date('Ymd', strtotime('+' . $package_info['days'] . ' days'));
    
    // 步骤3：添加授权码（使用管理员权限）
    $add_code_url = $api_base_url . '?action=add_auth_code';
    $add_code_data = [
        'username' => $admin_username,
        'password' => $admin_password,
        'code' => $auth_code,
        'expire_date' => $expire_date
    ];
    
    $add_code_result = call_api($add_code_url, $add_code_data);
    
    if ($add_code_result['code'] !== 200) {
        throw new Exception('生成授权码失败: ' . ($add_code_result['message'] ?? '未知错误'));
    }
    
    // 步骤4：使用授权码为用户开通会员
    $activate_url = $api_base_url . '?action=activate_member';
    $activate_data = [
        'username' => $username,
        'code' => $auth_code
    ];
    
    $activate_result = call_api($activate_url, $activate_data);
    
    if ($activate_result['code'] !== 200) {
        throw new Exception('开通会员失败: ' . ($activate_result['message'] ?? '未知错误'));
    }
    
    // 格式化到期日期显示
    $expire_display = date('Y年m月d日', strtotime('+' . $package_info['days'] . ' days'));
    
    // 记录日志
    $log_entry = date('Y-m-d H:i:s') . " | 用户: $username | 套餐: {$package_info['name']} | 授权码: $auth_code | 到期: $expire_display\n";
    @file_put_contents('activation_log.txt', $log_entry, FILE_APPEND);
    
    // 返回成功结果
    echo json_encode([
        'success' => true,
        'message' => '会员开通成功',
        'username' => $username,
        'package' => $package_info['name'],
        'auth_code' => $auth_code,
        'expire_date' => $expire_display,
        'price' => $package_info['price']
    ]);
    
} catch (Exception $e) {
    // 记录错误日志
    $error_log = date('Y-m-d H:i:s') . " | 用户: $username | 套餐: {$package_info['name']} | 错误: " . $e->getMessage() . "\n";
    @file_put_contents('activation_errors.txt', $error_log, FILE_APPEND);
    
    // 返回错误信息
    echo json_encode([
        'success' => false,
        'message' => $e->getMessage(),
        'suggestion' => '请检查用户名是否正确，或联系客服处理'
    ]);
}
?>