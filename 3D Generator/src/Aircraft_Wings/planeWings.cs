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

            // 1. Lê o .dat (coordenadas normalizadas 0..1, mesmo parser de antes)
            List<Coordinate> coordinates = DatParser.ReadDatFile(filePath);
            Console.WriteLine($"[DEBUG] Coordenadas lidas: {coordinates.Count}");

            if (coordinates.Count.Equals(0))
            {
                Console.WriteLine("Nenhuma coordenada lida — Verifique o arquivo, ou o caminho do arquivo.");
                return;
            }

            // 2. Define as estações ao longo da envergadura (raiz e ponta, por enquanto)
            float fSpanMM       = 7450.0f;
            float fRootChordMM  = 785.0f;
            float fTipChordMM   = 392.5f;
            float fTipTwistDeg  = -15.0f;
            float fWingSweepDeg = 0.0f;
            float fWingDihedralDeg = 0.0f;
            float fTipChanferDeg = 0.0f;

            MemoryUsageDebug(); // Inicia o debug do uso de memória em segundo plano

            LocalFrame oRootFrame = new LocalFrame();
            LocalFrame oTipFrame  = new LocalFrame()
                                        .oTranslate(new Vector3(fRootChordMM / 2, 0, fSpanMM))
                                        .oRotate(fTipTwistDeg * MathF.PI / 180f, Vector3.UnitZ).oRotate(fTipChanferDeg * MathF.PI / 180f, Vector3.UnitY);

            List<Vector3> aRootSection = avecBuildSection(coordinates, oRootFrame, fRootChordMM);
            List<Vector3> aTipSection  = avecBuildSection(coordinates, oTipFrame, fTipChordMM);

            // 3. Monta o mesh: casca lateral (loft) + tampas na raiz e na ponta
            Mesh oMesh = new();
            AddLoftBetweenSections(ref oMesh, aRootSection, aTipSection);
            AddCap(ref oMesh, aRootSection, bFlip: true);   // raiz olhando para -Z
            AddCap(ref oMesh, aTipSection, bFlip: false);   // ponta olhando para +Z

            oMesh.SaveToStlFile("D:\\Projetos Robotica\\TCC\\WingLabs\\output\\wing.stl");
            Console.WriteLine($"[DEBUG] Mesh salvo em wing.stl (D:\\Projetos Robotica\\TCC\\WingLabs\\output\\wing.stl)");
            
            Console.WriteLine($"[DEBUG] Mesh gerado: {oMesh.nVertexCount()} vértices, {oMesh.nTriangleCount()} triângulos");

            Voxels voxWing = new(oMesh);
            voxWing.voxSmoothen(1);

            Library.oViewer().Add(voxWing, 0);
            Library.oViewer().ZoomToFit();
            
            Console.WriteLine("[DEBUG] Asa adicionada ao viewer.\n");
            
        }

        async static void MemoryUsageDebug()
        {
            await Task.Delay(2000);
            while (true)
            {
                Console.Write($"\r[DEBUG] Memória Total utilizada: {Library.oLibrary().nTotalMemUsage() / 1000000} MegaBytes || Memória Voxel utilizada: {Library.oLibrary().nVoxelsMemUsage() / 1000000} MegaBytes || Memória Meshes utilizada: {Library.oLibrary().nMeshesMemUsage() / 1000} KiloBytes");
                await Task.Delay(1000); // Loga a cada 1 segundos
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