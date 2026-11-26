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
            if (string.IsNullOrWhiteSpace(filePath) || !File.Exists(filePath))
            {
                return coordinates;
            }

            foreach (string rawLine in File.ReadLines(filePath))
            {
                string line = rawLine.Trim();
                if (string.IsNullOrEmpty(line) ||
                    line.StartsWith("#") ||
                    line.StartsWith(";") ||
                    line.StartsWith("//") ||
                    line.StartsWith("NACA", StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                string[] parts = line.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries);

                if (parts.Length >= 2 &&
                    double.TryParse(parts[0], NumberStyles.Float, CultureInfo.InvariantCulture, out double x) &&
                    double.TryParse(parts[1], NumberStyles.Float, CultureInfo.InvariantCulture, out double y) &&
                    double.IsFinite(x) && double.IsFinite(y))
                {
                    if (coordinates.Count > 0)
                    {
                        Coordinate prev = coordinates[coordinates.Count - 1];
                        double dx = x - prev.X;
                        double dy = y - prev.Y;
                        if ((dx * dx + dy * dy) < 1e-16)
                        {
                            continue;
                        }
                    }

                    coordinates.Add(new Coordinate { X = x, Y = y });
                }
            }

            return coordinates;
        }
    }
}