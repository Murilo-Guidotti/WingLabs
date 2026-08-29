using PicoGK;
using FileReader;
using Plotter;
using PicoGKTesting;

using Leap71.ShapeKernel;

string strOutputFolder = @"D:\Projetos Robotica\TCC\WingLabs\3D Generator\output";

try
{
    // Inicializa o PicoGK com o tamanho de voxel desejado (ex: 0.1mm) e chama um exemplo do ShapeKernel
    PicoGK.Library.Go(0.1f, Leap71.ShapeKernelExamples.BaseLensShowCase.Task);
}
catch (Exception e)
{
    Console.WriteLine("Falha ao executar a tarefa.");
    Console.WriteLine(e.ToString());
}