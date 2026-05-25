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

namespace PicoGKExamples
{
    class HelloWorld
    {
        public static void Task()
        {
            Lattice latOutside = new();
            Lattice latInside = new();

            latOutside.AddBeam(new Vector3(0), new Vector3(50, 0, 0), 10, 10, false);
            
            latInside.AddBeam(new Vector3(0), new Vector3(50, 0, 0), 8, 8, false);

            Voxels voxOutside = new Voxels(latOutside);
            Voxels voxInside = new Voxels(latInside);

            voxOutside.BoolSubtract(voxInside);

            Library.oViewer().Add(voxOutside);
        }
    }
}