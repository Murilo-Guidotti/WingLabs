using PicoGK;
using PicoGKExamples;

// This simple call runs PicoGK with the specified task and shows the PicoGK viewer

Library.Go( 0.1f,                   // size of each voxel in millimeters
            HelloWorld.Task);       // the task you want to execute

// try
// {
//     using (StreamReader reader = new StreamReader("C:/Users/ALUNO/Downloads/WingLabs/output/naca_6512.dat"))
//     {
//         string line;
//         while ((line = reader.ReadLine()) != null)
//         {
//             Console.WriteLine(line);
//         }
//     }
// }
// catch(Exception e)
// {
//     Console.WriteLine(e);
// }

// After you close the viewer, the application exits.

