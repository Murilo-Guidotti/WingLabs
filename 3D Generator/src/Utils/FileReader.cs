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

                string[] parts = line.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries);

                if (parts.Length >= 2 &&
                    double.TryParse(parts[0], NumberStyles.Float, CultureInfo.InvariantCulture, out double x) &&
                    double.TryParse(parts[1], NumberStyles.Float, CultureInfo.InvariantCulture, out double y))
                {
                    coordinates.Add(new Coordinate {X = x, Y = y});
                }
            }

            return coordinates;
        }

        public static void ShowAllDatCoordinates(List<Coordinate> coordinates)
        {
            foreach(var coord in coordinates)
            {
                Console.WriteLine($"X: {coord.X.ToString("F7",CultureInfo.InvariantCulture)}     Y: {coord.Y.ToString("F7",CultureInfo.InvariantCulture)}");
            }
        }
    }
}