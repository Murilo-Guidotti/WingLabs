using System;
using System.Text.Json;
using PicoGK;
using WingMaker;
try
{
    // Inicializa o PicoGK com o tamanho de voxel desejado (ex: 0.1mm) e chama um exemplo do ShapeKernel
    Library.Go(2.5f, () => WingMaker.genPlot.Run("C:/Users/ALUNO/Downloads/software/wing/WingLabs/output/naca_6512.dat"));
}
catch (Exception e)
{
    Console.WriteLine("Falha ao executar a tarefa.");
    Console.WriteLine(e.ToString());
}
