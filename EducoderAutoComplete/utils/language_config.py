"""
语言配置管理器
"""
class LanguageConfig:
    """语言配置类"""

    # 支持的语言列表
    SUPPORTED_LANGUAGES = [
        ("C", "C语言"),
        ("C++", "C++"),
        ("java", "Java"),
        ("python", "Python"),
        ("javascript", "JavaScript"),
        ("c#", "C#")
    ]

    # 语言特定的文件扩展名
    LANGUAGE_EXTENSIONS = {
        "C": ".c",
        "C++": ".cpp",
        "java": ".java",
        "python": ".py",
        "javascript": ".js",
        "c#": ".cs"
    }

    @classmethod
    def get_language_name(cls, language_code):
        """获取语言显示名称"""
        for code, name in cls.SUPPORTED_LANGUAGES:
            if code == language_code:
                return name
        return language_code.upper()

    @classmethod
    def get_extension(cls, language_code):
        """获取文件扩展名"""
        return cls.LANGUAGE_EXTENSIONS.get(language_code, ".txt")

    @classmethod
    def validate_language(cls, language_code):
        """验证语言代码是否有效"""
        for code, _ in cls.SUPPORTED_LANGUAGES:
            if code == language_code.lower():
                return True
        return False