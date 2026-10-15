/**
 * ProgressChart — line chart sederhana (SVG) untuk tren WCPM/Accuracy (§33).
 * Tanpa dependensi eksternal. Sertakan tabel data untuk aksesibilitas.
 */
export function ProgressChart({
  points,
  labels,
  color = "#3B82F6",
  unit = "",
  height = 180,
  milestones,
}: {
  points: number[];
  labels: string[];
  color?: string;
  unit?: string;
  height?: number;
  milestones?: { index: number; label: string }[];
}) {
  const width = 520;
  const pad = { top: 16, right: 16, bottom: 32, left: 40 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;

  const max = Math.max(...points, 1) * 1.15;
  const min = 0;
  const x = (i: number) => pad.left + (points.length === 1 ? innerW / 2 : (i / (points.length - 1)) * innerW);
  const y = (v: number) => pad.top + innerH - ((v - min) / (max - min)) * innerH;

  const path = points.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(p)}`).join(" ");

  return (
    <figure className="w-full">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Grafik progres">
        {/* grid */}
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <line
            key={t}
            x1={pad.left}
            x2={width - pad.right}
            y1={pad.top + t * innerH}
            y2={pad.top + t * innerH}
            stroke="#E2E8F0"
            strokeWidth={1}
          />
        ))}

        {/* milestone bands */}
        {milestones?.map((m) => (
          <g key={m.label}>
            <line
              x1={x(m.index)}
              x2={x(m.index)}
              y1={pad.top}
              y2={pad.top + innerH}
              stroke="#CBD5E1"
              strokeDasharray="4 4"
            />
            <text x={x(m.index)} y={height - 6} textAnchor="middle" className="fill-slate-400 text-[10px]">
              {m.label}
            </text>
          </g>
        ))}

        {/* line */}
        <path d={path} fill="none" stroke={color} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />

        {/* points */}
        {points.map((p, i) => (
          <g key={i}>
            <circle cx={x(i)} cy={y(p)} r={i === points.length - 1 ? 5 : 4} fill={color} />
            <text x={x(i)} y={y(p) - 10} textAnchor="middle" className="fill-slate-600 text-[10px] font-semibold">
              {p}
              {unit}
            </text>
            <text x={x(i)} y={height - 16} textAnchor="middle" className="fill-slate-400 text-[10px]">
              {labels[i]}
            </text>
          </g>
        ))}
      </svg>

      {/* tabel alternatif (aksesibilitas) */}
      <figcaption className="sr-only">
        <table>
          <thead>
            <tr><th>Asesmen</th><th>Nilai</th></tr>
          </thead>
          <tbody>
            {points.map((p, i) => (
              <tr key={i}><td>{labels[i]}</td><td>{p}{unit}</td></tr>
            ))}
          </tbody>
        </table>
      </figcaption>
    </figure>
  );
}
