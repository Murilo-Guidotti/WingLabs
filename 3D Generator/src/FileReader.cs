namespace FileReader
{
    class readDat
    {
        public static void readDatFile(string filePath)
        {
            try
            {
                using (StreamReader reader = new StreamReader(filePath))
                {
                    string line;
                    char[] x;
                    string y = "";
                    while ((line = reader.ReadLine()) != null)
                    {
                        x = line.ToArray();
                        for(int i = 0; i < 10; i++)
                        {
                            // x[i] = line.ToArray().ElementAt(i);
                        }
                        Console.WriteLine(x);
                    }
                }
            }
            catch(Exception e)
            {
                Console.WriteLine(e);
            }        
        }
    }
}