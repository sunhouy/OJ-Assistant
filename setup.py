import PyInstaller.__main__

def main():
    args = [
        r'C:\Users\sunhouyun\Desktop\Educoder\OJAssistant\main.py',
        '--onefile',
        '--name=OJ助手',
        '--icon=app.png',
        '--windowed',
        '--clean',
    ]

    print(f"PyInstaller {' '.join(args)}")
    PyInstaller.__main__.run(args)

if __name__ == '__main__':
    main()