#!/usr/bin/env python3
"""Generate a UEFI/GPT Autounattend.xml without printing the password."""
from __future__ import annotations

import argparse
import base64
import os
import secrets
from pathlib import Path
from xml.sax.saxutils import escape


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    password = os.environ.get("BOOTSTRAP_PASSWORD")
    if not password:
        password = secrets.token_urlsafe(24) + "Aa1!"

    # This runs on the first automatic logon. It enables RDP, disables NLA for
    # the blank-password test account, and then clears the bootstrap password.
    ps = r"""$ErrorActionPreference = 'SilentlyContinue'
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server' -Name fDenyTSConnections -Type DWord -Value 0
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' -Name UserAuthentication -Type DWord -Value 0
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' -Name LimitBlankPasswordUse -Type DWord -Value 0
Enable-NetFirewallRule -DisplayGroup 'Remote Desktop'
& "$env:SystemRoot\System32\net.exe" user RDP ""
Set-Content -LiteralPath 'C:\KaggleImageReady.txt' -Value 'Windows installation completed; RDP is enabled'
"""
    encoded = base64.b64encode(ps.encode("utf-16le")).decode("ascii")
    first_logon = f"powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded}"

    xml = f'''<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
  <settings pass="windowsPE">
    <component name="Microsoft-Windows-International-Core-WinPE" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
      <SetupUILanguage><UILanguage>en-US</UILanguage></SetupUILanguage>
      <InputLocale>en-US</InputLocale><SystemLocale>en-US</SystemLocale><UILanguage>en-US</UILanguage><UserLocale>en-US</UserLocale>
    </component>
    <component name="Microsoft-Windows-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
      <DiskConfiguration>
        <Disk wcm:action="add"><DiskID>0</DiskID><WillWipeDisk>true</WillWipeDisk>
          <CreatePartitions>
            <CreatePartition wcm:action="add"><Order>1</Order><Type>EFI</Type><Size>100</Size></CreatePartition>
            <CreatePartition wcm:action="add"><Order>2</Order><Type>MSR</Type><Size>16</Size></CreatePartition>
            <CreatePartition wcm:action="add"><Order>3</Order><Type>Primary</Type><Extend>true</Extend></CreatePartition>
          </CreatePartitions>
          <ModifyPartitions>
            <ModifyPartition wcm:action="add"><Order>1</Order><PartitionID>1</PartitionID><Format>FAT32</Format><Label>System</Label></ModifyPartition>
            <ModifyPartition wcm:action="add"><Order>3</Order><PartitionID>3</PartitionID><Format>NTFS</Format><Label>Windows</Label><Letter>W</Letter></ModifyPartition>
          </ModifyPartitions>
        </Disk>
      </DiskConfiguration>
      <ImageInstall><OSImage><InstallTo><DiskID>0</DiskID><PartitionID>3</PartitionID></InstallTo><InstallToAvailablePartition>false</InstallToAvailablePartition></OSImage></ImageInstall>
      <UserData><AcceptEula>true</AcceptEula><FullName>RDP</FullName><Organization>Kaggle</Organization></UserData>
    </component>
  </settings>
  <settings pass="specialize">
    <component name="Microsoft-Windows-TerminalServices-LocalSessionManager" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS"><fDenyTSConnections>false</fDenyTSConnections></component>
  </settings>
  <settings pass="oobeSystem">
    <component name="Microsoft-Windows-International-Core" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS"><InputLocale>en-US</InputLocale><SystemLocale>en-US</SystemLocale><UILanguage>en-US</UILanguage><UserLocale>en-US</UserLocale></component>
    <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
      <UserAccounts><LocalAccounts><LocalAccount wcm:action="add"><Name>RDP</Name><DisplayName>RDP Test User</DisplayName><Group>Administrators</Group><Password><Value>{escape(password)}</Value><PlainText>true</PlainText></Password></LocalAccount></LocalAccounts></UserAccounts>
      <AutoLogon><Enabled>true</Enabled><Username>RDP</Username><LogonCount>5</LogonCount><Password><Value>{escape(password)}</Value><PlainText>true</PlainText></Password></AutoLogon>
      <OOBE><HideEULAPage>true</HideEULAPage><HideLocalAccountScreen>true</HideLocalAccountScreen><HideOEMRegistrationScreen>true</HideOEMRegistrationScreen><HideOnlineAccountScreens>true</HideOnlineAccountScreens><HideWirelessSetupInOOBE>true</HideWirelessSetupInOOBE><ProtectYourPC>3</ProtectYourPC></OOBE>
      <FirstLogonCommands><SynchronousCommand wcm:action="add" wcm:keyValue="1"><CommandLine>{escape(first_logon)}</CommandLine><Description>Enable RDP and mark the image ready</Description><Order>1</Order></SynchronousCommand></FirstLogonCommands>
    </component>
  </settings>
</unattend>
'''
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(xml, encoding="utf-8")


if __name__ == "__main__":
    main()
