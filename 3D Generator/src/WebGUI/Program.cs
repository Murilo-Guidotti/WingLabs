using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://localhost:15000", "http://127.0.0.1:15000");

var app = builder.Build();

app.UseStaticFiles();

app.MapGet("/", () => Results.Redirect("/index.html"));

// Redirecionar para a pagina inicial se acessar a porta diretamente
app.MapGet("", () => Results.Redirect("/index.html"));

// Endpoint para verificar se o servidor está funcionando
app.MapGet("/api/ping", () => Results.Ok(new { status = "ok", message = "WingLabs Web GUI está funcionando!" }));

// Endpoint para gerar a asa
app.MapPost("/api/generate", async (HttpContext context) =>
{
    try
    {
        using var reader = new StreamReader(context.Request.Body);
        var requestBody = await reader.ReadToEndAsync();
        
        var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
        var parameters = JsonSerializer.Deserialize<WingParameters>(requestBody, options);
        
        if (parameters == null)
        {
            return Results.BadRequest(new GenerateResponse
            {
                Success = false,
                Error = "Parametros invalidos."
            });
        }
        
        // Validar arquivo .dat
        if (string.IsNullOrWhiteSpace(parameters.DatFilePath) || !System.IO.File.Exists(parameters.DatFilePath))
        {
            return Results.BadRequest(new GenerateResponse
            {
                Success = false,
                Error = "Arquivo .dat nao encontrado: " + parameters.DatFilePath
            });
        }
        
        // Validar diretorio de saida
        var outputDir = System.IO.Path.GetDirectoryName(parameters.OutputStlPath);
        if (!string.IsNullOrEmpty(outputDir) && !System.IO.Directory.Exists(outputDir))
        {
            System.IO.Directory.CreateDirectory(outputDir);
        }
        
        // Salvar parametros em um arquivo temporario para o programa principal ler
        var tempParamsFile = System.IO.Path.Combine(
            System.IO.Path.GetTempPath(),
            "winglabs_params.json"
        );
        
        System.IO.File.WriteAllText(tempParamsFile, requestBody);
        
        Console.WriteLine("[WEB] Parametros recebidos e salvos em: " + tempParamsFile);
        Console.WriteLine("[WEB] Arquivo .dat: " + parameters.DatFilePath);
        Console.WriteLine("[WEB] Span: " + parameters.WingSpanMM + " mm");
        Console.WriteLine("[WEB] Output STL: " + parameters.OutputStlPath);
        
        // Retornar sucesso
        return Results.Ok(new GenerateResponse
        {
            Success = true,
            SectionsCount = 0, // Será calculado pelo programa principal
            SectionSize = parameters.TargetSectionSizeMM,
            OutputPath = parameters.OutputStlPath,
            Message = "Parametros recebidos com sucesso. Execute o programa principal para gerar a asa."
        });
    }
    catch (Exception ex)
    {
        Console.WriteLine("[WEB] Erro: " + ex.Message);
        return Results.InternalServerError(new GenerateResponse
        {
            Success = false,
            Error = "Erro interno: " + ex.Message
        });
    }
});

app.Run();

// Classes para serializacao
public class WingParameters
{
    public string DatFilePath { get; set; } = "";
    public double WingSpanMM { get; set; } = 7450.0;
    public double RootChordMM { get; set; } = 1570.0;
    public double TipChordMM { get; set; } = 784.5;
    public double TipTwistDeg { get; set; } = -15.0;
    public double WingSweepDeg { get; set; } = 30.0;
    public double WingDihedralDeg { get; set; } = 0.0;
    public double TipChanferDeg { get; set; } = 0.0;
    public double TargetSectionSizeMM { get; set; } = 500.0;
    public string OutputStlPath { get; set; } = "output/wing.stl";
}

public class GenerateResponse
{
    public bool Success { get; set; }
    public string? Error { get; set; }
    public string? Message { get; set; }
    public int SectionsCount { get; set; }
    public double SectionSize { get; set; }
    public string? OutputPath { get; set; }
}
