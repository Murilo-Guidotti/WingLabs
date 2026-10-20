using System;
using System.Text.Json;
using PicoGK;
try
{
    // Inicializa o PicoGK com o tamanho de voxel desejado (ex: 0.1mm) e chama um exemplo do ShapeKernel
    Library.Go(2.5f, () => WingMaker.genPlot.Run("..\\..\\..\\..\\output\\naca_6512.dat"
    , 5000.0 // Span
    , 1500.0 // Root Chord
    , 700.0 // Tip Chord
    , -25.0 // Twist
    , 35.0 // Sweep
    , 0.0 // Dihedral
    , 0.0 // Tip Chanfer
    , 500.0 // Target Section Size
    , "..\\..\\..\\..\\output\\wing.stl"));
}
catch (Exception e)
{
    Console.WriteLine("Falha ao executar a tarefa.");
    Console.WriteLine(e.ToString());
}
