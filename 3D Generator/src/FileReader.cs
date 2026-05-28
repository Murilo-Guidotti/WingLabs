using System.Globalization;

namespace FileReader
{
    public struct Coordinate
    {
        public double X;
        public double Y;
    }

    public class DatParser
    {
        public static List<Coordinate> ReadDatFile(string filePath)
        {
            var coordinates = new List<Coordinate>();

            foreach(string line in File.ReadLines(filePath))
            {
                if (line.StartsWith("NACA", StringComparison.OrdinalIgnoreCase) || string.IsNullOrWhiteSpace(line))
                continue;

                string[] parts = line.Split(new[] {' '}, StringSplitOptions.RemoveEmptyEntries);

                if (parts.Length >= 2)
                {
                    double x = double.Parse(parts[0], CultureInfo.InvariantCulture);
                    double y = double.Parse(parts[1], CultureInfo.InvariantCulture);

                    coordinates.Add(new Coordinate {X = x, Y = y});
                }
            }

            return coordinates;
        }

        public static void ShowAllDatCoordinates(List<Coordinate> coordinates)
        {
            foreach(string a in coordinates)
            {
                
            }
        }
    }
}