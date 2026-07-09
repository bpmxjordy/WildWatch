"use client";

import { motion } from "framer-motion";

interface ActivityClockProps {
  /** 24 values, index = local hour, value = detection count. */
  hourly: number[];
  total: number;
  periodLabel: string;
}

const SIZE = 300;
const CENTER = SIZE / 2;
const INNER_R = 58;
const OUTER_R = 128;
const BAR_SPAN = OUTER_R - INNER_R;

function isNight(h: number): boolean {
  return h < 6 || h >= 19;
}

/** Polar → cartesian, midnight at top, clockwise. */
function polar(hour: number, radius: number): [number, number] {
  const angle = (hour / 24) * Math.PI * 2 - Math.PI / 2;
  return [CENTER + radius * Math.cos(angle), CENTER + radius * Math.sin(angle)];
}

export default function ActivityClock({ hourly, total, periodLabel }: ActivityClockProps) {
  const max = Math.max(...hourly, 1);
  const peakIdx = hourly.indexOf(Math.max(...hourly));

  const cardinals = [
    { hour: 0, label: "12a" },
    { hour: 6, label: "6a" },
    { hour: 12, label: "12p" },
    { hour: 18, label: "6p" },
  ];

  return (
    <div className="relative" style={{ width: SIZE, height: SIZE }}>
      {/* Rotating radar sweep */}
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background:
            "conic-gradient(from 0deg, transparent 0deg, transparent 300deg, rgba(106,155,90,0.18) 350deg, rgba(125,184,106,0.32) 360deg)",
          animation: "explore-sweep 6s linear infinite",
          maskImage:
            "radial-gradient(circle, transparent 38%, black 39%, black 86%, transparent 87%)",
          WebkitMaskImage:
            "radial-gradient(circle, transparent 38%, black 39%, black 86%, transparent 87%)",
        }}
      />

      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        width={SIZE}
        height={SIZE}
        className="relative"
      >
        {/* Concentric guide rings */}
        {[0.5, 1].map((f) => (
          <circle
            key={f}
            cx={CENTER}
            cy={CENTER}
            r={INNER_R + BAR_SPAN * f}
            fill="none"
            stroke="rgba(180,206,170,0.10)"
            strokeWidth={1}
          />
        ))}
        <circle
          cx={CENTER}
          cy={CENTER}
          r={INNER_R}
          fill="none"
          stroke="rgba(180,206,170,0.18)"
          strokeWidth={1}
        />

        {/* Day arc (6a–7p) subtle highlight band */}
        <path
          d={describeArc(6, 19, INNER_R - 8)}
          fill="none"
          stroke="rgba(212,180,90,0.22)"
          strokeWidth={2.5}
          strokeLinecap="round"
        />

        {/* Hour bars */}
        {hourly.map((v, h) => {
          const len = (v / max) * BAR_SPAN;
          const angle = (h / 24) * 360;
          const night = isNight(h);
          const isPeak = h === peakIdx && v > 0;
          const barW = 5.5;

          const color = isPeak
            ? "#c9e8b8"
            : night
              ? "#3f7d84"
              : "#7db86a";

          return (
            <g key={h} transform={`rotate(${angle} ${CENTER} ${CENTER})`}>
              <motion.rect
                x={CENTER - barW / 2}
                width={barW}
                rx={barW / 2}
                initial={{ height: 0, y: CENTER - INNER_R }}
                animate={{ height: len, y: CENTER - INNER_R - len }}
                transition={{
                  duration: 0.7,
                  delay: h * 0.012,
                  ease: [0.16, 1, 0.3, 1],
                }}
                fill={color}
                style={{
                  filter: isPeak
                    ? "drop-shadow(0 0 6px rgba(201,232,184,0.9))"
                    : v > 0
                      ? `drop-shadow(0 0 3px ${color}66)`
                      : "none",
                }}
              />
            </g>
          );
        })}

        {/* Cardinal hour markers */}
        {cardinals.map(({ hour, label }) => {
          const [x, y] = polar(hour, OUTER_R + 16);
          return (
            <text
              key={label}
              x={x}
              y={y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="fill-[#8fb085] font-mono"
              style={{ fontSize: 10, letterSpacing: "0.08em" }}
            >
              {label}
            </text>
          );
        })}
      </svg>

      {/* Center readout */}
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <motion.span
          key={total}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4 }}
          className="font-serif text-[38px] font-medium leading-none text-[#eef5e9]"
        >
          {total.toLocaleString()}
        </motion.span>
        <span className="mt-1 font-mono text-[9px] uppercase tracking-[0.2em] text-[#8fb085]">
          detections
        </span>
        <span className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-[#5f7d63]">
          {periodLabel}
        </span>
      </div>
    </div>
  );
}

function describeArc(startHour: number, endHour: number, r: number): string {
  const [x0, y0] = polar(startHour, r);
  const [x1, y1] = polar(endHour, r);
  const large = endHour - startHour > 12 ? 1 : 0;
  return `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}`;
}
