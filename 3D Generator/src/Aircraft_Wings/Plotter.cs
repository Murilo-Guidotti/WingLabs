using System.Numerics;
using PicoGK;
using Leap71.ShapeKernel;
using FileReader;

namespace Plotter
{
    class genPlot
    {
        public static void Run(string filePath)
        {
            Library.oViewer().SetBackgroundColor("#6e6e6e");
            Library.oViewer().SetGroupMaterial(0, "#a86da8", 0, 0.1F);

            // 1. Lê o .dat (coordenadas normalizadas 0..1, mesmo parser de antes)
            List<Coordinate> coordinates = DatParser.ReadDatFile(filePath);
            Console.WriteLine($"[DEBUG] Coordenadas lidas: {coordinates.Count}");

            if (coordinates.Count < 3)
            {
                Console.WriteLine("Menos de 3 coordenadas — nada para desenhar.");
                return;
            }

            // 2. Define as estações ao longo da envergadura (raiz e ponta, por enquanto)
            float fSpanMM       = 1500f;
            float fRootChordMM  = 300f;
            float fTipChordMM   = 180f;
            float fTipTwistDeg  = -3f; // washout típico (ponta com incidência menor)

            LocalFrame oRootFrame = new LocalFrame();
            LocalFrame oTipFrame  = new LocalFrame()
                                        .oTranslate(new Vector3(0, 0, fSpanMM))
                                        .oRotate(fTipTwistDeg * MathF.PI / 180f, Vector3.UnitZ);

            List<Vector3> aRootSection = avecBuildSection(coordinates, oRootFrame, fRootChordMM);
            List<Vector3> aTipSection  = avecBuildSection(coordinates, oTipFrame, fTipChordMM);

            // 3. Monta o mesh: casca lateral (loft) + tampas na raiz e na ponta
            Mesh oMesh = new();
            AddLoftBetweenSections(ref oMesh, aRootSection, aTipSection);
            AddCap(ref oMesh, aRootSection, bFlip: true);   // raiz olhando para -Z
            AddCap(ref oMesh, aTipSection, bFlip: false);   // ponta olhando para +Z

            Console.WriteLine($"[DEBUG] Mesh gerado: {oMesh.nVertexCount()} vértices, {oMesh.nTriangleCount()} triângulos");

            Voxels voxWing = new(oMesh);
            Library.oViewer().Add(voxWing, 0);
            Console.WriteLine("[DEBUG] Asa adicionada ao viewer.");
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