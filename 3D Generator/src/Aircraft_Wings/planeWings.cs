using System.Diagnostics;
using System.Numerics;
using PicoGK;
using Leap71.ShapeKernel;
using FileReader;

namespace WingMaker
{
    class genPlot
    {
        // Fração da corda usada como pivô de torção aerodinâmica (25% = centro aerodinâmico c/4)
        private const float TwistPivotChordFraction = 0.25f;

        // Início da zona de transição elíptica na ponta da asa (80% da envergadura)
        private const double TipTransitionStart = 0.80;

        // Método parametrizado completo
        public static void Run(
            string filePath,
            double dSpanMM = 7450.0,
            double dRootChordMM = 1570.0,
            double dTipChordMM = 784.5,
            double dTipTwistDeg = -15.0,
            double dWingSweepDeg = 30.0,
            double dWingDihedralDeg = 0.0,
            double dTipChanferDeg = 0.0,
            double dTargetSectionSizeMM = 500.0,
            string outputStlPath = "..\\..\\..\\..\\output\\wing.stl",
            double dShellThicknessMM = 0.0,
            bool bExportVoxelMesh = false,
            bool bEllipticalTransition = true,
            bool bRoundedTipCap = true,
            double dTipCapRadiusMM = 60.0,
            List<WingSectionConfig>? customSections = null)
        {
            var sw = Stopwatch.StartNew();

            Library.oViewer().SetBackgroundColor("#001521");
            Library.oViewer().SetGroupMaterial(0, "#00349d", 0.1f, 0.8f);

            Console.WriteLine($"[3D] Lendo arquivo .dat: {filePath}");
            List<Coordinate> coordinates = DatParser.ReadDatFile(filePath);
            Console.WriteLine($"[3D] Coordenadas válidas lidas: {coordinates.Count}");

            if (coordinates.Count < 3)
            {
                Console.WriteLine("[ERRO] Coordenadas insuficientes (< 3) — Verifique o arquivo .dat.");
                return;
            }

            bool bUsingCustomSections = customSections != null && customSections.Count >= 2;
            Console.WriteLine(
                $"[3D] Parâmetros: Span={dSpanMM:F1}mm | Root={dRootChordMM:F1}mm | Tip={dTipChordMM:F1}mm | " +
                $"Twist={dTipTwistDeg:F2}° (pivô 25% c) | Sweep={dWingSweepDeg:F2}° | Dihedral={dWingDihedralDeg:F2}° | " +
                $"Chamfer={dTipChanferDeg:F2}° | Casca={dShellThicknessMM:F2}mm | ExportVoxels={bExportVoxelMesh} | " +
                $"Elíptica={bEllipticalTransition} | PontaCilíndrica={bRoundedTipCap} ({dTipCapRadiusMM:F1}mm) | " +
                $"SeçõesCustom={(bUsingCustomSections ? customSections!.Count : 0)}");

            List<LocalFrame> lFrames;
            List<double> lChords;
            List<double> lThicknessScales;

            if (bUsingCustomSections)
            {
                var ordered = customSections!.OrderBy(s => s.ZMM).ToList();
                lFrames = new List<LocalFrame>(ordered.Count);
                lChords = new List<double>(ordered.Count);
                lThicknessScales = new List<double>(ordered.Count);
                double maxZ = Math.Max(1.0, ordered[^1].ZMM);
                double basePivotX = dRootChordMM * (0.5 + TwistPivotChordFraction);

                for (int i = 0; i < ordered.Count; i++)
                {
                    var s = ordered[i];
                    double t = Math.Clamp(s.ZMM / maxZ, 0.0, 1.0);
                    Vector3 vecPos = new(
                        (float)(basePivotX + s.SweepXMM),
                        (float)s.DihedralYMM,
                        (float)s.ZMM);

                    LocalFrame oFrame = new LocalFrame()
                        .oTranslate(vecPos)
                        .oRotate((float)(s.TwistDeg * Math.PI / 180.0), Vector3.UnitZ);

                    if (Math.Abs(dTipChanferDeg) > 1e-4)
                    {
                        double tauChanfer = Math.Clamp((t - TipTransitionStart) / (1.0 - TipTransitionStart), 0.0, 1.0);
                        double sChanfer = tauChanfer * tauChanfer * (3.0 - 2.0 * tauChanfer);
                        if (sChanfer > 1e-5)
                        {
                            oFrame = oFrame.oRotate((float)(dTipChanferDeg * sChanfer * Math.PI / 180.0), Vector3.UnitX);
                        }
                    }

                    lFrames.Add(oFrame);
                    lChords.Add(Math.Max(2.0, s.ChordMM));
                    lThicknessScales.Add(Math.Clamp(s.ThicknessScale, 0.05, 5.0));
                }
            }
            else
            {
                lFrames = CreateSectionsWing(
                    dSpanMM,
                    dWingSweepDeg,
                    dWingDihedralDeg,
                    dTipTwistDeg,
                    dRootChordMM,
                    dTargetSectionSizeMM,
                    dTipChanferDeg,
                    dTipChordMM,
                    bEllipticalTransition,
                    out lChords);
                lThicknessScales = Enumerable.Repeat(1.0, lFrames.Count).ToList();
            }

            Mesh oMesh = new();
            List<List<Vector3>> sections = new(lFrames.Count + 14);

            for (int i = 0; i < lFrames.Count; i++)
            {
                List<Vector3> section = avecBuildSection(coordinates, lFrames[i], lChords[i], lThicknessScales[i]);
                sections.Add(section);
            }

            // Ponta cilíndrica / elíptica 3D (fechamento tipo meio-cilindro contínuo entre extradorso e intradorso)
            if (bRoundedTipCap && dTipCapRadiusMM > 0.5 && lFrames.Count >= 2)
            {
                const int nCapRings = 12;
                LocalFrame oTipFrame = lFrames[^1];
                double dLastChord = lChords[^1];
                double dLastThickScale = lThicknessScales[^1];

                // Calcula a direção tangente da envergadura na ponta para continuar enflechamento e diedro sem quina
                Vector3 vecTipPos = lFrames[^1].vecGetPosition();
                Vector3 vecPrevPos = lFrames[^2].vecGetPosition();
                float dzStep = Math.Max(1e-3f, vecTipPos.Z - vecPrevPos.Z);
                float dXdZ = (vecTipPos.X - vecPrevPos.X) / dzStep;
                float dYdZ = (vecTipPos.Y - vecPrevPos.Y) / dzStep;

                for (int k = 1; k <= nCapRings; k++)
                {
                    double phi = (0.5 * Math.PI) * ((double)k / nCapRings);
                    double sinPhi = Math.Sin(phi);
                    double cosPhi = Math.Cos(phi);

                    // Avança suavemente na direção da ponta enquanto fecha a espessura em arco circular cos(phi)
                    float capZOffset = (float)(dTipCapRadiusMM * sinPhi);
                    Vector3 vecCapDelta = new(dXdZ * capZOffset, dYdZ * capZOffset, capZOffset);
                    double capThickScale = dLastThickScale * Math.Max(0.012, cosPhi);

                    LocalFrame oCapFrame = oTipFrame.oTranslate(vecCapDelta);
                    List<Vector3> capSection = avecBuildSection(coordinates, oCapFrame, dLastChord, capThickScale);
                    sections.Add(capSection);
                }
            }

            for (int i = 1; i < sections.Count; i++)
            {
                AddLoftBetweenSections(ref oMesh, sections[i - 1], sections[i]);
            }

            if (sections.Count >= 2)
            {
                AddCap(ref oMesh, sections[0], bFlip: true);
                AddCap(ref oMesh, sections[sections.Count - 1], bFlip: false);
            }

            Console.WriteLine(
                $"[3D] Malha base construída: {lFrames.Count} estações, " +
                $"{oMesh.nVertexCount()} vértices, {oMesh.nTriangleCount()} triângulos.");

            Voxels voxels = new(oMesh);

            // Estrutura interna: geração de casca oca via offset volumétrico negativo
            bool bHasHollowShell = dShellThicknessMM > 0.0;
            if (bHasHollowShell)
            {
                Console.WriteLine($"[3D] Aplicando estrutura interna (casca oca de {dShellThicknessMM:F2} mm)...");
                Voxels voxInnerCavity = voxels.voxOffset(-(float)dShellThicknessMM);
                voxels = voxels.voxBoolSubtract(voxInnerCavity);
            }

            // Exportação STL: versão de Voxels (Marching Cubes) ou malha poligonal direta
            if (bExportVoxelMesh || bHasHollowShell)
            {
                string reason = bExportVoxelMesh
                    ? "opção de exportação de voxels ativada"
                    : "estrutura de casca oca volumétrica ativa";
                Console.WriteLine($"[3D] Extraindo malha final a partir do campo de voxels ({reason})...");
                Mesh oVoxelMesh = new(voxels);
                oVoxelMesh.SaveToStlFile(outputStlPath);
                Console.WriteLine(
                    $"[3D] STL (Voxels) salvo em: {outputStlPath} " +
                    $"({oVoxelMesh.nVertexCount()} vértices, {oVoxelMesh.nTriangleCount()} triângulos)");
            }
            else
            {
                oMesh.SaveToStlFile(outputStlPath);
                Console.WriteLine($"[3D] STL (Malha Loft) salvo em: {outputStlPath}");
            }

            Library.oViewer().Add(voxels, 0);

            sw.Stop();
            Console.WriteLine($"[3D] Asa gerada com sucesso em {sw.Elapsed.TotalSeconds:F2}s.");
        }

