using PicoGK;
using Plotter;

string filePath = "D:\\Projetos Robotica\\TCC\\WingLabs\\output\\naca_6512.dat";

try
{
    // Inicializa o PicoGK com o tamanho de voxel desejado (ex: 0.1mm) e chama um exemplo do ShapeKernel
    Library.Go(2.5f, () => WingMaker.genPlot.Run(filePath));
}
catch (Exception e)
{
    Console.WriteLine("Falha ao executar a tarefa.");
    Console.WriteLine(e.ToString());
}