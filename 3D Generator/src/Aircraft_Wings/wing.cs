using System.Numerics;
using Leap71.ShapeKernel;

namespace Plane{
    namespace Wing{
        public class wingMaker(){
        double 	dWingSpanMM;
        double 	dWingSweepDeg;
        double 	dWingTorxDeg;
        double 	dRootChordMM;
        double 	dTipChordMM;
        
        
            public static void CreateSectionsWing(double dWingSpanMM, double dWingSweepDeg, double dWingRotationDeg, double dTargetSectionSizeMM = 500){

                double     dWingSectionSize;
                double 		dWingSectionRotation; // Amount of rotation angle per section, until it reachs the wing total rotational angle
                const int 	nMinSections = 20; 	// Minimum number of sections
                const int 	nMaxSections = 500; 	// Maximum number of sections
                int        nSections;
            
                nSections = (int) Math.Round(dWingSpanMM / dTargetSectionSizeMM); 	// Divide the Wing span by the target section size, and round to the closest integer
                nSections = (int) Math.Clamp(nSections, nMinSections, nMaxSections);// Clamp the result amount of sections, the range IS hard coded (2 -> 50)
                dWingSectionSize = dWingSpanMM / nSections; 						// Divide the Wing Span by the number of sections, to get the size of each section 
                // This is a linear slicer, so each section have the same size, it's best practice to have a NON-Linear slicer
            
                dWingSectionRotation = dWingRotationDeg / nSections; // the rotation angle of each section
                // This rate of change is linear, for non-linear rate of change another function is needed
                // This means that the difference between the angle in section A and section B is the same than Section B and section C
            
                Console.WriteLine($"Número de seções: {nSections}");
                Console.WriteLine($"Tamanho de cada seção (mm): {dWingSectionSize:N4}");
                Console.WriteLine($"Rotação por seção (graus): {dWingSectionRotation:N4}");
                Console.WriteLine("---");
            
                List<LocalFrame> lFrames = new List<LocalFrame>();
                for (int i = 0; i <= nSections; i++) {
            
                    double dZ = i * dWingSectionSize;
                    double dSectionRotation = i * dWingSectionRotation;
                    double dY = Math.Tan((dWingSweepDeg * Math.PI) / 180f) * dZ;
            
                    Console.WriteLine($"Seção {i}: Z={dZ:F2}mm, Y={dY:F2}mm, Rotação={dSectionRotation:F2}°");
            
                    LocalFrame oFrame = new LocalFrame(new Vector3(0, (float) dY, (float) dZ));
                    oFrame.oRotate((float)dSectionRotation, Vector3.UnitZ);
                    lFrames.Add(oFrame);
                }
            }       
        }
    }
}