using System.Text.Json;
using PicoGK;
using WingMaker;

// Classe para receber parametros da linha de comando
public class WingParameters
{
    public string DatFilePath { get; set; } = "D:\\Projetos Robotica\\TCC\\WingLabs\\output\\naca_6512.dat";
    public double WingSpanMM { get; set; } = 7450.0;
    public double RootChordMM { get; set; } = 1570.0;
    public double TipChordMM { get; set; } = 784.5;
    public double TipTwistDeg { get; set; } = -15.0;
    public double WingSweepDeg { get; set; } = 30.0;
    public double WingDihedralDeg { get; set; } = 0.0;
    public double TipChanferDeg { get; set; } = 0.0;
    public double TargetSectionSizeMM { get; set; } = 500.0;
    public string OutputStlPath { get; set; } = "D:\\Projetos Robotica\\TCC\\WingLabs\\output\\wing.stl";
}

// Classe para parse de argumentos
public static class CommandLineParser
{
    public static WingParameters Parse(string[] args)
    {
        var parameters = new WingParameters();
        
        for (int i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "--datFile" or "--dat":
                    if (i + 1 < args.Length) parameters.DatFilePath = args[++i];
                    break;
                case "--span":
                    if (i + 1 < args.Length) double.TryParse(args[++i], out parameters.WingSpanMM);
                    break;
                case "--rootChord":
                    if (i + 1 < args.Length) double.TryParse(args[++i], out parameters.RootChordMM);
                    break;
                case "--tipChord":
                    if (i + 1 < args.Length) double.TryParse(args[++i], out parameters.TipChordMM);
                    break;
                case "--tipTwist":
                    if (i + 1 < args.Length) double.TryParse(args[++i], out parameters.TipTwistDeg);
                    break;
                case "--sweep":
                    if (i + 1 < args.Length) double.TryParse(args[++i], out parameters.WingSweepDeg);
                    break;
                case "--dihedral":
                    if (i + 1 < args.Length) double.TryParse(args[++i], out parameters.WingDihedralDeg);
                    break;
                case "--chanfer":
                    if (i + 1 < args.Length) double.TryParse(args[++i], out parameters.TipChanferDeg);
                    break;
                case "--sectionSize":
                    if (i + 1 < args.Length) double.TryParse(args[++i], out parameters.TargetSectionSizeMM);
                    break;
                case "--output":
                    if (i + 1 < args.Length) parameters.OutputStlPath = args[++i];
                    break;
                case "--paramsFile":
                    if (i + 1 < args.Length)
                    {
                        var paramsFile = args[++i];
                        if (System.IO.File.Exists(paramsFile))
                        {
                            var json = System.IO.File.ReadAllText(paramsFile);
                            var parsedParams = JsonSerializer.Deserialize<WingParameters>(json);
                            if (parsedParams != null)
                            {
                                // Copiar valores nao nulos
                                if (!string.IsNullOrEmpty(parsedParams.DatFilePath))
                                    parameters.DatFilePath = parsedParams.DatFilePath;
                                if (parsedParams.WingSpanMM != 0)
                                    parameters.WingSpanMM = parsedParams.WingSpanMM;
                                if (parsedParams.RootChordMM != 0)
                                    parameters.RootChordMM = parsedParams.RootChordMM;
                                if (parsedParams.TipChordMM != 0)
                                    parameters.TipChordMM = parsedParams.TipChordMM;
                                if (parsedParams.TipTwistDeg != 0)
                                    parameters.TipTwistDeg = parsedParams.TipTwistDeg;
                                if (parsedParams.WingSweepDeg != 0)
                                    parameters.WingSweepDeg = parsedParams.WingSweepDeg;
                                if (parsedParams.WingDihedralDeg != 0)
                                    parameters.WingDihedralDeg = parsedParams.WingDihedralDeg;
                                if (parsedParams.TipChanferDeg != 0)
                                    parameters.TipChanferDeg = parsedParams.TipChanferDeg;
                                if (parsedParams.TargetSectionSizeMM != 0)
                                    parameters.TargetSectionSizeMM = parsedParams.TargetSectionSizeMM;
                                if (!string.IsNullOrEmpty(parsedParams.OutputStlPath))
                                    parameters.OutputStlPath = parsedParams.OutputStlPath;
                            }
                        }
                    }
                    break;
            }
        }
        
        return parameters;
    }
}

try
{
    // Parse arguments
    var parameters = CommandLineParser.Parse(args);
    
    Console.WriteLine("[WingLabs] Iniciando geracao da asa...");
    Console.WriteLine("[WingLabs] Parametros:");
    Console.WriteLine($"  Arquivo .dat: {parameters.DatFilePath}");
    Console.WriteLine($"  Span: {parameters.WingSpanMM} mm");
    Console.WriteLine($"  Root Chord: {parameters.RootChordMM} mm");
    Console.WriteLine($"  Tip Chord: {parameters.TipChordMM} mm");
    Console.WriteLine($"  Tip Twist: {parameters.TipTwistDeg} deg");
    Console.WriteLine($"  Sweep: {parameters.WingSweepDeg} deg");
    Console.WriteLine($"  Dihedral: {parameters.WingDihedralDeg} deg");
    Console.WriteLine($"  Chanfer: {parameters.TipChanferDeg} deg");
    Console.WriteLine($"  Target Section Size: {parameters.TargetSectionSizeMM} mm");
    Console.WriteLine($"  Output STL: {parameters.OutputStlPath}");
    Console.WriteLine();
    
    // Criar diretorio de saida se nao existir
    var outputDir = System.IO.Path.GetDirectoryName(parameters.OutputStlPath);
    if (!string.IsNullOrEmpty(outputDir) && !System.IO.Directory.Exists(outputDir))
    {
        System.IO.Directory.CreateDirectory(outputDir);
        Console.WriteLine($"[WingLabs] Diretorio criado: {outputDir}");
    }
    
    // Inicializa o PicoGK com o tamanho de voxel desejado e passa os parametros
    Library.Go(2.5f, () => WingMaker.genPlot.Run(
        parameters.DatFilePath,
        parameters.WingSpanMM,
        parameters.RootChordMM,
        parameters.TipChordMM,
        parameters.TipTwistDeg,
        parameters.WingSweepDeg,
        parameters.WingDihedralDeg,
        parameters.TipChanferDeg,
        parameters.TargetSectionSizeMM,
        parameters.OutputStlPath
    ));
    
    Console.WriteLine("[WingLabs] Asa gerada com sucesso!");
}
catch (Exception e)
{
    Console.WriteLine("[ERRO] Falha ao executar a tarefa.");
    Console.WriteLine(e.ToString());
}
