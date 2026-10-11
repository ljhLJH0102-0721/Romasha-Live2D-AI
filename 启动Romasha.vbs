' Romasha Live2D launcher - starts the app with a hidden console window.
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "d:\BaiduNetdiskDownload\Romasha-Live2D-AI-main\Romasha-Live2D-AI-main"
Set svc = GetObject("winmgmts:\\.\root\cimv2")
Set hits = svc.ExecQuery("SELECT * FROM Win32_Process WHERE Name='python.exe' AND CommandLine LIKE '%Romasha-Live2D-AI-main%main.py%'")
If hits.Count = 0 Then
    sh.Run """d:\BaiduNetdiskDownload\Romasha-Live2D-AI-main\Romasha-Live2D-AI-main\venv\Scripts\python.exe"" main.py", 0, False
End If
