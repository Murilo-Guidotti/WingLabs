namespace FileReader
{
    class readDat
    {
        public static int _lineNumber = 1;
        public static void readDatFile(string filePath)
        {
            try
            {
                using (StreamReader reader = new StreamReader(filePath))
                {
                    string? line;
                    char[,] x = new char[20, 1001];
                    char[,] y = new char[20, 1001];
                    int count = 0;
                    while ((line = reader.ReadLine()) != null)
                    {
                        if(line.StartsWith("NACA"))
                        {
                            Console.WriteLine(line);
                            _lineNumber++;
                        } else
                        {
                            for(count = 0; line[count] != ' '; count++)
                            {
                                x[count,_lineNumber] = line[count];
                            }

                            Console.WriteLine("Line Count: " + _lineNumber);
                            Console.WriteLine("Line: " + line);
                            Console.WriteLine("X: " + getXinIndex(count, _lineNumber, x) + "\n");
                            _lineNumber++;
                        }
                    }
                }
            }
            catch(Exception e)
            {
                Console.WriteLine(e);
            }        
        }

        private static string getXinIndex(int count, int lineNumber, char[,] x)
        {
            char[] chars = new char[count];
            for (int j = 0; j < count; j++)
            {
                chars[j] = x[j,lineNumber];
            }

            return new string(chars);
        }

        private static char getDatX(int count, int lineNumber, char[,] x, string line)
        {
            for(count = 0; line[count] != ' '; count++)
            {
                x[count,_lineNumber] = line[count];
            }
            return x[count, lineNumber];
        }
    }
}