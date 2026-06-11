// 占位技术图纸 —— 风格化减速机剖面（细线、单色），让标注框有承载物。
// 真实接入时替换为 <img>/PDF/Canvas 渲染的图纸位图。
export function DrawingArtwork() {
  const stroke = "#334155";
  return (
    <svg
      viewBox="0 0 1000 700"
      className="h-full w-full"
      preserveAspectRatio="xMidYMid meet"
    >
      {/* 图框 */}
      <rect
        x="20"
        y="20"
        width="960"
        height="660"
        fill="none"
        stroke={stroke}
        strokeWidth="2"
      />
      <rect
        x="34"
        y="34"
        width="932"
        height="632"
        fill="none"
        stroke="#94A3B8"
        strokeWidth="1"
      />

      <g stroke={stroke} strokeWidth="1.4" fill="none">
        {/* 箱体 */}
        <rect x="200" y="250" width="500" height="300" rx="10" />
        {/* 输入轴 */}
        <line x1="80" y1="150" x2="320" y2="150" />
        <line x1="80" y1="172" x2="320" y2="172" />
        <rect x="300" y="140" width="40" height="44" fill="#F1F5F9" />
        {/* 一级斜齿轮 */}
        <circle cx="430" cy="300" r="78" fill="#F8FAFC" />
        <circle cx="430" cy="300" r="60" />
        <circle cx="430" cy="300" r="14" />
        {Array.from({ length: 24 }).map((_, i) => {
          const a = (i / 24) * Math.PI * 2;
          return (
            <line
              key={i}
              x1={430 + Math.cos(a) * 70}
              y1={300 + Math.sin(a) * 70}
              x2={430 + Math.cos(a) * 80}
              y2={300 + Math.sin(a) * 80}
            />
          );
        })}
        {/* 轴承 6208 */}
        <rect x="600" y="150" width="120" height="44" fill="#F1F5F9" />
        <line x1="600" y1="172" x2="720" y2="172" />
        {/* 输出轴 */}
        <line x1="80" y1="500" x2="300" y2="500" />
        <line x1="80" y1="522" x2="300" y2="522" />
        {/* 油封 */}
        <rect x="150" y="490" width="34" height="44" fill="#F1F5F9" />
        {/* 通气塞 */}
        <line x1="450" y1="250" x2="450" y2="210" />
        <circle cx="450" cy="200" r="12" fill="#F1F5F9" />
        {/* 油标 */}
        <rect x="650" y="470" width="40" height="60" rx="6" fill="#F8FAFC" />
        {/* 调整垫片 */}
        <rect x="710" y="280" width="22" height="40" fill="#F1F5F9" />
        {/* 中心线 */}
        <g stroke="#CBD5E1" strokeDasharray="14 4 3 4" strokeWidth="0.8">
          <line x1="60" y1="161" x2="780" y2="161" />
          <line x1="60" y1="511" x2="340" y2="511" />
        </g>
      </g>

      {/* 标题栏 */}
      <g>
        <rect
          x="700"
          y="590"
          width="266"
          height="72"
          fill="#FFFFFF"
          stroke={stroke}
          strokeWidth="1"
        />
        <line x1="700" y1="614" x2="966" y2="614" stroke="#94A3B8" />
        <line x1="820" y1="590" x2="820" y2="662" stroke="#94A3B8" />
        <text x="710" y="608" fontSize="13" fill="#475569" fontWeight="600">
          减速机总装配图
        </text>
        <text x="710" y="636" fontSize="11" fill="#64748B">
          图号 ZJ-200
        </text>
        <text x="710" y="652" fontSize="11" fill="#64748B">
          比例 1:2
        </text>
        <text x="830" y="636" fontSize="11" fill="#64748B">
          单位 mm
        </text>
        <text x="830" y="652" fontSize="11" fill="#64748B">
          A3
        </text>
      </g>
    </svg>
  );
}
