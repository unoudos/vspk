@echo off
powershell -WindowStyle Hidden -Command "Start-Process php -ArgumentList '%~1' -WindowStyle Hidden"