        public static List<LocalFrame> CreateSectionsWing(
            double dWingSpanMM,
            double dWingSweepDeg,
            double dWingDihedralDeg,
            double dWingRotationDeg,
            double dRootChordMM,
            double dTargetSectionSizeMM,
            double dTipChanferDeg,
            double dTipChordMM,
            bool bEllipticalTransition,
            out List<double> lChords)
        {
            const int nMinSections = 8;
            const int nMaxSections = 500;
            int nSections = Math.Clamp(
                (int)Math.Round(dWingSpanMM / Math.Max(1.0, dTargetSectionSizeMM)),
                nMinSections,
                nMaxSections);

            double sweepTan = Math.Tan(dWingSweepDeg * Math.PI / 180.0);
            double dihedralTan = Math.Tan(dWingDihedralDeg * Math.PI / 180.0);
            double basePivotX = dRootChordMM * (0.5 + TwistPivotChordFraction);

            // Espinha dorsal B-Spline (ControlPointSpline do ShapeKernel) para interpolação não-linear suave
            ControlPointSpline? oSpineSpline = null;
            if (bEllipticalTransition)
            {
                double[] ctrlT = { 0.0, 0.25, 0.50, 0.75, 1.0 };
                List<Vector3> aCtrlPts = new(ctrlT.Length);
                foreach (double ct in ctrlT)
                {
                    double z = ct * dWingSpanMM;
                    float x = (float)(basePivotX + sweepTan * z);
                    float y = (float)(dihedralTan * z);
                    aCtrlPts.Add(new Vector3(x, y, (float)z));
                }
                oSpineSpline = new ControlPointSpline(aCtrlPts, nDegree: 2, ControlPointSpline.EEnds.OPEN);
            }

            string modeDesc = bEllipticalTransition
                ? "Não-linear (Agrupamento Cosseno + B-Spline + Transição Elíptica Suave)"
                : "Linear Trapezoidal";
            Console.WriteLine($"[3D] Discretização: {nSections} segmentos | Modo: {modeDesc}");

            List<LocalFrame> lFrames = new(nSections + 1);
            lChords = new List<double>(nSections + 1);

            const double ellipEccentricity = 0.80;
            double sRoot = Math.Sqrt(1.0 - ellipEccentricity * ellipEccentricity); // 0.60

            for (int i = 0; i <= nSections; i++)
            {
                double u = (double)i / nSections;

                // Agrupamento não-linear (cosseno híbrido) concentrando mais seções na transição da ponta
                double t = bEllipticalTransition
                    ? 0.5 * u + 0.5 * Math.Sin(0.5 * Math.PI * u)
                    : u;

                double chord;
                double twistDeg;
                Vector3 vecSpinePos;

                if (bEllipticalTransition)
                {
                    // Distribuição elíptica truncada (e=0.80): derivada finita na ponta, eliminando estrangulamento/defeito
                    double ellipFactor = (Math.Sqrt(1.0 - Math.Pow(ellipEccentricity * t, 2.0)) - sRoot) / (1.0 - sRoot);
                    chord = dTipChordMM + (dRootChordMM - dTipChordMM) * ellipFactor;

                    // Interpolação não-linear Hermite (Smoothstep) para a torção aerodinâmica
                    double sTwist = 0.4 * t + 0.6 * (t * t * (3.0 - 2.0 * t));
                    twistDeg = dWingRotationDeg * sTwist;

                    vecSpinePos = oSpineSpline!.vecGetPointAt((float)t);
                }
                else
                {
                    chord = dRootChordMM + (dTipChordMM - dRootChordMM) * t;
                    twistDeg = dWingRotationDeg * t;
                    double lengthZ = t * dWingSpanMM;
                    vecSpinePos = new Vector3(
                        (float)(basePivotX + sweepTan * lengthZ),
                        (float)(dihedralTan * lengthZ),
                        (float)lengthZ);
                }

                lChords.Add(chord);

                LocalFrame oFrame = new LocalFrame()
                    .oTranslate(vecSpinePos)
                    .oRotate((float)(twistDeg * Math.PI / 180.0), Vector3.UnitZ);

                if (Math.Abs(dTipChanferDeg) > 1e-4)
                {
                    double tauChanfer = bEllipticalTransition
                        ? Math.Clamp((t - TipTransitionStart) / (1.0 - TipTransitionStart), 0.0, 1.0)
                        : (i == nSections ? 1.0 : 0.0);
                    double sChanfer = tauChanfer * tauChanfer * (3.0 - 2.0 * tauChanfer);
                    if (sChanfer > 1e-5)
                    {
                        oFrame = oFrame.oRotate((float)(dTipChanferDeg * sChanfer * Math.PI / 180.0), Vector3.UnitX);
                    }
                }

                lFrames.Add(oFrame);
            }

            return lFrames;
        }

