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
            float   fSpanMM           = 7450.0f;
            float   fRootChordMM      = 1570.0f;
            float   fTipChordMM       = 784.5f;
            float   fTipTwistDeg      = -15.0f;
            double  fWingSweepDeg     = 30.0f;
            float   fWingDihedralDeg  = 0.0f;
            float   fTipChanferDeg    = 0.0f;

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
            CreateSections(fSpanMM);


            // Export the mesh in STL format
            oMesh.SaveToStlFile("D:\\Projetos Robotica\\TCC\\WingLabs\\output\\wing.stl"); // <-- this needs to be a parameter
            Console.WriteLine($"[DEBUG] Mesh salvo em wing.stl (D:\\Projetos Robotica\\TCC\\WingLabs\\output\\wing.stl)");
            
            Console.WriteLine($"[DEBUG] Mesh gerado: {oMesh.nVertexCount()} vértices, {oMesh.nTriangleCount()} triângulos");

            // Voxels voxWing = new(oMesh);
            // voxWing.voxSmoothen(5f);

            // Library.oViewer().Add(voxWing, 0);
            
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
        static void CreateSections(float fSpanMM = 0, float fRootChordMM = 0, float fTipChordMM = 0, float fTipTwistDeg = 0, double fWingSweepDeg = 0, float fWingDihedralDeg = 0, float fTipChanferDeg = 0)
        {
            double fSectionSize = fSpanMM / 10.0f;
            Console.WriteLine($"[DEBUG] Tamanho de seção: {fSectionSize} mm");

            LocalFrame []oNFrame = new LocalFrame[(int) Math.Floor(fSpanMM / fSectionSize)];
            Console.WriteLine($"[DEBUG] Quantidade de seções: {oNFrame.Length}");
        }

        static void CreateSectionsMehs(){}

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