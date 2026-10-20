using System.Numerics;
using PicoGK;
using Leap71.ShapeKernel;
using FileReader;

namespace WingMaker
{
    class genPlot
    {
        // Metodo original para compatibilidade
        public static void Run(string filePath)
        {
            Run(filePath, 7450.0, 1570.0, 784.5, -15.0, 30.0, 0.0, 0.0, 500.0, "..\\..\\..\\..\\output\\wing.stl");
        }
        
        // Novo metodo com todos os parametros
        public static void Run(
            string filePath,
            double dSpanMM = 7450.0,
            double dRootChordMM = 1570.0,
            double dTipChordMM = 784.5,
            double dTipTwistDeg = -15.0,
            double dWingSweepDeg = 30.0,
            double dWingDihedralDeg = 0.0,
            double dTipChanferDeg = 0.0,
            double dTargetSectionSizeMM = 500.0,
            string outputStlPath = "..\\..\\..\\..\\output\\wing.stl")
        {
            // Library.oViewer().SetBackgroundColor("#070707");
            Library.oViewer().SetBackgroundColor("#ffffff");
            // Library.oViewer().SetGroupMaterial(0, "#ffffff", 0.0f, 0.1F);
            Library.oViewer().SetGroupMaterial(0, "#212121", 0.4f, 0.8F);

            Console.WriteLine($"[DEBUG] Caminho do arquivo: {filePath}");

            // .Dat coordinates reader
            List<Coordinate> coordinates = DatParser.ReadDatFile(filePath);
            Console.WriteLine($"[DEBUG] Coordenadas lidas: {coordinates.Count}");

            if (coordinates.Count.Equals(0))
            {
                Console.WriteLine("Nenhuma coordenada lida — Verifique o arquivo, ou o caminho do arquivo.");
                return;
            }

            // Wing Parameters - agora passados como argumentos
            Console.WriteLine($"[DEBUG] Span: {dSpanMM} mm");
            Console.WriteLine($"[DEBUG] Root Chord: {dRootChordMM} mm");
            Console.WriteLine($"[DEBUG] Tip Chord: {dTipChordMM} mm");
            Console.WriteLine($"[DEBUG] Tip Twist: {dTipTwistDeg} deg");
            Console.WriteLine($"[DEBUG] Wing Sweep: {dWingSweepDeg} deg");
            Console.WriteLine($"[DEBUG] Wing Dihedral: {dWingDihedralDeg} deg");
            Console.WriteLine($"[DEBUG] Tip Chanfer: {dTipChanferDeg} deg");
            Console.WriteLine($"[DEBUG] Target Section Size: {dTargetSectionSizeMM} mm");
            Console.WriteLine($"[DEBUG] Output STL: {outputStlPath}");

            // MemoryUsageDebug(); // Memory Debugger
            LocalFrame oRootFrame = new LocalFrame();
            LocalFrame oTipFrame  = new LocalFrame()
                                        .oTranslate(new Vector3((float)(dRootChordMM / 2), 0, (float)dSpanMM))
                                        .oRotate((float) (dTipTwistDeg * Math.PI / 180f), Vector3.UnitZ)
                                        .oTranslate(new Vector3((float)(Math.Tan(dWingSweepDeg * Math.PI / 180.0f) * dSpanMM), 0, 0));
            // List<Vector3> aRootSection = avecBuildSection(coordinates, oRootFrame, dRootChordMM);
            // List<Vector3> aTipSection  = avecBuildSection(coordinates, oTipFrame, dTipChordMM);
            




            List<LocalFrame> lFrames = CreateSectionsWing(dSpanMM, dWingSweepDeg, dWingDihedralDeg, dTipTwistDeg, dRootChordMM, dTargetSectionSizeMM);
            Console.WriteLine($"[DEBUG] Seções geradas: {lFrames.Count}");

            Mesh oMesh = new();
            
            List<List<Vector3>> sections = new();
            double dTotalChordDiff = dRootChordMM - dTipChordMM;
            double dChordDiffPerSection = dTotalChordDiff / (lFrames.Count - 1);


            for(int i = 0; i < lFrames.Count; i++)
            {
                List<Vector3> section = avecBuildSection(coordinates, lFrames[i], dRootChordMM - (dChordDiffPerSection * i));
                sections.Add(section);
            }
            
            
            Voxels voxels = new();
            for(int i = 0; i < lFrames.Count; i++)
            {
                AddLoftBetweenSections(ref oMesh, sections[i==0? 0 : i-1], sections[i]);
                AddCap(ref oMesh, sections[i], bFlip: false);
                
                Console.WriteLine($"[DEBUG] Seções Criadas: {i}\n");  
                Console.WriteLine($"[DEBUG] Triângulos da Mesh: {oMesh.nTriangleCount()}\n");  
                Console.WriteLine($"[DEBUG] Vértices da Mesh: {oMesh.nVertexCount()}\n");
                voxels.BoolAdd(new(oMesh));
                Library.oViewer().Add(voxels, 0);
            }

            // // LOFT
            // AddLoftBetweenSections(ref oMesh, aRootSection, aTipSection);
            // AddCap(ref oMesh, aRootSection, bFlip: true);
            // AddCap(ref oMesh, aTipSection, bFlip: false);

            

            

            // Export the mesh in STL format
            oMesh.SaveToStlFile(outputStlPath);
            Console.WriteLine($"[DEBUG] Mesh salvo em: {outputStlPath}");
            
            // Console.WriteLine($"[DEBUG] Mesh gerado: {oMesh.nVertexCount()} vértices, {oMesh.nTriangleCount()} triângulos");

            // Voxels voxWing = new(oMesh);
            voxels.voxSmoothen(25f);

            Library.oViewer().Add(voxels, 0);
            
            Console.WriteLine("[DEBUG] Asa gerada com sucesso!\n");            
        }

