// Offline, per-user installer. Payload files are checked against a SHA-256 manifest.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

internal sealed class PayloadStream : Stream
{
    private readonly Stream source;
    private readonly long offset, length;
    public PayloadStream(Stream source, long offset, long length) { this.source = source; this.offset = offset; this.length = length; Position = 0; }
    public override bool CanRead { get { return true; } }
    public override bool CanSeek { get { return true; } }
    public override bool CanWrite { get { return false; } }
    public override long Length { get { return length; } }
    public override long Position { get { return source.Position - offset; } set { if (value < 0 || value > length) throw new IOException("Invalid payload position"); source.Position = offset + value; } }
    public override int Read(byte[] buffer, int start, int count) { return source.Read(buffer, start, (int)Math.Min(count, length - Position)); }
    public override long Seek(long value, SeekOrigin origin) { Position = origin == SeekOrigin.Begin ? value : origin == SeekOrigin.Current ? Position + value : length + value; return Position; }
    public override void Flush() { }
    public override void SetLength(long value) { throw new NotSupportedException(); }
    public override void Write(byte[] buffer, int start, int count) { throw new NotSupportedException(); }
}

internal static class Installer
{
    [STAThread]
    private static int Main(string[] args)
    {
        if (args.Length > 0)
        {
            try
            {
                if (args.Length != 2 || args[0] != "--install-dir") throw new ArgumentException("Use --install-dir <empty folder>");
                Install(args[1], delegate(int n, string name) { });
                return 0;
            }
            catch (Exception error) { Trace.WriteLine(error); return 1; }
        }
        Application.EnableVisualStyles();
        Application.Run(new SetupWindow());
        return 0;
    }

    private static void CheckPath(string path)
    {
        for (DirectoryInfo item = new DirectoryInfo(path); item != null; item = item.Parent)
            if (item.Exists && (item.Attributes & FileAttributes.ReparsePoint) != 0)
                throw new IOException("Choose a normal folder, not a link / 請選擇一般資料夾。");
    }

    internal static void Install(string destination, Action<int, string> progress)
    {
        string root = Path.GetFullPath(destination).TrimEnd(Path.DirectorySeparatorChar);
        CheckPath(root);
        if (Directory.Exists(root) && Directory.GetFileSystemEntries(root).Length != 0)
            throw new IOException("Choose an empty folder; existing games and saves are never overwritten.\n請選擇空白資料夾；不會覆寫現有遊戲或存檔。");
        using (FileStream file = File.OpenRead(Assembly.GetExecutingAssembly().Location))
        {
            if (file.Length < 16) throw new IOException("Missing payload");
            file.Seek(-16, SeekOrigin.End);
            byte[] footer = new byte[16];
            if (file.Read(footer, 0, 16) != 16 || Encoding.ASCII.GetString(footer, 8, 8) != "SDPACKV1")
                throw new IOException("Invalid installer payload");
            long length = BitConverter.ToInt64(footer, 0);
            if (length <= 0 || length > file.Length - 16) throw new IOException("Invalid payload length");
            using (PayloadStream payload = new PayloadStream(file, file.Length - 16 - length, length))
            using (ZipArchive archive = new ZipArchive(payload, ZipArchiveMode.Read))
            {
                ZipArchiveEntry manifestEntry = archive.GetEntry("release-manifest.json");
                if (manifestEntry == null || manifestEntry.Length > 16000000) throw new IOException("Missing manifest");
                string manifestText;
                using (StreamReader reader = new StreamReader(manifestEntry.Open(), Encoding.UTF8)) manifestText = reader.ReadToEnd();
                JavaScriptSerializer serializer = new JavaScriptSerializer();
                serializer.MaxJsonLength = 16000000;
                var manifest = serializer.Deserialize<Dictionary<string, object>>(manifestText);
                var files = (Dictionary<string, object>)manifest["files"];
                if (files.Count == 0 || files.Count > 100000) throw new IOException("Invalid manifest count");
                var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                // Validate the entire directory before writing anything.
                foreach (ZipArchiveEntry entry in archive.Entries)
                {
                    if (entry.FullName == "release-manifest.json") continue;
                    string target = Path.GetFullPath(Path.Combine(root, entry.FullName.Replace('/', Path.DirectorySeparatorChar)));
                    if (!target.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)
                        || entry.FullName.IndexOf(':') >= 0 || !seen.Add(entry.FullName) || !files.ContainsKey(entry.FullName)
                        || ((entry.ExternalAttributes >> 16) & 0xF000) == 0xA000)
                        throw new IOException("Unsafe or unlisted payload file: " + entry.FullName);
                }
                if (seen.Count != files.Count) throw new IOException("Incomplete payload");
                Directory.CreateDirectory(root);
                string marker = Path.Combine(root, ".installation-incomplete");
                File.WriteAllText(marker, "Installation has not completed. Your existing game was not modified.");
                int done = 0;
                foreach (ZipArchiveEntry entry in archive.Entries)
                {
                    if (entry.FullName == "release-manifest.json") continue;
                    var expected = (Dictionary<string, object>)files[entry.FullName];
                    if (entry.Length != Convert.ToInt64(expected["size"])) throw new IOException("Size mismatch: " + entry.FullName);
                    string target = Path.GetFullPath(Path.Combine(root, entry.FullName.Replace('/', Path.DirectorySeparatorChar)));
                    Directory.CreateDirectory(Path.GetDirectoryName(target));
                    using (Stream source = entry.Open())
                    using (FileStream output = new FileStream(target, FileMode.CreateNew, FileAccess.ReadWrite))
                    using (SHA256 sha = SHA256.Create())
                    {
                        source.CopyTo(output);
                        output.Position = 0;
                        string digest = BitConverter.ToString(sha.ComputeHash(output)).Replace("-", "").ToLowerInvariant();
                        if (digest != (string)expected["sha256"]) throw new IOException("Checksum mismatch: " + entry.FullName);
                    }
                    progress(++done * 95 / files.Count, entry.FullName);
                }
                File.WriteAllText(Path.Combine(root, "release-manifest.json"), manifestText, new UTF8Encoding(false));
                progress(97, "Checking installed game / 檢查安裝結果…");
                ProcessStartInfo start = new ProcessStartInfo(Path.Combine(root, "SoundDetective.exe"), "--check");
                start.WorkingDirectory = root;
                start.UseShellExecute = false;
                start.CreateNoWindow = true;
                start.WindowStyle = ProcessWindowStyle.Hidden;
                using (Process process = Process.Start(start))
                {
                    if (!process.WaitForExit(120000)) { process.Kill(); throw new IOException("Installed dependency check timed out"); }
                    if (process.ExitCode != 0) throw new IOException("Installed check failed. See .runtime/launcher logs in the selected folder.");
                }
                File.Delete(marker);
                progress(100, "Ready / 完成");
            }
        }
    }

    internal static void Shortcut(string root)
    {
        Type shellType = Type.GetTypeFromProgID("WScript.Shell");
        object shell = Activator.CreateInstance(shellType);
        string path = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "Sound Detective.lnk");
        if (File.Exists(path)) return; // Keep existing shortcuts.
        object shortcut = shellType.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, shell, new object[] { path });
        Type shortcutType = shortcut.GetType();
        shortcutType.InvokeMember("TargetPath", BindingFlags.SetProperty, null, shortcut, new object[] { Path.Combine(root, "SoundDetective.exe") });
        shortcutType.InvokeMember("WorkingDirectory", BindingFlags.SetProperty, null, shortcut, new object[] { root });
        shortcutType.InvokeMember("Save", BindingFlags.InvokeMethod, null, shortcut, null);
    }
}

