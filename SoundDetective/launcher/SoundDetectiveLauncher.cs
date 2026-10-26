// GUI entry point for development and self-contained installed releases.
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

[assembly: AssemblyTitle("Sound Detective")]
[assembly: AssemblyDescription("Sound Detective desktop game launcher")]
[assembly: AssemblyProduct("Sound Detective")]
[assembly: AssemblyVersion("0.1.0.0")]
[assembly: AssemblyFileVersion("0.1.0.0")]

internal static class SoundDetectiveLauncher
{
    [STAThread]
    private static int Main(string[] args)
    {
        bool quiet = Array.IndexOf(args, "--check") >= 0 || Array.IndexOf(args, "--smoke-test") >= 0 || Array.IndexOf(args, "--diagnose") >= 0;
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string logPath = null;
        try
        {
            bool music = false, check = false, smoke = false, diagnose = false, diagnostics = false;
            foreach (string argument in args)
            {
                switch (argument)
                {
                    case "--music-studio": music = true; break;
                    case "--check": check = true; break;
                    case "--smoke-test": smoke = true; break;
                    case "--diagnose": diagnose = true; break;
                    case "--diagnostics": diagnostics = true; break;
                    default: throw new ArgumentException("Unknown launcher option: " + argument);
                }
            }
            if ((check ? 1 : 0) + (smoke ? 1 : 0) + (diagnose ? 1 : 0) + (diagnostics ? 1 : 0) > 1)
                throw new ArgumentException("Use --check or --smoke-test, not both.");

            string logDirectory = Path.Combine(root, ".runtime", "launcher");
            Directory.CreateDirectory(logDirectory);
            logPath = Path.Combine(logDirectory, "startup-" +
                DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fff") + "-" + Process.GetCurrentProcess().Id + ".log");
            using (StreamWriter log = new StreamWriter(logPath, false, new UTF8Encoding(false)))
            {
                log.AutoFlush = true;
                log.WriteLine("Sound Detective launcher | " + DateTime.UtcNow.ToString("o"));
                log.WriteLine("Project: " + root);
                string python = Path.Combine(root, "runtime", "pythonw.exe");
                if (!File.Exists(python)) python = Path.Combine(root, ".venv", "Scripts", "pythonw.exe");
                if (!File.Exists(python) || !File.Exists(Path.Combine(root, "sound_detective", "launcher.py")))
                    throw new FileNotFoundException("Keep SoundDetective.exe in the SoundDetective project folder, " +
                        "with its runtime (or .venv), engine and sound_detective folders. See docs/EXE_LAUNCHER.md for setup.");

                ProcessStartInfo start = new ProcessStartInfo();
                start.FileName = python;
                start.WorkingDirectory = root;
                start.Arguments = "-B -m sound_detective.launcher" + (music ? " --music-studio" : "") +
                    (check ? " --check" : "") + (smoke ? " --smoke-test" : "") +
                    (diagnose ? " --diagnose" : "") + (diagnostics ? " --diagnostics" : "");
                start.UseShellExecute = false;
                start.CreateNoWindow = true;
                start.WindowStyle = ProcessWindowStyle.Hidden;
                start.RedirectStandardOutput = true;
                start.RedirectStandardError = true;
                start.StandardOutputEncoding = Encoding.UTF8;
                start.StandardErrorEncoding = Encoding.UTF8;
                start.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
                start.EnvironmentVariables["PYTHONUTF8"] = "1";
                start.EnvironmentVariables["PYTHONNOUSERSITE"] = "1";
                start.EnvironmentVariables.Remove("PYTHONHOME");
                start.EnvironmentVariables.Remove("PYTHONPATH");
                string bundledEngine = Path.Combine(root, "engine", "SuperCollider");
                if (File.Exists(Path.Combine(bundledEngine, "sclang.exe")))
                    start.EnvironmentVariables["SOUND_DETECTIVE_SC_DIR"] = bundledEngine;
                object writeLock = new object();
                using (Process process = new Process())
                {
                    process.StartInfo = start;
                    DataReceivedEventHandler write = delegate(object sender, DataReceivedEventArgs line)
                    {
                        if (line.Data != null)
                            lock (writeLock) { log.WriteLine(line.Data); }
                    };
                    process.OutputDataReceived += write;
                    process.ErrorDataReceived += write;
                    if (!process.Start())
                        throw new InvalidOperationException("The game could not be started.");
                    process.BeginOutputReadLine();
                    process.BeginErrorReadLine();
                    process.WaitForExit();
                    int code = process.ExitCode;
                    log.WriteLine("Game exit code: " + code);
                    if (code != 0 && !quiet)
                        ShowError("The game could not finish starting or exited with an error.", logPath);
                    return code;
                }
            }
        }
        catch (Exception error)
        {
            if (logPath != null)
            {
                try { File.AppendAllText(logPath, error.ToString() + Environment.NewLine, new UTF8Encoding(false)); }
                catch (Exception) { }
            }
            if (!quiet) ShowError(error.Message, logPath);
            return 1;
        }
    }

    private static void ShowError(string message, string logPath)
    {
        MessageBox.Show(message + (logPath == null ? "" : "\n\nDetails / 詳細記錄:\n" + logPath),
            "Sound Detective", MessageBoxButtons.OK, MessageBoxIcon.Error);
    }
}
