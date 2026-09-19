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
            Run(filePath, 7450.0, 1570.0, 784.5, -15.0, 30.0, 0.0, 0.0, 500.0, "D:\\Projetos Robotica\\TCC\\WingLabs\\output\\wing.stl");
        }
        
        // Novo metodo com todos os parametros
        public static void Run(
            string filePath,
            double fSpanMM = 7450.0,
            double fRootChordMM = 1570.0,
            double fTipChordMM = 784.5,
            double fTipTwistDeg = -15.0,
            double fWingSweepDeg = 30.0,
            double fWingDihedralDeg = 0.0,
            double fTipChanferDeg = 0.0,
            double dTargetSectionSizeMM = 500.0,
            string outputStlPath = "D:\\Projetos Robotica\\TCC\\WingLabs\\output\\wing.stl")
        {
            Library.oViewer().SetBackgroundColor("#010005");
            Library.oViewer().SetGroupMaterial(0, "#ebebeb", 0.4f, 0.1F);

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
            Console.WriteLine($"[DEBUG] Span: {fSpanMM} mm");
            Console.WriteLine($"[DEBUG] Root Chord: {fRootChordMM} mm");
            Console.WriteLine($"[DEBUG] Tip Chord: {fTipChordMM} mm");
            Console.WriteLine($"[DEBUG] Tip Twist: {fTipTwistDeg} deg");
            Console.WriteLine($"[DEBUG] Wing Sweep: {fWingSweepDeg} deg");
            Console.WriteLine($"[DEBUG] Wing Dihedral: {fWingDihedralDeg} deg");
            Console.WriteLine($"[DEBUG] Tip Chanfer: {fTipChanferDeg} deg");
            Console.WriteLine($"[DEBUG] Target Section Size: {dTargetSectionSizeMM} mm");
            Console.WriteLine($"[DEBUG] Output STL: {outputStlPath}");

            // MemoryUsageDebug(); // Memory Debugger
            LocalFrame oRootFrame = new LocalFrame();
            LocalFrame oTipFrame  = new LocalFrame()
                                        .oTranslate(new Vector3(fRootChordMM / 2, 0, fSpanMM))
                                        .oRotate((float) (fTipTwistDeg * Math.PI / 180f), Vector3.UnitZ)
                                        .oTranslate(new Vector3((float) Math.Tan(fWingSweepDeg * Math.PI / 180.0f) * fSpanMM, 0, 0));

            List<Vector3> aRootSection = avecBuildSection(coordinates, oRootFrame, fRootChordMM);
            List<Vector3> aTipSection  = avecBuildSection(coordinates, oTipFrame, fTipChordMM);

            // LOFT
            Mesh oMesh = new();
            AddLoftBetweenSections(ref oMesh, aRootSection, aTipSection);
            AddCap(ref oMesh, aRootSection, bFlip: true);
            AddCap(ref oMesh, aTipSection, bFlip: false);
            
            // Chamar CreateSectionsWing com o target section size
            List<LocalFrame> wingFrames = CreateSectionsWing(
                fSpanMM,
                fWingSweepDeg,
                fTipTwistDeg,
                dTargetSectionSizeMM
            );

            // Export the mesh in STL format
            oMesh.SaveToStlFile(outputStlPath);
            Console.WriteLine($"[DEBUG] Mesh salvo em: {outputStlPath}");
            
            Console.WriteLine($"[DEBUG] Mesh gerado: {oMesh.nVertexCount()} vértices, {oMesh.nTriangleCount()} triângulos");
            Console.WriteLine($"[DEBUG] Seções geradas: {wingFrames.Count}");

            // Voxels voxWing = new(oMesh);
            // voxWing.voxSmoothen(5f);

            // Library.oViewer().Add(voxWing, 0);
            
            Console.WriteLine("[DEBUG] Asa gerada com sucesso!\n");            
        }

        // This is the actual function that will create the sections of the wing, based on the parameters provided
        public static List<LocalFrame> CreateSectionsWing(double dWingSpanMM, double dWingSweepDeg, double dWingRotationDeg, double dTargetSectionSizeMM = 500)
        {
            double     dWingSectionSize;
            double     dWingSectionRotation;
            const int  nMinSections = 20;
            const int  nMaxSections = 500;
            int        nSections;
        
            nSections = (int) Math.Round(dWingSpanMM / dTargetSectionSizeMM);
            nSections = (int) Math.Clamp(nSections, nMinSections, nMaxSections);
            dWingSectionSize = dWingSpanMM / nSections;
        
            dWingSectionRotation = dWingRotationDeg / nSections;
        
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
                oFrame.oRotate(dSectionRotation, Vector3.UnitZ);
                lFrames.Add(oFrame);
            }
            return lFrames;
        }

        async static void MemoryUsageDebug()
        {
            await Task.Delay(2000);
            while (true)
            {
                Console.Write($"\r[DEBUG] Memória Total utilizada: {Library.oLibrary().nTotalMemUsage() / 1000000} MegaBytes || Memória Voxel utilizada: {Library.oLibrary().nVoxelsMemUsage() / 1000000} MegaBytes || Memória Meshes utilizada: {Library.oLibrary().nMeshesMemUsage() / 1000} KiloBytes");
                await Task.Delay(1000);
            }
        }

        static List<Vector3> avecBuildSection(List<Coordinate> coordinates, LocalFrame oFrame, float fChordMM)
        {
            List<Vector3> avec = new();
            foreach (var c in coordinates)
            {
                float x = (float)c.X * fChordMM;
                float y = (float)c.Y * fChordMM;

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
                oMesh.nAddTriangle(secA[i], secA[i + 1], secB[i + 1]);
                oMesh.nAddTriangle(secA[i], secB[i + 1], secB[i]);
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