        // This is the actual function that will create the sections of the wing, based on the parameters provided
        public static List<LocalFrame> CreateSectionsWing(double dWingSpanMM, double dWingSweepDeg, double dWingDihedralDeg, double dWingRotationDeg, double dRootChordMM,double dTargetSectionSizeMM = 500)
        {
            const int  nMinSections = 5;
            const int  nMaxSections = 500;
            int        nSections = Math.Clamp(
                                    (int) Math.Round(dWingSpanMM / dTargetSectionSizeMM),
                                    nMinSections,
                                    nMaxSections);
            double     dSectionSize = dWingSpanMM / nSections;
            double     dSectionRotation = dWingRotationDeg / nSections;
            double     dSweepPerSection = Math.Tan(dWingSweepDeg * Math.PI / 180f) * dWingSpanMM / nSections;
            double     dDihedralPerSection = Math.Tan(dWingDihedralDeg * Math.PI / 180f) * dWingSpanMM / nSections;

            {
                Console.WriteLine($"Número de seções: {nSections}");
                Console.WriteLine($"Tamanho de cada seção (mm): {dSectionSize:N4}");
                Console.WriteLine($"Rotação por seção (graus): {dSectionRotation:N4}");
                Console.WriteLine("---");
            } 
            
            List<LocalFrame> lFrames = new List<LocalFrame>();
            for (int i = 0; i <= nSections; i++) {
        
                double Legth = i * dSectionSize;
                double Sweep = i * dSweepPerSection;
                double Dihedral = i * dDihedralPerSection;
                Console.WriteLine($"Seção {i}: Lenght={Legth:F2}mm, Sweep={Sweep:F2}mm, Dihedral={Dihedral:F2}mm, Rotação={i * dSectionRotation:F2}°");
                
                LocalFrame oFrame = new LocalFrame().oTranslate(new Vector3((float) dRootChordMM / 2, 0, (float) Legth))
                        .oRotate((float) (dSectionRotation * i * Math.PI / 180f), Vector3.UnitZ)
                        .oTranslate(new Vector3((float)Sweep, (float)Dihedral, 0));
                
                lFrames.Add(oFrame);
            }
            return lFrames;
        }

        async static void MemoryUsageDebug()
        {
            await Task.Delay(2000);
            while (true)
            {
                Console.WriteLine($"\r[DEBUG] Memória Total utilizada: {Library.oLibrary().nTotalMemUsage() / 1000000} MegaBytes || Memória Voxel utilizada: {Library.oLibrary().nVoxelsMemUsage() / 1000000} MegaBytes || Memória Meshes utilizada: {Library.oLibrary().nMeshesMemUsage() / 1000} KiloBytes");
                await Task.Delay(1000);
            }
        }

        static List<Vector3> avecBuildSection(List<Coordinate> coordinates, LocalFrame oFrame, double dChordMM)
        {
            List<Vector3> avec = new();
            foreach (var c in coordinates)
            {
                float x = (float)c.X * (float)dChordMM;
                float y = (float)c.Y * (float)dChordMM;

                Vector3 vec = oFrame.vecGetPosition()
                            + x * oFrame.vecGetLocalX()
                            + y * oFrame.vecGetLocalY();
                avec.Add(vec);
            }
            return avec;
        }

        static void AddLoftBetweenSections(ref Mesh oMesh, List<Vector3> secA, List<Vector3> secB)
        {
            int n = Math.Min(secA.Count, secB.Count);
            for (int i = 0; i < n - 1; i++)
            {
                try
                {
                    oMesh.nAddTriangle(secA[i], secA[i + 1], secB[i + 1]);
                    oMesh.nAddTriangle(secA[i], secB[i + 1], secB[i]);    
                }catch(Exception e)
                {
                    Console.WriteLine($"[DEBUG] Erro ao adicionar loft entre seções: {e.Message}");
                }
            }
        }

        static void AddCap(ref Mesh oMesh, List<Vector3> section, bool bFlip)
        {
            Vector3 vecCentroid = Vector3.Zero;
            foreach (var vec in section)
                vecCentroid += vec;
            vecCentroid /= section.Count;

            for (int i = 0; i < section.Count - 1; i++)
            {
                if (!bFlip)
                    oMesh.nAddTriangle(vecCentroid, section[i], section[i + 1]);
                else
                    oMesh.nAddTriangle(vecCentroid, section[i + 1], section[i]);
            }
        }
    }
}