using System;
using System.Globalization;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;
using PicoGK;

Wing3DConfig cfg = Wing3DConfig.Load(args);
cfg.Validate();

try
{
    string? outDir = Path.GetDirectoryName(Path.GetFullPath(cfg.OutputStlPath));
    if (!string.IsNullOrEmpty(outDir))
    {
        Directory.CreateDirectory(outDir);
    }

    Console.WriteLine($"[3D] DAT: {cfg.DatFilePath}");
    Console.WriteLine($"[3D] STL: {cfg.OutputStlPath}");

    Library.Go(
        (float)cfg.VoxelSizeMM,
        () => WingMaker.genPlot.Run(
            cfg.DatFilePath,
            cfg.SpanMM,
            cfg.RootChordMM,
            cfg.TipChordMM,
            cfg.TipTwistDeg,
            cfg.WingSweepDeg,
            cfg.WingDihedralDeg,
            cfg.TipChanferDeg,
            cfg.TargetSectionSizeMM,
            cfg.OutputStlPath,
            cfg.ShellThicknessMM,
            cfg.ExportVoxelMesh,
            cfg.EllipticalTransition,
            cfg.RoundedTipCap,
            cfg.TipCapRadiusMM,
            cfg.CustomSections),
        bEndAppWithTask: cfg.Headless);
}
catch (Exception e)
{
    Console.WriteLine("Falha ao executar a tarefa.");
    Console.WriteLine(e.ToString());
    Environment.ExitCode = 1;
}

public sealed class WingSectionConfig
{
    [JsonPropertyName("z_mm")]
    public double ZMM { get; set; }

    [JsonPropertyName("chord_mm")]
    public double ChordMM { get; set; }

    [JsonPropertyName("sweep_x_mm")]
    public double SweepXMM { get; set; }

    [JsonPropertyName("dihedral_y_mm")]
    public double DihedralYMM { get; set; }

    [JsonPropertyName("twist_deg")]
    public double TwistDeg { get; set; }

    [JsonPropertyName("thickness_scale")]
    public double ThicknessScale { get; set; } = 1.0;
}

internal sealed class Wing3DConfig
{
    [JsonPropertyName("dat_file_path")]
    public string DatFilePath { get; set; } = Path.Combine("..", "output", "naca_6512.dat");

    [JsonPropertyName("output_stl_path")]
    public string OutputStlPath { get; set; } = Path.Combine("..", "output", "wing.stl");

    [JsonPropertyName("span_mm")]
    public double SpanMM { get; set; } = 5000.0;

    [JsonPropertyName("root_chord_mm")]
    public double RootChordMM { get; set; } = 1500.0;

    [JsonPropertyName("tip_chord_mm")]
    public double TipChordMM { get; set; } = 700.0;

    [JsonPropertyName("tip_twist_deg")]
    public double TipTwistDeg { get; set; } = -25.0;

    [JsonPropertyName("wing_sweep_deg")]
    public double WingSweepDeg { get; set; } = 35.0;

    [JsonPropertyName("wing_dihedral_deg")]
    public double WingDihedralDeg { get; set; } = 0.0;

    [JsonPropertyName("tip_chanfer_deg")]
    public double TipChanferDeg { get; set; } = 0.0;

    [JsonPropertyName("target_section_size_mm")]
    public double TargetSectionSizeMM { get; set; } = 500.0;

    [JsonPropertyName("voxel_size_mm")]
    public double VoxelSizeMM { get; set; } = 2.5;

    [JsonPropertyName("shell_thickness_mm")]
    public double ShellThicknessMM { get; set; } = 0.0;

    [JsonPropertyName("export_voxel_mesh")]
    public bool ExportVoxelMesh { get; set; } = false;

    [JsonPropertyName("elliptical_transition")]
    public bool EllipticalTransition { get; set; } = true;

    [JsonPropertyName("rounded_tip_cap")]
    public bool RoundedTipCap { get; set; } = true;

    [JsonPropertyName("tip_cap_radius_mm")]
    public double TipCapRadiusMM { get; set; } = 60.0;

