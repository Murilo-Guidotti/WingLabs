using PicoGK;
using PicoGKExamples;
using FileReader;

// This simple call runs PicoGK with the specified task and shows the PicoGK viewer

// Library.Go( 0.1f,                   // size of each voxel in millimeters
//             HelloWorld.Task);       // the task you want to execute

string datpath = "/home/zenith/Downloads/WingLabs/output/naca_6512.dat";
readDat.readDatFile(datpath);

// After you close the viewer, the application exits.

