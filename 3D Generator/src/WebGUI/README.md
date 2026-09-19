# WingLabs Web GUI

Uma interface web para o gerador de asas 3D WingLabs. Funciona em Windows e Linux.

## Estrutura

- **`wwwroot/index.html`** - Página HTML com formulário para inserção de parâmetros
- **`Program.cs`** - Servidor web ASP.NET Core Minimal API
- **`WebGUI.csproj`** - Projeto .NET para o servidor web
- **`start_webui.bat`** - Script para iniciar o servidor no Windows
- **`start_webui.sh`** - Script para iniciar o servidor no Linux

## Requisitos

- .NET 9.0 ou superior
- Navegador web moderno (Chrome, Firefox, Edge, etc.)

## Como usar

### 1. Iniciar o servidor web

#### No Windows:
```cmd
cd 3D Generator\src\WebGUI
start_webui.bat
```

#### No Linux:
```bash
cd "3D Generator/src/WebGUI"
chmod +x start_webui.sh
./start_webui.sh
```

Ou manualmente:
```bash
dotnet run --project WebGUI.csproj
```

### 2. Acessar a interface

Abra o navegador e acesse: **http://localhost:20000**

### 3. Preencher os parâmetros

- **Caminho do arquivo .dat**: Caminho completo para o arquivo com coordenadas do perfil aerodinâmico
- **Envergadura (Span)**: Distância de ponta a ponta da asa em mm
- **Corda na Raiz**: Largura do perfil na raiz em mm
- **Corda na Ponta**: Largura do perfil na ponta em mm
- **Torção na Ponta (Twist)**: Ângulo de torção na ponta em graus
- **Varredura (Sweep)**: Ângulo de varredura em graus
- **Diedro**: Ângulo de inclinação vertical da asa em graus
- **Chanfro na Ponta**: Ângulo de corte na ponta da asa em graus
- **Tamanho alvo da seção**: Tamanho aproximado de cada seção da asa em mm
- **Caminho do arquivo STL de saída**: Local onde o arquivo STL será salvo

### 4. Gerar a asa

Clique no botão **"Gerar Asa 3D"** para submeter os parâmetros.

A GUI web irá:
1. Validar o arquivo .dat
2. Criar o diretório de saída se não existir
3. Salvar os parâmetros em um arquivo temporário
4. Retornar uma confirmação

### 5. Executar a geração

Após enviar os parâmetros, execute o programa principal:

#### No Windows (PowerShell):
```powershell
cd 3D Generator
."src\WebGUI\run_winglabs.ps1"
```

#### Ou manualmente:
```bash
cd 3D Generator
dotnet run -- --paramsFile="%TEMP%\winglabs_params.json"
```

Ou passe os parâmetros diretamente:
```bash
dotnet run -- --datFile="caminho/para/arquivo.dat" --span=7450 --rootChord=1570 --tipChord=784.5 --tipTwist=-15 --sweep=30 --sectionSize=500 --output="caminho/para/saida.stl"
```

## API Endpoints

- **GET /** - Redireciona para /index.html
- **GET /api/ping** - Verifica se o servidor está funcionando
- **POST /api/generate** - Recebe os parâmetros e salva em arquivo temporário

## Formato do JSON (POST /api/generate)

```json
{
    "datFilePath": "D:\\Projetos Robotica\\TCC\\WingLabs\\output\\naca_6512.dat",
    "wingSpanMM": 7450.0,
    "rootChordMM": 1570.0,
    "tipChordMM": 784.5,
    "tipTwistDeg": -15.0,
    "wingSweepDeg": 30.0,
    "wingDihedralDeg": 0.0,
    "tipChanferDeg": 0.0,
    "targetSectionSizeMM": 500.0,
    "outputStlPath": "D:\\Projetos Robotica\\TCC\\WingLabs\\output\\wing.stl"
}
```

## Resposta da API

```json
{
    "success": true,
    "message": "Parametros recebidos com sucesso.",
    "sectionsCount": 15,
    "sectionSize": 500.0,
    "outputPath": "D:\\Projetos Robotica\\TCC\\WingLabs\\output\\wing.stl"
}
```

## Solução de problemas

### Porto 20000 já está em uso
Altere o número da porta nos arquivos:
- `Program.cs` - Linha: `builder.WebHost.UseUrls("http://localhost:20000"...`
- `start_webui.bat` - Mensagem de porta

### Erro de permissão (Linux)
Execute com permissões de administrador ou mude a porta para um número acima de 1024.

### Arquivo .dat não encontrado
Verifique se o caminho está correto e o arquivo existe.

### .NET não encontrado
Instale o .NET 9.0 SDK:
- Windows: https://dotnet.microsoft.com/download/dotnet/9.0
- Linux: https://docs.microsoft.com/pt-br/dotnet/core/install/linux

## Tecnologias usadas

- **Frontend**: HTML5, CSS3, JavaScript puro
- **Backend**: ASP.NET Core Minimal API
- **C#**: .NET 9.0
- **Biblioteca 3D**: PicoGK com ShapeKernel

## License

MIT License - Sinta-se à vontade para usar e modificar.
