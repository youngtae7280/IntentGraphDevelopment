IntentGraph Windows Portable Bundle

This directory is assembled locally from repository sources. It does not download,
sign, publish, or contact a provider. Python 3.11 or newer is required. The C#
workflow also requires a supported locally installed .NET SDK.

Install without changing PATH:
  powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -InstallRoot C:\Tools\IntentGraph -NoPathUpdate

Run from that explicit location:
  C:\Tools\IntentGraph\igd.cmd doctor

Uninstall without changing PATH:
  powershell -NoProfile -ExecutionPolicy Bypass -File C:\Tools\IntentGraph\uninstall.ps1 -InstallRoot C:\Tools\IntentGraph -NoPathUpdate
