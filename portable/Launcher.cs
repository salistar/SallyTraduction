// SallyTraduction portable : un seul .exe, sans installation.
// L'application (dossier PyInstaller + modèles) est ajoutée en fin de fichier sous forme de ZIP.
// Au premier lancement elle est décompressée dans %LOCALAPPDATA%\SallyTraduction\app-<version>,
// puis lancée directement les fois suivantes.
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Windows.Forms;

[assembly: System.Reflection.AssemblyTitle("SallyTraduction")]
[assembly: System.Reflection.AssemblyDescription("SallyTraduction - Traduction technique locale FR/EN (portable)")]
[assembly: System.Reflection.AssemblyCompany("SALISTAR")]
[assembly: System.Reflection.AssemblyProduct("SallyTraduction")]
[assembly: System.Reflection.AssemblyCopyright("Copyright (c) 2026 SALISTAR")]
[assembly: System.Reflection.AssemblyVersion("1.1.1.0")]
[assembly: System.Reflection.AssemblyFileVersion("1.1.1.0")]

static class Program
{
    const string Version = "1.1.1";
    const string Magic = "SALLYPK1";

    [DllImport("user32.dll")] static extern bool SetProcessDPIAware();

    [STAThread]
    static int Main(string[] args)
    {
        try { SetProcessDPIAware(); } catch { }
        string self = Application.ExecutablePath;
        string root = PickRoot(self);
        if (root == null)
        {
            MessageBox.Show("Aucun dossier accessible en écriture n'a été trouvé (profil utilisateur, dossier temporaire, " +
                            "dossier du programme).", "SallyTraduction", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 3;
        }
        string exe = Path.Combine(root, "SallyTraduction.exe");
        string marker = Path.Combine(root, ".portable-ok");

        long offset, length;
        if (!ReadTrailer(self, out offset, out length))
        {
            MessageBox.Show("Fichier incomplet ou endommagé : téléchargez de nouveau SallyTraduction.",
                            "SallyTraduction", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
        string stamp = length.ToString();
        bool ready = File.Exists(exe) && File.Exists(marker) && File.ReadAllText(marker) == stamp;
        if (!ready)
        {
            try { Directory.CreateDirectory(Path.GetDirectoryName(root)); } catch { }
            Application.EnableVisualStyles();
            var form = new SplashForm();
            Exception error = null;
            var worker = new Thread(() =>
            {
                try { Extract(self, offset, length, root, marker, stamp, form); }
                catch (Exception e) { error = e; }
                form.Done();
            });
            form.Shown += (s, e) => worker.Start();
            Application.Run(form);
            if (error != null)
            {
                MessageBox.Show("Impossible de préparer l'application :\n" + error.Message, "SallyTraduction",
                                MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 2;
            }
        }
        // --prepare <fichier> : décompresse seulement et écrit le dossier de l'application (utilisé par SallyTraduction.ps1)
        if (args.Length >= 1 && args[0] == "--prepare")
        {
            if (args.Length >= 2) File.WriteAllText(args[1], root, new UTF8Encoding(false));
            return 0;
        }
        var sb = new StringBuilder();
        foreach (var a in args) sb.Append(" \"").Append(a.Replace("\"", "\\\"")).Append('"');
        var p = Process.Start(new ProcessStartInfo(exe, sb.ToString()) { UseShellExecute = false, WorkingDirectory = root });
        if (Array.IndexOf(args, "--cli") >= 0)
        {
            p.WaitForExit();                 // ligne de commande : on attend et on renvoie le code de sortie
            return p.ExitCode;
        }
        return 0;
    }

    // Dossier de décompression, sans droits administrateur : profil local, puis dossier temporaire,
    // puis dossier du programme. Un dossier déjà prêt est réutilisé en priorité.
    static string PickRoot(string self)
    {
        var bases = new[] {
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            Path.GetTempPath(),
            Path.GetDirectoryName(self) };
        string firstWritable = null;
        foreach (var b in bases)
        {
            if (string.IsNullOrEmpty(b)) continue;
            string root = Path.Combine(b, "SallyTraduction", "app-" + Version);
            if (File.Exists(Path.Combine(root, ".portable-ok"))) return root;
            if (firstWritable == null && CanWrite(Path.Combine(b, "SallyTraduction"))) firstWritable = root;
        }
        return firstWritable;
    }

    static bool CanWrite(string dir)
    {
        try
        {
            Directory.CreateDirectory(dir);
            string probe = Path.Combine(dir, ".write-test-" + Guid.NewGuid().ToString("N"));
            File.WriteAllText(probe, "ok");
            File.Delete(probe);
            return true;
        }
        catch { return false; }
    }

    static bool ReadTrailer(string path, out long offset, out long length)
    {
        offset = length = 0;
        using (var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read))
        {
            if (fs.Length < 24) return false;
            fs.Seek(-24, SeekOrigin.End);
            var buf = new byte[24];
            fs.Read(buf, 0, 24);
            if (Encoding.ASCII.GetString(buf, 16, 8) != Magic) return false;
            offset = BitConverter.ToInt64(buf, 0);
            length = BitConverter.ToInt64(buf, 8);
            return offset > 0 && length > 0 && offset + length + 24 == fs.Length;
        }
    }

    static void Extract(string self, long offset, long length, string root, string marker, string stamp, SplashForm form)
    {
        string tmp = root + ".tmp";
        if (Directory.Exists(tmp)) Directory.Delete(tmp, true);
        Directory.CreateDirectory(tmp);
        using (var fs = new FileStream(self, FileMode.Open, FileAccess.Read, FileShare.Read))
        using (var zip = new ZipArchive(new SubStream(fs, offset, length), ZipArchiveMode.Read))
        {
            long total = 0, done = 0;
            foreach (var e in zip.Entries) total += e.Length;
            string full = Path.GetFullPath(tmp) + Path.DirectorySeparatorChar;
            foreach (var e in zip.Entries)
            {
                string dest = Path.GetFullPath(Path.Combine(tmp, e.FullName));
                if (!dest.StartsWith(full, StringComparison.OrdinalIgnoreCase)) continue;   // sécurité
                if (e.FullName.EndsWith("/")) { Directory.CreateDirectory(dest); continue; }
                Directory.CreateDirectory(Path.GetDirectoryName(dest));
                e.ExtractToFile(dest, true);
                done += e.Length;
                form.Progress(total > 0 ? (int)(done * 1000 / total) : 1000);
            }
        }
        if (Directory.Exists(root)) Directory.Delete(root, true);
        Directory.Move(tmp, root);
        File.WriteAllText(marker, stamp);
        // Nettoie les anciennes versions décompressées
        foreach (var d in Directory.GetDirectories(Path.GetDirectoryName(root), "app-*"))
            if (!string.Equals(d, root, StringComparison.OrdinalIgnoreCase))
                try { Directory.Delete(d, true); } catch { }
    }
}

// Fenêtre d'attente du premier lancement (thème de l'application)
class SplashForm : Form
{
    readonly ProgressBar bar;
    readonly Label pct;

    public SplashForm()
    {
        FormBorderStyle = FormBorderStyle.None;
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(14, 21, 40);
        ClientSize = new Size(520, 190);
        ShowInTaskbar = true;
        Text = "SallyTraduction";
        try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch { }
        var title = new Label { Text = "Sally", ForeColor = Color.White, Font = new Font("Segoe UI Semibold", 20f),
                                AutoSize = true, Location = new Point(30, 26) };
        var title2 = new Label { Text = "Traduction", ForeColor = Color.FromArgb(109, 106, 245), Font = new Font("Segoe UI Semibold", 20f),
                                 AutoSize = true, Location = new Point(98, 26) };
        var sub = new Label { Text = "Préparation du premier lancement… (une seule fois)", ForeColor = Color.FromArgb(141, 153, 179),
                              Font = new Font("Segoe UI", 10.5f), AutoSize = true, Location = new Point(33, 78) };
        bar = new ProgressBar { Location = new Point(34, 118), Size = new Size(400, 14), Maximum = 1000, Style = ProgressBarStyle.Continuous };
        pct = new Label { Text = "0 %", ForeColor = Color.White, Font = new Font("Segoe UI Semibold", 10.5f), AutoSize = true,
                          Location = new Point(448, 113) };
        var note = new Label { Text = "Aucune installation · 100 % hors ligne", ForeColor = Color.FromArgb(141, 153, 179),
                               Font = new Font("Segoe UI", 9f), AutoSize = true, Location = new Point(33, 150) };
        Controls.AddRange(new Control[] { title, title2, sub, bar, pct, note });
        title.SizeChanged += (s, e) => title2.Left = title.Right - 6;
    }

    public void Progress(int v)
    {
        if (!IsHandleCreated) return;
        BeginInvoke((Action)(() => { bar.Value = Math.Min(1000, v); pct.Text = (v / 10) + " %"; }));
    }

    public void Done()
    {
        if (IsHandleCreated) BeginInvoke((Action)Close);
    }
}

// Vue en lecture seule d'une portion d'un flux (le ZIP ajouté en fin d'exécutable)
class SubStream : Stream
{
    readonly Stream s; readonly long start, len; long pos;
    public SubStream(Stream s, long start, long len) { this.s = s; this.start = start; this.len = len; }
    public override bool CanRead { get { return true; } }
    public override bool CanSeek { get { return true; } }
    public override bool CanWrite { get { return false; } }
    public override long Length { get { return len; } }
    public override long Position { get { return pos; } set { pos = value; } }
    public override void Flush() { }
    public override int Read(byte[] buffer, int offset, int count)
    {
        long left = len - pos;
        if (left <= 0) return 0;
        if (count > left) count = (int)left;
        s.Seek(start + pos, SeekOrigin.Begin);
        int n = s.Read(buffer, offset, count);
        pos += n;
        return n;
    }
    public override long Seek(long offset, SeekOrigin origin)
    {
        if (origin == SeekOrigin.Begin) pos = offset;
        else if (origin == SeekOrigin.Current) pos += offset;
        else pos = len + offset;
        return pos;
    }
    public override void SetLength(long value) { throw new NotSupportedException(); }
    public override void Write(byte[] buffer, int offset, int count) { throw new NotSupportedException(); }
}
