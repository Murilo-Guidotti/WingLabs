using PicoGK;
using PicoGKExamples;

// This simple call runs PicoGK with the specified task and shows the PicoGK viewer

Library.Go( 0.1f,                   // size of each voxel in millimeters
            HelloWorld.Task);       // the task you want to execute

// After you close the viewer, the application exits.

