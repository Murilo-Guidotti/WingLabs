namespace datReader
{
    class getCoordinates
    {
        public void readDatFile(Uri filePath)
        {
            try
            {
                using (StreamReader reader = new StreamReader(filePath.AbsolutePath))
                {
                    string line;
                    while ((line = reader.ReadLine()) != null)
                    {
                        Console.WriteLine(line);
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