        static List<Vector3> avecBuildSection(
            List<Coordinate> coordinates,
            LocalFrame oFrame,
            double dChordMM,
            double dThicknessScale = 1.0)
        {
            int n = coordinates.Count;
            List<Vector3> avec = new(n);
            float fChord = (float)dChordMM;
            float fThickScale = (float)dThicknessScale;
            Vector3 pivot = oFrame.vecGetPosition();
            Vector3 lx = oFrame.vecGetLocalX();
            Vector3 ly = oFrame.vecGetLocalY();

            for (int i = 0; i < n; i++)
            {
                var c = coordinates[i];
                var cMirror = coordinates[n - 1 - i];
                double yCamber = 0.5 * (c.Y + cMirror.Y);
                double yThick = c.Y - yCamber;
                double yScaled = yCamber + yThick * fThickScale;

                float xRel = ((float)c.X - TwistPivotChordFraction) * fChord;
                float yRel = (float)yScaled * fChord;
                avec.Add(pivot + xRel * lx + yRel * ly);
            }
            return avec;
        }

        static void AddTriangleSafe(ref Mesh oMesh, Vector3 a, Vector3 b, Vector3 c)
        {
            if (Vector3.Cross(b - a, c - a).LengthSquared() <= 1e-12f)
            {
                return;
            }
            oMesh.nAddTriangle(a, b, c);
        }

