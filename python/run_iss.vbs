Dim sh
Set sh = CreateObject("WScript.Shell")
sh.Run "bun """ & sh.CurrentDirectory & "\iss_tracker.js""", 0, False
