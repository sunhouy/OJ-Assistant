import PyInstaller.__main__

def main():
    args = [
        'C:\\Users\\sunhouyun\\Desktop\\Educoder\\EducoderAssistant\\main.py',  # 主程序路径
        '--onefile',
        '--name=Educoder助手',
        '--icon=app.png',
        '--windowed',
        '--clean',
    ]

    print(f"PyInstaller {' '.join(args)}")
    PyInstaller.__main__.run(args)

if __name__ == '__main__':
    main()