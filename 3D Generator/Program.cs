using System;
using System.Text.Json;
using PicoGK;
try
{
    // Inicializa o PicoGK com o tamanho de voxel desejado (ex: 0.1mm) e chama um exemplo do ShapeKernel
    Library.Go(2.5f, () => WingMaker.genPlot.Run("..\\..\\..\\..\\output\\naca_6512.dat"
    , 5000.0 // Span
    , 1570.0 // Root Chord
    , 784.5 // Tip Chord
    , -5.0 // Twist
    , 30.0 // Sweep
    , 45.0 // Dihedral
    , 0.0 // Tip Chanfer
    , 500.0 // Target Section Size
    , "..\\..\\..\\..\\output\\wing.stl"));
}
catch (Exception e)
{
    Console.WriteLine("Falha ao executar a tarefa.");
    Console.WriteLine(e.ToString());
}