internal sealed class SetupWindow : Form
{
    private readonly TextBox folder = new TextBox();
    private readonly Label status = new Label();
    private readonly ProgressBar progress = new ProgressBar();
    private readonly Button install = new Button();
    private readonly Button browse = new Button();
    private readonly CheckBox shortcut = new CheckBox();
    private bool busy, finished;
    internal SetupWindow()
    {
        Text = "Sound Detective · Setup / 安裝";
        ClientSize = new System.Drawing.Size(640, 280);
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;
        Label title = new Label { Left = 24, Top = 20, Width = 590, Height = 50,
            Text = "Sound Detective\nOffline installation · Python + SuperCollider included / 已包含執行環境" };
        folder.SetBounds(24, 82, 490, 25);
        folder.Text = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "SoundDetective");
        browse.SetBounds(524, 80, 92, 28); browse.Text = "Browse / 選擇";
        browse.Click += delegate { using (FolderBrowserDialog dialog = new FolderBrowserDialog()) { if (dialog.ShowDialog() == DialogResult.OK) folder.Text = Path.Combine(dialog.SelectedPath, "SoundDetective"); } };
        shortcut.SetBounds(24, 118, 590, 24); shortcut.Text = "Create desktop shortcut / 建立桌面捷徑"; shortcut.Checked = true;
        progress.SetBounds(24, 156, 592, 22);
        status.SetBounds(24, 188, 592, 42); status.Text = "Choose an empty, writable folder / 請選擇可寫入的空白資料夾";
        install.SetBounds(430, 234, 186, 30); install.Text = "Install / 安裝";
        Controls.AddRange(new Control[] { title, folder, browse, shortcut, progress, status, install });
        install.Click += async delegate
        {
            if (finished) { Process.Start(new ProcessStartInfo(Path.Combine(folder.Text, "SoundDetective.exe")) { UseShellExecute = true, WorkingDirectory = folder.Text, WindowStyle = ProcessWindowStyle.Hidden }); Close(); return; }
            busy = true; folder.Enabled = browse.Enabled = install.Enabled = shortcut.Enabled = false;
            string destination = folder.Text;
            try
            {
                await Task.Run(delegate { Installer.Install(destination, delegate(int n, string name) { BeginInvoke((Action)delegate { progress.Value = n; status.Text = name; }); }); });
                if (shortcut.Checked) { try { Installer.Shortcut(destination); } catch (Exception) { status.Text = "Installed; shortcut could not be created / 已安裝，未能建立捷徑"; } }
                finished = true; install.Text = "Play / 開始遊戲";
                status.Text = "Installed successfully / 安裝完成";
            }
            catch (Exception error) { status.Text = error.Message; folder.Enabled = browse.Enabled = shortcut.Enabled = true; }
            finally { busy = false; install.Enabled = true; }
        };
        FormClosing += delegate(object sender, FormClosingEventArgs e) { if (busy) e.Cancel = true; };
    }
}
