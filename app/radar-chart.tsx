"use client";

import { useEffect, useRef } from "react";

type RadarAxis = {
  rank: number;
  label: string;
  candidate_score: number;
  market_score: number;
};

function compactLabel(label: string, narrow: boolean) {
  const limit = narrow ? 7 : 11;
  return label.length > limit ? `${label.slice(0, limit)}…` : label;
}

export function RadarChart({ axes, label }: { axes: RadarAxis[]; label: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || axes.length < 3) return;
    const context = canvas.getContext("2d");
    if (!context) return;

    const draw = () => {
      const rect = canvas.getBoundingClientRect();
      const ratio = window.devicePixelRatio || 1;
      canvas.width = rect.width * ratio;
      canvas.height = rect.height * ratio;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      context.clearRect(0, 0, rect.width, rect.height);

      const narrow = rect.width < 480;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const radius = Math.min(rect.width, rect.height) * (narrow ? 0.27 : 0.31);
      const angleFor = (index: number) => -Math.PI / 2 + (Math.PI * 2 * index) / axes.length;
      const point = (index: number, value: number) => ({
        x: centerX + Math.cos(angleFor(index)) * radius * value,
        y: centerY + Math.sin(angleFor(index)) * radius * value,
      });

      const polygon = (values: number[]) => {
        context.beginPath();
        values.forEach((value, index) => {
          const next = point(index, value / 100);
          if (index === 0) context.moveTo(next.x, next.y);
          else context.lineTo(next.x, next.y);
        });
        context.closePath();
      };

      context.lineJoin = "round";
      [0.2, 0.4, 0.6, 0.8, 1].forEach((level) => {
        polygon(axes.map(() => level * 100));
        context.strokeStyle = level === 1 ? "#75839a" : "#d7dfec";
        context.lineWidth = level === 1 ? 1.5 : 1;
        context.setLineDash(level === 1 ? [5, 5] : []);
        context.stroke();
      });

      context.setLineDash([]);
      axes.forEach((_, index) => {
        const end = point(index, 1);
        context.beginPath();
        context.moveTo(centerX, centerY);
        context.lineTo(end.x, end.y);
        context.strokeStyle = "#e3e8f1";
        context.lineWidth = 1;
        context.stroke();
      });

      polygon(axes.map((axis) => axis.market_score));
      context.strokeStyle = "#2457ff";
      context.lineWidth = 2;
      context.setLineDash([7, 5]);
      context.stroke();

      context.setLineDash([]);
      polygon(axes.map((axis) => axis.candidate_score));
      const fill = context.createLinearGradient(0, centerY - radius, 0, centerY + radius);
      fill.addColorStop(0, "rgba(24, 169, 121, .30)");
      fill.addColorStop(1, "rgba(24, 169, 121, .08)");
      context.fillStyle = fill;
      context.fill();
      context.strokeStyle = "#18a979";
      context.lineWidth = 3;
      context.stroke();

      axes.forEach((axis, index) => {
        const valuePoint = point(index, axis.candidate_score / 100);
        const labelPoint = point(index, narrow ? 1.34 : 1.28);
        const cosine = Math.cos(angleFor(index));

        context.beginPath();
        context.arc(valuePoint.x, valuePoint.y, 4, 0, Math.PI * 2);
        context.fillStyle = "#ff6b35";
        context.fill();
        context.strokeStyle = "#ffffff";
        context.lineWidth = 2;
        context.stroke();

        context.font = `${narrow ? 10 : 11}px "PingFang SC", "Microsoft YaHei", sans-serif`;
        context.fillStyle = "#172033";
        context.textAlign = Math.abs(cosine) < 0.2 ? "center" : cosine > 0 ? "left" : "right";
        context.textBaseline = "middle";
        context.fillText(compactLabel(axis.label, narrow), labelPoint.x, labelPoint.y - 6);
        context.font = `600 ${narrow ? 9 : 10}px SFMono-Regular, Consolas, monospace`;
        context.fillStyle = "#647087";
        context.fillText(`市场 ${axis.market_score} · 证据 ${axis.candidate_score}`, labelPoint.x, labelPoint.y + 9);
      });
    };

    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(canvas);
    return () => observer.disconnect();
  }, [axes]);

  return (
    <canvas
      ref={canvasRef}
      className="radar-canvas"
      role="img"
      aria-label={`${label} 雷达图，对比 ${axes.length} 个能力轴的岗位市场信号与简历证据覆盖`}
    />
  );
}
