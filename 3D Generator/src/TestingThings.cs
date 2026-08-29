//
// SPDX-License-Identifier: CC0-1.0
//
// This example code file is released to the public under Creative Commons CC0.
// See https://creativecommons.org/publicdomain/zero/1.0/legalcode
//
// To the extent possible under law, the author has waived all copyright and
// related or neighboring rights to this example code file.
//
// THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS
// OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
// THE SOFTWARE.
//

using System.Numerics;
using PicoGK;

namespace PicoGKTesting
{
    class Testing
    {
        public static void Run()
        {

            // ==========================================
        // STEP 1: Criar uma Lattice (Estrutura Reticulada)
        // ==========================================
        Lattice lattice = new();
        
        float fRadius = 30.0f;
        int nPoints = 50;

        // Gera uma hélice matemática tridimensional conectada por barras
        for (int i = 0; i < nPoints; i++)
        {
            float t1 = i * 0.2f;
            float t2 = (i + 1) * 0.2f;

            Vector3 v1 = new(
                MathF.Cos(t1) * fRadius,
                MathF.Sin(t1) * fRadius,
                i * 2.0f
            );

            Vector3 v2 = new(
                MathF.Cos(t2) * fRadius,
                MathF.Sin(t2) * fRadius,
                (i + 1) * 2.0f
            );

            // Adiciona uma barra entre v1 e v2 com raio inicial de 3mm e raio final de 1mm
            lattice.AddBeam(v1, v2, 3.0f, 1.0f, true);
        }

        // Converte a estrutura de barras (Lattice) para Voxels 3D
        Voxels voxLattice = new(lattice);

        // ==========================================
        // STEP 2: Criar um Cilindro Sólido via Lattice
        // ==========================================
        Lattice latticeCilindro = new();
        // Um cilindro pode ser definido como uma única barra de grande raio
        latticeCilindro.AddBeam(
            new Vector3(0, 0, 0), 
            new Vector3(0, 0, 100), 
            35.0f, 35.0f, false
        );

        Voxels voxCilindro = new(latticeCilindro);

        // ==========================================
        // STEP 3: Operações Booleanas (Corte/Interseção)
        // ==========================================
        
        // Subtrai a estrutura em hélice do cilindro sólido (Cria canais internos)
        // voxCilindro.BoolSubtract(voxLattice);

        // Alternativa: Operação de Interseção
        voxCilindro.BoolIntersect(voxLattice); // Mantém apenas a intersecção

        // ==========================================
        // STEP 4: Exibir no Visualizador e Exportar
        // ==========================================
        
        // Adiciona ao visualizador viewport do PicoGK
        Library.oViewer().Add(voxCilindro);

        // Opcional: Converter os Voxels em Mesh de triângulos para exportar em STL/3MF
        Mesh meshFinal = new(voxCilindro);
        // meshFinal.SaveToStl("PecaComplexa.stl");
        }

        public static void test()
        {
            Matrix4x4 matMoved = Matrix4x4.CreateTranslation(new Vector3(50,0,0));

            Vector3 vecOrigin = Vector3.Zero;
            Vector3 vec100mmX = new(100,0,0);

            Vector3 vecOriginT = Vector3.Transform(vecOrigin, matMoved);
            Vector3 vec100mmXT = Vector3.Transform(vec100mmX, matMoved);

            Plane plane = new Plane(Vector3.UnitX, 0);
            Matrix4x4 matPlane = Matrix4x4.CreateReflection(plane);

            Vector3 vecOriginP = Vector3.Transform(vecOrigin, matPlane);
            Vector3 vec100mmXP = Vector3.Transform(vec100mmX, matPlane);

            Quaternion quatZ    = Quaternion.CreateFromAxisAngle(Vector3.UnitZ, float.Pi / 2);
            Matrix4x4 matQuatZ  = Matrix4x4.CreateFromQuaternion(quatZ);

            Vector3 vecOriginQZ = Vector3.Transform(vecOrigin, matQuatZ);
            Vector3 vec100mmXQZ = Vector3.Transform(vec100mmX, matQuatZ);

            Console.WriteLine($"Origin is at {vecOriginT}");
            Console.WriteLine($"100mm is at {vec100mmXT}");
            Console.WriteLine($"Origin Plane is at {vecOriginP}");
            Console.WriteLine($"100mm Plane is at {vec100mmXP}");
            Console.WriteLine($"Origin Rotated is at {vecOriginQZ}");
            Console.WriteLine($"100mm Rotated is at {vec100mmXQZ}");
        }
    }   
}