Dim sh
Set sh = CreateObject("WScript.Shell")
sh.Run "pythonw """ & sh.CurrentDirectory & "\iss_tracker.py""", 0, False
