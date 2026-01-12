# Password Kraken

An encrypted password manager with 4-digit PIN protection. Follows Windows dark/light theme automatically.

## Features

- **AES-256 Encryption** - Passwords encrypted using Fernet (AES-128-CBC + HMAC)
- **PBKDF2 Key Derivation** - 480,000 iterations to protect against brute force
- **4-Digit PIN** - Simple to remember, secures your vault
- **Windows Theme Support** - Automatically matches dark/light mode
- **Search** - Quickly find entries by name or username
- **Import** - Import from Chrome, Firefox, 1Password, LastPass (CSV export)
- **Export** - Backup your vault to JSON
- **Clipboard Auto-Clear** - Passwords cleared from clipboard after 30 seconds

## Installation

Run `PasswordKraken_Setup.exe` from the `release_installer` folder.

Or run directly with Python:
```
pip install cryptography
python password_kraken_gui.py
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+C | Copy password to clipboard |
| Ctrl+N | Add new entry |
| Ctrl+F | Focus search box |
| Enter | Edit selected entry |
| Delete | Delete selected entry |

## Importing Passwords

### From Chrome:
1. Go to `chrome://password-manager/settings`
2. Click "Download file" under "Export passwords"
3. In Password Kraken, click **Import** and select the CSV

### From Firefox:
1. Go to `about:logins`
2. Click the menu (three dots) and select "Export Logins"
3. In Password Kraken, click **Import** and select the CSV

### From Other Managers:
Export to CSV with columns: `name`, `url`, `username`, `password`, `notes`

## Files

- `passwords.kraken` - Your encrypted password vault
- `passwords.kraken.salt` - Random salt for key derivation

**Keep these files safe. Without them, your passwords cannot be recovered.**

## Security Notes

- A 4-digit PIN has only 10,000 combinations. The high PBKDF2 iteration count slows brute-force attacks significantly, but for maximum security consider a longer passphrase.
- The vault file is encrypted at rest. Passwords are only decrypted in memory when unlocked.
- Export files are **unencrypted** - delete them after use.

## Building from Source

### Requirements:
- Python 3.10+
- cryptography library
- PyInstaller (for exe)
- .NET 8 SDK (for installer)

### Build:
```powershell
# Create exe
pip install pyinstaller cryptography
pyinstaller --onefile --windowed --icon=kraken.ico --name=PasswordKraken password_kraken_gui.py

# Create installer
cd src\Installer
dotnet publish -c Release -o ..\..\release_installer
```

## License

MIT