    [JsonPropertyName("custom_sections")]
    public List<WingSectionConfig>? CustomSections { get; set; }

    [JsonPropertyName("headless")]
    public bool Headless { get; set; } = false;

    public void Validate()
    {
        SpanMM = Math.Max(10.0, SpanMM);
        RootChordMM = Math.Max(5.0, RootChordMM);
        TipChordMM = Math.Max(2.0, TipChordMM);
        TargetSectionSizeMM = Math.Max(1.0, TargetSectionSizeMM);
        VoxelSizeMM = Math.Clamp(VoxelSizeMM, 0.05, 100.0);
        ShellThicknessMM = Math.Max(0.0, ShellThicknessMM);
        TipCapRadiusMM = Math.Max(0.0, TipCapRadiusMM);
    }

    public static Wing3DConfig Load(string[] args)
    {
        var cfg = new Wing3DConfig();

        for (int i = 0; i < args.Length; i++)
        {
            string arg = args[i];
            if ((arg == "--config" || arg == "-c") && i + 1 < args.Length)
            {
                string jsonPath = args[++i];
                if (File.Exists(jsonPath))
                {
                    string json = File.ReadAllText(jsonPath);
                    var loaded = JsonSerializer.Deserialize<Wing3DConfig>(json);
                    if (loaded != null) cfg = loaded;
                }
            }
            else if (arg == "--dat" && i + 1 < args.Length) cfg.DatFilePath = args[++i];
            else if (arg == "--output" && i + 1 < args.Length) cfg.OutputStlPath = args[++i];
            else if (arg == "--span" && i + 1 < args.Length) cfg.SpanMM = ParseDouble(args[++i], cfg.SpanMM);
            else if (arg == "--root-chord" && i + 1 < args.Length) cfg.RootChordMM = ParseDouble(args[++i], cfg.RootChordMM);
            else if (arg == "--tip-chord" && i + 1 < args.Length) cfg.TipChordMM = ParseDouble(args[++i], cfg.TipChordMM);
            else if (arg == "--twist" && i + 1 < args.Length) cfg.TipTwistDeg = ParseDouble(args[++i], cfg.TipTwistDeg);
            else if (arg == "--sweep" && i + 1 < args.Length) cfg.WingSweepDeg = ParseDouble(args[++i], cfg.WingSweepDeg);
            else if (arg == "--dihedral" && i + 1 < args.Length) cfg.WingDihedralDeg = ParseDouble(args[++i], cfg.WingDihedralDeg);
            else if (arg == "--chanfer" && i + 1 < args.Length) cfg.TipChanferDeg = ParseDouble(args[++i], cfg.TipChanferDeg);
            else if (arg == "--section-size" && i + 1 < args.Length) cfg.TargetSectionSizeMM = ParseDouble(args[++i], cfg.TargetSectionSizeMM);
            else if (arg == "--voxel" && i + 1 < args.Length) cfg.VoxelSizeMM = ParseDouble(args[++i], cfg.VoxelSizeMM);
            else if (arg == "--shell-thickness" && i + 1 < args.Length) cfg.ShellThicknessMM = ParseDouble(args[++i], cfg.ShellThicknessMM);
            else if (arg == "--tip-cap-radius" && i + 1 < args.Length) cfg.TipCapRadiusMM = ParseDouble(args[++i], cfg.TipCapRadiusMM);
            else if (arg == "--export-voxel-mesh") cfg.ExportVoxelMesh = true;
            else if (arg == "--elliptical") cfg.EllipticalTransition = true;
            else if (arg == "--linear") cfg.EllipticalTransition = false;
            else if (arg == "--rounded-tip") cfg.RoundedTipCap = true;
            else if (arg == "--flat-tip") cfg.RoundedTipCap = false;
            else if (arg == "--headless") cfg.Headless = true;
        }

        return cfg;
    }

    private static double ParseDouble(string raw, double fallback)
        => double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out double val) ? val : fallback;
}
