namespace MiniLZO
{
    class Program
    {
        static void Main(string[] args)
        {
            if (args.Length < 3)
            {
                Console.WriteLine("Usage: MiniLZO <compress|decompress> <inputFile> <outputFile>");
                return;
            }

            string mode = args[0];
            string inputFile = args[1];
            string outputFile = args[2];

            try
            {
                byte[] input = File.ReadAllBytes(inputFile);
                byte[] output;

                if (mode == "compress")
                {
                    output = MiniLZO.CompressBytes(input);
                }
                else if (mode == "decompress")
                {
                    output = MiniLZO.DecompressBytes(input);
                }
                else
                {
                    Console.WriteLine("Invalid mode. Use 'compress' or 'decompress'.");
                    return;
                }

                File.WriteAllBytes(outputFile, output);
            }
            catch (Exception ex)
            {
                Console.WriteLine("Error: " + ex.Message);
                Environment.Exit(1);
            }
        }
    }
}
