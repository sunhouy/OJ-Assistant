import uiautomation as auto


def type_with_uiautomation(text):
    """
    使用uiautomation库输入中文
    这个库可以更好地处理Windows UI自动化
    """
    # 获取当前焦点控件
    control = auto.GetFocusedControl()

    # 发送文本（支持Unicode）
    if control:
        control.SendKeys(text, interval=0.05)
    else:
        # 如果没有找到控件，尝试发送到桌面
        auto.SendKeys(text, interval=0.05)


# 使用示例
type_with_uiautomation("sdfgdsfd")
