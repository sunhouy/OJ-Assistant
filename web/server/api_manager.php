<?php

class ApiManager {
    private $apiFile;
    private $encryptionKey;
    
    public function __construct() {
        // API信息存储文件路径
        $this->apiFile = dirname(__FILE__) . '/api_info.json';
        // 加密密钥（建议在生产环境中从环境变量获取）
        $this->encryptionKey = 'educoder_api_encryption_key_2025';
    }
    
    // 加密数据
    private function encrypt($data) {
        $iv = openssl_random_pseudo_bytes(openssl_cipher_iv_length('aes-256-cbc'));
        $encrypted = openssl_encrypt(
            json_encode($data),
            'aes-256-cbc',
            $this->encryptionKey,
            0,
            $iv
        );
        return base64_encode($iv . $encrypted);
    }
    
    // 解密数据
    private function decrypt($encryptedData) {
        $encryptedData = base64_decode($encryptedData);
        $ivLength = openssl_cipher_iv_length('aes-256-cbc');
        $iv = substr($encryptedData, 0, $ivLength);
        $encrypted = substr($encryptedData, $ivLength);
        
        $decrypted = openssl_decrypt(
            $encrypted,
            'aes-256-cbc',
            $this->encryptionKey,
            0,
            $iv
        );
        
        return json_decode($decrypted, true);
    }
    
    // 获取所有API信息
    public function getAllApiInfo() {
        if (!file_exists($this->apiFile)) {
            return ['config' => [], 'preferred_model' => null];
        }
        
        $content = file_get_contents($this->apiFile);
        if (empty($content)) {
            return ['config' => [], 'preferred_model' => null];
        }
        
        $decrypted = $this->decrypt($content);
        
        // 兼容旧版本数据格式
        if (isset($decrypted['config'])) {
            return $decrypted;
        } else {
            // 旧版本只有配置数据，转换为新版本格式
            return ['config' => $decrypted, 'preferred_model' => null];
        }
    }
    
    // 保存API信息
    private function saveApiInfo($apiInfo) {
        $encryptedData = $this->encrypt($apiInfo);
        return file_put_contents($this->apiFile, $encryptedData);
    }
    
    // 添加API信息
    public function addApiInfo($model, $baseUrl, $apiKey) {
        $apiInfo = $this->getAllApiInfo();
        $config = $apiInfo['config'];
        
        // 检查是否已存在相同的base_url和api_key
        $baseUrlKey = md5($baseUrl . $apiKey);
        
        if (isset($config[$baseUrlKey])) {
            // 如果已存在，添加模型到该配置
            if (!in_array($model, $config[$baseUrlKey]['models'])) {
                $config[$baseUrlKey]['models'][] = $model;
            }
        } else {
            // 如果不存在，创建新配置
            $config[$baseUrlKey] = [
                'base_url' => $baseUrl,
                'api_key' => $apiKey,
                'models' => [$model]
            ];
        }
        
        $apiInfo['config'] = $config;
        return $this->saveApiInfo($apiInfo);
    }
    
    // 删除API信息
    public function deleteApiInfo($baseUrl, $apiKey) {
        $apiInfo = $this->getAllApiInfo();
        $config = $apiInfo['config'];
        $baseUrlKey = md5($baseUrl . $apiKey);
        
        if (isset($config[$baseUrlKey])) {
            unset($config[$baseUrlKey]);
            $apiInfo['config'] = $config;
            return $this->saveApiInfo($apiInfo);
        }
        
        return false;
    }
    
    // 从base_url和api_key中移除特定模型
    public function removeModel($baseUrl, $apiKey, $model) {
        $apiInfo = $this->getAllApiInfo();
        $config = $apiInfo['config'];
        $baseUrlKey = md5($baseUrl . $apiKey);
        
        if (isset($config[$baseUrlKey])) {
            $modelIndex = array_search($model, $config[$baseUrlKey]['models']);
            if ($modelIndex !== false) {
                array_splice($config[$baseUrlKey]['models'], $modelIndex, 1);
                
                // 如果该配置下没有模型了，删除整个配置
                if (empty($config[$baseUrlKey]['models'])) {
                    unset($config[$baseUrlKey]);
                }
                
                $apiInfo['config'] = $config;
                
                // 如果移除的是首选模型，清空首选模型设置
                if ($apiInfo['preferred_model'] === $model) {
                    $apiInfo['preferred_model'] = null;
                }
                
                return $this->saveApiInfo($apiInfo);
            }
        }
        
        return false;
    }
    
    // 获取所有可用模型
    public function getAllModels() {
        $apiInfo = $this->getAllApiInfo();
        $config = $apiInfo['config'];
        $models = [];
        
        foreach ($config as $configItem) {
            $models = array_merge($models, $configItem['models']);
        }
        
        // 去重并排序
        $models = array_unique($models);
        sort($models);
        
        return $models;
    }
    
    // 获取所有带序号的模型和配置信息
    public function getAllModelsWithDetails() {
        $apiInfo = $this->getAllApiInfo();
        $config = $apiInfo['config'];
        $modelDetails = [];
        $index = 0;
        
        foreach ($config as $configItem) {
            foreach ($configItem['models'] as $model) {
                $modelDetails[] = [
                    'index' => $index++,
                    'model' => $model,
                    'base_url' => $configItem['base_url'],
                    'api_key' => $configItem['api_key']
                ];
            }
        }
        
        return $modelDetails;
    }
    
    // 通过序号删除模型
    public function deleteModelByIndex($index) {
        $modelDetails = $this->getAllModelsWithDetails();
        
        if (isset($modelDetails[$index])) {
            $modelInfo = $modelDetails[$index];
            return $this->removeModel($modelInfo['base_url'], $modelInfo['api_key'], $modelInfo['model']);
        }
        
        return false;
    }
    
    // 获取特定模型的配置
    public function getModelConfig($model) {
        $apiInfo = $this->getAllApiInfo();
        $config = $apiInfo['config'];
        
        foreach ($config as $configItem) {
            if (in_array($model, $configItem['models'])) {
                return [
                    'base_url' => $configItem['base_url'],
                    'api_key' => $configItem['api_key']
                ];
            }
        }
        
        return null;
    }
    
    // 设置首选模型
    public function setPreferredModel($model) {
        $apiInfo = $this->getAllApiInfo();
        $allModels = $this->getAllModels();
        
        // 检查模型是否存在
        if (in_array($model, $allModels)) {
            $apiInfo['preferred_model'] = $model;
            return $this->saveApiInfo($apiInfo);
        }
        
        return false;
    }
    
    // 获取首选模型
    public function getPreferredModel() {
        $apiInfo = $this->getAllApiInfo();
        return $apiInfo['preferred_model'];
    }
    
    // 获取首选模型的配置
    public function getPreferredModelConfig() {
        $preferredModel = $this->getPreferredModel();
        if ($preferredModel) {
            return $this->getModelConfig($preferredModel);
        }
        return null;
    }
}
