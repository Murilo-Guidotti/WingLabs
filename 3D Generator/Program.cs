using PicoGK;
using FileReader;
using PicoGKTesting;
using Plotter;

// This simple call runs PicoGK with the specified task and shows the PicoGK viewer

// Library.Go( 0.1f,                   // size of each voxel in millimeters
//             HelloWorld.Task);       // the task you want to execute

string datpath = "../../../../output/naca_6512.dat";
DatParser.ShowAllDatCoordinates(DatParser.ReadDatFile(datpath));


Library.Go(1f, () => genPlot.Run(datpath));

// After you close the viewer, the application exits.

