// 支付相关逻辑

// 生成易支付签名
function generateEPaySign(params, key) {
    // 按照参数名ASCII码从小到大排序
    const sortedKeys = Object.keys(params).sort();
    
    // 拼接参数字符串
    let signStr = '';
    for (const k of sortedKeys) {
        if (k !== 'sign' && k !== 'sign_type' && params[k] !== '' && params[k] !== null) {
            signStr += `${k}=${params[k]}&`;
        }
    }
    
    // 添加商户密钥
    signStr += `key=${key}`;
    
    // 计算MD5签名
    return md5(signStr).toUpperCase();
}

// 简单的MD5函数（生产环境应该使用更完整的实现）
function md5(input) {
    // 这是一个简化的MD5实现，生产环境应该使用完整的MD5库
    // 例如：https://github.com/blueimp/JavaScript-MD5
    return 'md5_' + input; // 简化实现，实际需要完整的MD5算法
}

// 模拟后端创建订单并返回支付参数
// 注意：实际应用中，这个函数应该在后端实现
function simulateCreateOrder(username, planType, planName, price, paymentType) {
    // 生成订单号
    const outTradeNo = 'EDU' + Date.now() + Math.floor(Math.random() * 1000);
    
    // 商品名称
    const productName = `Educoder助手${planName}`;
    
    // 商户ID和密钥（实际应该从后端获取，不能在前端暴露）
    const pid = '3212';
    const key = '4pu2aNc8AePEGYH2PkPmJ32lxCIRcV4J';
    
    // 构建参数
    const params = {
        pid: pid,
        type: paymentType,
        out_trade_no: outTradeNo,
        notify_url: 'https://yhsun.cn/server/notify.php',
        return_url: 'https://yhsun.cn/server/return.php',
        name: productName,
        money: price.toFixed(2),
        clientip: '127.0.0.1',
        device: 'pc',
        param: JSON.stringify({
            username: username,
            plan_type: planType,
            plan_name: planName
        }),
        sign_type: 'MD5'
    };
    
    // 生成签名
    const sign = generateEPaySign(params, key);
    params.sign = sign;
    
    return {
        code: 200,
        message: '订单创建成功',
        data: params
    };
}