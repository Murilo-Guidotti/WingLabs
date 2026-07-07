using System.Numerics;
using PicoGK;
using FileReader;
using System.Globalization;

namespace Plotter
{
    class genPlot
    {
        public static void Run()
        {
            string filePath = "../../../../output/naca_6512.dat";
            Library.oViewer().SetBackgroundColor("#cfcfcf");
            Library.oViewer().SetGroupMaterial(0, "#e97bff", 0, 0.1F);

            Lattice lat = new();
            List<Coordinate> coordinates = DatParser.ReadDatFile(filePath);
            Vector3 vecPrev = new(float.Parse(coordinates[0].X.ToString("F7", CultureInfo.InvariantCulture)), float.Parse(coordinates[0].Y.ToString("F7", CultureInfo.InvariantCulture)), 0);

            for (int n = 1; n < coordinates.Count; n++)
            {
                Vector3 vecNew = new (  float.Parse(coordinates[n].X.ToString("F7", CultureInfo.InvariantCulture)),
                                        float.Parse(coordinates[n].Y.ToString("F7", CultureInfo.InvariantCulture)),
                                        0);

                lat.AddBeam(vecPrev,
                            vecNew,
                            1,
                            1,
                            true);

                vecPrev = vecNew;
            }

            DatParser.ShowAllDatCoordinates(DatParser.ReadDatFile(filePath));

            Voxels voxLat = new(lat);

            Library.oViewer().Add(voxLat, 0);
        }
    }
}