using System.Diagnostics;
using System.Runtime.InteropServices;
using Microsoft.Win32;

namespace PasswordKrakenInstaller;

public class InstallerForm : Form
{
    [DllImport("dwmapi.dll", PreserveSig = true)]
    private static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);
    private const int DWMWA_USE_IMMERSIVE_DARK_MODE = 20;

    private readonly string _defaultPath;
    private TextBox _pathBox = null!;
    private CheckBox _desktopShortcut = null!;
    private CheckBox _startMenuShortcut = null!;
    private Button _installBtn = null!;
    private Button _browseBtn = null!;
    private ProgressBar _progress = null!;
    private Label _statusLabel = null!;
    private bool _isDarkMode;

    private static readonly string[] EmbeddedFiles = {
        "PasswordKraken.exe",
        "kraken.ico"
    };

    public InstallerForm()
    {
        _defaultPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "PasswordKraken");
        _isDarkMode = IsWindowsDarkMode();
        InitializeComponent();
    }

    protected override void OnHandleCreated(EventArgs e)
    {
        base.OnHandleCreated(e);
        int value = _isDarkMode ? 1 : 0;
        DwmSetWindowAttribute(Handle, DWMWA_USE_IMMERSIVE_DARK_MODE, ref value, sizeof(int));
    }

    private static bool IsWindowsDarkMode()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize");
            var value = key?.GetValue("AppsUseLightTheme");
            return value is int i && i == 0;
        }
        catch { return false; }
    }

    private void InitializeComponent()
    {
        Text = "Password Kraken Setup";
        Size = new Size(500, 320);
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;

        var bgColor = _isDarkMode ? Color.FromArgb(30, 30, 30) : SystemColors.Control;
        var fgColor = _isDarkMode ? Color.FromArgb(212, 212, 212) : SystemColors.ControlText;
        var boxBg = _isDarkMode ? Color.FromArgb(45, 45, 45) : SystemColors.Window;

        BackColor = bgColor;
        ForeColor = fgColor;

        // Title
        var title = new Label
        {
            Text = "Password Kraken",
            Font = new Font("Segoe UI", 18, FontStyle.Bold),
            Location = new Point(20, 15),
            AutoSize = true,
            ForeColor = fgColor
        };
        Controls.Add(title);

        var subtitle = new Label
        {
            Text = "An encrypted password manager with PIN protection.",
            Location = new Point(22, 50),
            AutoSize = true,
            ForeColor = fgColor
        };
        Controls.Add(subtitle);

        // Install location
        var pathLabel = new Label
        {
            Text = "Install location:",
            Location = new Point(20, 90),
            AutoSize = true,
            ForeColor = fgColor
        };
        Controls.Add(pathLabel);

        _pathBox = new TextBox
        {
            Text = _defaultPath,
            Location = new Point(20, 110),
            Size = new Size(350, 23),
            BackColor = boxBg,
            ForeColor = fgColor
        };
        Controls.Add(_pathBox);

        _browseBtn = new Button
        {
            Text = "Browse...",
            Location = new Point(380, 109),
            Size = new Size(80, 25),
            FlatStyle = _isDarkMode ? FlatStyle.Flat : FlatStyle.Standard,
            BackColor = _isDarkMode ? Color.FromArgb(60, 60, 60) : SystemColors.Control,
            ForeColor = fgColor
        };
        _browseBtn.Click += BrowseBtn_Click;
        Controls.Add(_browseBtn);

        // Options
        var optionsLabel = new Label
        {
            Text = "Options:",
            Location = new Point(20, 150),
            AutoSize = true,
            ForeColor = fgColor
        };
        Controls.Add(optionsLabel);

        _desktopShortcut = new CheckBox
        {
            Text = "Create desktop shortcut",
            Checked = true,
            Location = new Point(30, 170),
            AutoSize = true,
            ForeColor = fgColor
        };
        Controls.Add(_desktopShortcut);

        _startMenuShortcut = new CheckBox
        {
            Text = "Create Start Menu shortcut",
            Checked = true,
            Location = new Point(30, 195),
            AutoSize = true,
            ForeColor = fgColor
        };
        Controls.Add(_startMenuShortcut);

        // Progress
        _progress = new ProgressBar
        {
            Location = new Point(20, 230),
            Size = new Size(445, 23),
            Visible = false
        };
        Controls.Add(_progress);

        _statusLabel = new Label
        {
            Text = "",
            Location = new Point(20, 230),
            Size = new Size(445, 23),
            ForeColor = fgColor
        };
        Controls.Add(_statusLabel);

        // Install button
        _installBtn = new Button
        {
            Text = "Install",
            Location = new Point(380, 255),
            Size = new Size(85, 30),
            FlatStyle = _isDarkMode ? FlatStyle.Flat : FlatStyle.Standard,
            BackColor = _isDarkMode ? Color.FromArgb(60, 60, 60) : SystemColors.Control,
            ForeColor = fgColor
        };
        _installBtn.Click += InstallBtn_Click;
        Controls.Add(_installBtn);

        var cancelBtn = new Button
        {
            Text = "Cancel",
            Location = new Point(285, 255),
            Size = new Size(85, 30),
            FlatStyle = _isDarkMode ? FlatStyle.Flat : FlatStyle.Standard,
            BackColor = _isDarkMode ? Color.FromArgb(60, 60, 60) : SystemColors.Control,
            ForeColor = fgColor
        };
        cancelBtn.Click += (s, e) => Close();
        Controls.Add(cancelBtn);
    }

    private void BrowseBtn_Click(object? sender, EventArgs e)
    {
        using var dialog = new FolderBrowserDialog
        {
            Description = "Select installation folder",
            InitialDirectory = _pathBox.Text
        };
        if (dialog.ShowDialog() == DialogResult.OK)
        {
            _pathBox.Text = dialog.SelectedPath;
        }
    }

    private async void InstallBtn_Click(object? sender, EventArgs e)
    {
        _installBtn.Enabled = false;
        _browseBtn.Enabled = false;
        _progress.Visible = true;
        _statusLabel.Visible = false;
        _progress.Value = 0;

        try
        {
            string installPath = _pathBox.Text;
            Directory.CreateDirectory(installPath);

            // Extract files
            _progress.Value = 10;
            await Task.Run(() => ExtractFiles(installPath));
            _progress.Value = 50;

            // Register application
            await Task.Run(() => RegisterApplication(installPath));
            _progress.Value = 70;

            string exePath = Path.Combine(installPath, "PasswordKraken.exe");
            string iconPath = Path.Combine(installPath, "kraken.ico");

            // Create shortcuts
            if (_desktopShortcut.Checked)
            {
                string desktopPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Desktop), "Password Kraken.lnk");
                CreateShortcut(desktopPath, exePath, iconPath);
            }
            _progress.Value = 80;

            if (_startMenuShortcut.Checked)
            {
                string startMenuPath = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.StartMenu),
                    "Programs", "Password Kraken"
                );
                Directory.CreateDirectory(startMenuPath);
                CreateShortcut(Path.Combine(startMenuPath, "Password Kraken.lnk"), exePath, iconPath);
            }
            _progress.Value = 90;

            // Create uninstaller info
            CreateUninstallEntry(installPath);
            _progress.Value = 100;

            MessageBox.Show(
                "Password Kraken has been installed successfully!\n\n" +
                $"Location: {installPath}\n\n" +
                "Your passwords are encrypted with AES-256 and protected by your 4-digit PIN.",
                "Installation Complete",
                MessageBoxButtons.OK,
                MessageBoxIcon.Information
            );

            // Offer to launch
            if (MessageBox.Show("Would you like to launch Password Kraken now?", "Launch", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = exePath,
                    UseShellExecute = true
                });
            }

            Close();
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Installation failed: {ex.Message}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            _installBtn.Enabled = true;
            _browseBtn.Enabled = true;
            _progress.Visible = false;
        }
    }

    private void ExtractFiles(string installPath)
    {
        var assembly = typeof(InstallerForm).Assembly;
        foreach (var fileName in EmbeddedFiles)
        {
            using var stream = assembly.GetManifestResourceStream(fileName);
            if (stream == null) continue;

            string destPath = Path.Combine(installPath, fileName);
            using var fileStream = File.Create(destPath);
            stream.CopyTo(fileStream);
        }
    }

    private void RegisterApplication(string installPath)
    {
        string exePath = Path.Combine(installPath, "PasswordKraken.exe");
        string iconPath = Path.Combine(installPath, "kraken.ico");

        // Register capabilities
        using (var key = Registry.CurrentUser.CreateSubKey(@"Software\PasswordKraken\Capabilities"))
        {
            key.SetValue("ApplicationName", "Password Kraken");
            key.SetValue("ApplicationDescription", "An encrypted password manager with PIN protection.");
        }

        // Register with Windows
        using (var key = Registry.CurrentUser.CreateSubKey(@"Software\RegisteredApplications"))
        {
            key.SetValue("PasswordKraken", @"Software\PasswordKraken\Capabilities");
        }

        // Register in Applications
        using (var key = Registry.CurrentUser.CreateSubKey(@"Software\Classes\Applications\PasswordKraken.exe"))
        {
            key.SetValue("FriendlyAppName", "Password Kraken");
        }
        using (var key = Registry.CurrentUser.CreateSubKey(@"Software\Classes\Applications\PasswordKraken.exe\shell\open\command"))
        {
            key.SetValue("", $"\"{exePath}\"");
        }
    }

    private void CreateUninstallEntry(string installPath)
    {
        string iconPath = Path.Combine(installPath, "kraken.ico");

        using var key = Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Uninstall\PasswordKraken");
        key.SetValue("DisplayName", "Password Kraken");
        key.SetValue("DisplayIcon", iconPath);
        key.SetValue("DisplayVersion", "1.0");
        key.SetValue("Publisher", "Kraken Software");
        key.SetValue("InstallLocation", installPath);
        key.SetValue("UninstallString", $"powershell -ExecutionPolicy Bypass -Command \"Remove-Item -Recurse -Force '{installPath}'; Remove-Item 'HKCU:\\Software\\PasswordKraken' -Recurse -ErrorAction SilentlyContinue; Remove-Item 'HKCU:\\Software\\Classes\\Applications\\PasswordKraken.exe' -Recurse -ErrorAction SilentlyContinue; Remove-ItemProperty 'HKCU:\\Software\\RegisteredApplications' -Name 'PasswordKraken' -ErrorAction SilentlyContinue; Remove-Item 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\PasswordKraken' -Recurse\"");
        key.SetValue("NoModify", 1);
        key.SetValue("NoRepair", 1);
    }

    private static void CreateShortcut(string shortcutPath, string targetPath, string iconPath)
    {
        string script = $@"
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcutPath.Replace("'", "''")}')
$Shortcut.TargetPath = '{targetPath.Replace("'", "''")}'
$Shortcut.IconLocation = '{iconPath.Replace("'", "''")}'
$Shortcut.WorkingDirectory = '{Path.GetDirectoryName(targetPath)?.Replace("'", "''")}'
$Shortcut.Save()
";
        var psi = new ProcessStartInfo
        {
            FileName = "powershell",
            Arguments = $"-ExecutionPolicy Bypass -Command \"{script.Replace("\"", "\\\"")}\"",
            UseShellExecute = false,
            CreateNoWindow = true
        };
        using var process = Process.Start(psi);
        process?.WaitForExit();
    }
}
