using System.Numerics;
using PicoGK;
using Leap71.ShapeKernel;
using FileReader;

namespace WingMaker
{
    class genPlot
    {
        public static void Run(string filePath)
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

            // Wing Parameters (all of this needs to be parameters)
            double      dSpanMM           = 7450.0f;
            double      dRootChordMM      = 1570.0f;
            double      dTipChordMM       = 784.5f;
            double      dWingTwistDeg      = -30.0f;
            double      dWingSweepDeg     = 60.0f;
            double      dWingDihedralDeg  = 45.0f;
            // double      dTipChanferDeg    = 0.0f;

            // MemoryUsageDebug(); // Memory Debugger
            LocalFrame oRootFrame = new LocalFrame();
            LocalFrame oTipFrame  = new LocalFrame()
                                        .oTranslate(new Vector3((float) dRootChordMM / 2, 0, (float) dSpanMM))
                                        .oRotate((float) (dWingTwistDeg * Math.PI / 180f), Vector3.UnitZ)
                                        .oTranslate(new Vector3((float) Math.Tan(dWingSweepDeg * Math.PI / 180.0f) * (float) dSpanMM, 0, 0));

            List<LocalFrame> lFrames = CreateSections(dSpanMM, dWingTwistDeg, dWingSweepDeg, dWingDihedralDeg);
            oRootFrame = lFrames[0];
            oTipFrame = lFrames[^1];

            List<Vector3> aRootSection = avecBuildSection(coordinates, oRootFrame, dRootChordMM);
            List<Vector3> aTipSection  = avecBuildSection(coordinates, oTipFrame, dTipChordMM);

            // LOFT
            Mesh oMesh = new();
            AddLoftBetweenSections(ref oMesh, aRootSection, aTipSection);
            AddCap(ref oMesh, aRootSection, bFlip: true);
            AddCap(ref oMesh, aTipSection, bFlip: false);

            

            

            // Export the mesh in STL format
            oMesh.SaveToStlFile("C:/Users/ALUNO/Downloads/software/wing/WingLabs/output/wing2.stl"); // <-- this needs to be a parameter
            Console.WriteLine($"[DEBUG] Mesh salvo em wing.stl (C:/Users/ALUNO/Downloads/software/wing/WingLabs/output)");
            
            Console.WriteLine($"[DEBUG] Mesh gerado: {oMesh.nVertexCount()} vértices, {oMesh.nTriangleCount()} triângulos");

            Voxels voxWing = new(oMesh);
            voxWing.voxSmoothen(5f);

            Library.oViewer().Add(voxWing, 0);
            
            Console.WriteLine("[DEBUG] Asa adicionada ao viewer.\n");            
        }

        // Ignore this function, it's for the future if mesh division is needed
        static void CreateSections(Mesh oMesh)
        {
            BBox3 bBox = new BBox3();
            bBox = oMesh.oBoundingBox();
            
            float fSectionSize;

            fSectionSize = (bBox.vecSize().Z / 10.0f);
            Console.WriteLine($"[DEBUG] Tamanho de seção: {fSectionSize} mm");

        }

        // This is the actual function that will create the sections of the wing, based on the parameters provided
        static List<LocalFrame> CreateSections(double dSpanMM = 0, double dTwistDeg = 0, double dSweepDeg = 0, double dDihedralDeg = 0, double dTargetSectionSizeMM = 500)
        {
            const int   nMinSections = 2;
            const int   nMaxSections = 200;
            int         nSections;
            double      dSectionSize;


            nSections = (int) Math.Round(dSpanMM / dTargetSectionSizeMM);
            nSections = Math.Clamp(nSections, nMinSections, nMaxSections);
            dSectionSize = dSpanMM / nSections;

            double dTwist       = dTwistDeg / nSections;
            double dSweep       = dSweepDeg / nSections;
            double dDihedral    = dDihedralDeg / nSections;

            List<LocalFrame> lFrames = new List<LocalFrame>();
            lFrames.Add(new LocalFrame(new Vector3(0,0,0)));

            for(int i = 1; i < nSections; i++)
            {
                LocalFrame oFrame = new LocalFrame()
                                        .oTranslate(new Vector3(
                                            (float) Math.Tan((dSweep * nSections)  * Math.PI / 180.0f) * (float) dSpanMM,
                                            (float) Math.Tan((dDihedral * nSections) * Math.PI / 180.0f) * (float) dSpanMM,
                                            (float) dSectionSize))
                                        .oRotate((float) ((dTwist * nSections) * Math.PI / 180f), Vector3.UnitZ);
                
                Console.WriteLine($"X: {oFrame.vecGetLocalX().ToString()} || Y: {oFrame.vecGetLocalY().ToString()} || Z {oFrame.vecGetLocalZ().ToString()} || Position: {oFrame.vecGetPosition().ToString()}");
            }

            return lFrames;
        }

        static void CreateSectionsMesh(){}

        async static void MemoryUsageDebug()
        {
            await Task.Delay(2000);
            while (true)
            {
                Console.Write($"\r[DEBUG] Memória Total utilizada: {Library.oLibrary().nTotalMemUsage() / 1000000} MegaBytes || Memória Voxel utilizada: {Library.oLibrary().nVoxelsMemUsage() / 1000000} MegaBytes || Memória Meshes utilizada: {Library.oLibrary().nMeshesMemUsage() / 1000} KiloBytes");
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