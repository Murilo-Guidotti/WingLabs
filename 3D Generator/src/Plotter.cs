using System.Numerics;
using PicoGK;
using FileReader;

namespace Plotter
{
    class genPlot
    {
        const float fChordLengthMM = 100f;
        const float fBeamRadiusMM = 0.3f;

        public static void Run()
        {
            string filePath = "../output/naca_6512.dat";
            Library.oViewer().SetBackgroundColor("#cfcfcf");
            Library.oViewer().SetGroupMaterial(0, "#e97bff", 0, 0.1F);

            Lattice lat = new();
            List<Coordinate> coordinates = DatParser.ReadDatFile(filePath);

            Console.WriteLine($"[DEBUG] Coordenadas lidas: {coordinates.Count}");

            if (coordinates.Count < 2)
            {
                Console.WriteLine("Menos de 2 coordenadas lidas do arquivo .dat — nada para desenhar.");
                return;
            }

            // Converte todas as coordenadas normalizadas (0..1) para Vector3 em mm
            List<Vector3> points = new();
            foreach (var c in coordinates)
            {
                float x = (float)c.X * fChordLengthMM;
                float y = (float)c.Y * fChordLengthMM;
                points.Add(new Vector3(x, y, 0));
            }

            // Conecta TODOS os pontos em sequência (extradorso + intradorso)
            for (int n = 0; n < points.Count - 1; n++)
            {
                lat.AddBeam(points[n],
                            points[n + 1],
                            fBeamRadiusMM,
                            fBeamRadiusMM,
                            true);
            }

            // Fecha o contorno ligando o último ponto de volta ao primeiro
            lat.AddBeam(points[^1],
                        points[0],
                        fBeamRadiusMM,
                        fBeamRadiusMM,
                        true);

            float xMin = points.Min(p => p.X);
            float xMax = points.Max(p => p.X);
            float yMin = points.Min(p => p.Y);
            float yMax = points.Max(p => p.Y);
            Console.WriteLine($"[DEBUG] Bounding box: X [{xMin:F2}, {xMax:F2}]  Y [{yMin:F2}, {yMax:F2}]");

            DatParser.ShowAllDatCoordinates(coordinates);

            Voxels voxLat = new(lat);
            Console.WriteLine("[DEBUG] Voxels criados a partir da lattice, adicionando ao viewer...");

            Library.oViewer().Add(voxLat, 0);
            Console.WriteLine("[DEBUG] Objeto adicionado ao viewer.");

            Thread.Sleep(2000);

            voxLat.ProjectZSlice(voxLat.oCalculateBoundingBox().vecMin.Z, 100.0f);
        }
    }
}