        static void AddLoftBetweenSections(ref Mesh oMesh, List<Vector3> secA, List<Vector3> secB)
        {
            int n = Math.Min(secA.Count, secB.Count);
            if (n < 2)
            {
                return;
            }

            for (int i = 0; i < n - 1; i++)
            {
                AddTriangleSafe(ref oMesh, secA[i], secA[i + 1], secB[i + 1]);
                AddTriangleSafe(ref oMesh, secA[i], secB[i + 1], secB[i]);
            }

            // Fecha o bordo de fuga caso o perfil .dat possua espessura finita (primeiro != último ponto)
            if (Vector3.DistanceSquared(secA[n - 1], secA[0]) > 1e-10f ||
                Vector3.DistanceSquared(secB[n - 1], secB[0]) > 1e-10f)
            {
                AddTriangleSafe(ref oMesh, secA[n - 1], secA[0], secB[0]);
                AddTriangleSafe(ref oMesh, secA[n - 1], secB[0], secB[n - 1]);
            }
        }

        static void AddCap(ref Mesh oMesh, List<Vector3> section, bool bFlip)
        {
            int n = section.Count;
            if (n < 3)
            {
                return;
            }

            Vector3 vecCentroid = Vector3.Zero;
            foreach (var vec in section)
            {
                vecCentroid += vec;
            }
            vecCentroid /= n;

            for (int i = 0; i < n - 1; i++)
            {
                if (!bFlip)
                    AddTriangleSafe(ref oMesh, vecCentroid, section[i], section[i + 1]);
                else
                    AddTriangleSafe(ref oMesh, vecCentroid, section[i + 1], section[i]);
            }

            // Fecha a tampa no bordo de fuga caso o último ponto não coincida com o primeiro
            if (Vector3.DistanceSquared(section[n - 1], section[0]) > 1e-10f)
            {
                if (!bFlip)
                    AddTriangleSafe(ref oMesh, vecCentroid, section[n - 1], section[0]);
                else
                    AddTriangleSafe(ref oMesh, vecCentroid, section[0], section[n - 1]);
            }
        }
    }
}