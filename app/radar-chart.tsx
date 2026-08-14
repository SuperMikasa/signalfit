"use client";

import { useEffect, useRef } from "react";

type RadarAxis = { rank: number; label: string; candidate_score: number };

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

      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const radius = Math.min(rect.width, rect.height) * 0.34;
      const angleFor = (index: number) => -Math.PI / 2 + (Math.PI * 2 * index) / axes.length;
      const point = (index: number, value: number) => ({
        x: centerX + Math.cos(angleFor(index)) * radius * value,
        y: centerY + Math.sin(angleFor(index)) * radius * value,
      });

      context.lineJoin = "round";
      [0.2, 0.4, 0.6, 0.8, 1].forEach((level) => {
        context.beginPath();
        axes.forEach((_, index) => {
          const next = point(index, level);
          if (index === 0) context.moveTo(next.x, next.y);
          else context.lineTo(next.x, next.y);
        });
        context.closePath();
        context.strokeStyle = level === 1 ? "#6f7d96" : "#d7dfec";
        context.lineWidth = level === 1 ? 1.5 : 1;
        context.setLineDash(level === 1 ? [6, 6] : []);
        context.stroke();
      });

      context.setLineDash([]);
      axes.forEach((_, index) => {
        const end = point(index, 1);
        context.beginPath();
        context.moveTo(centerX, centerY);
        context.lineTo(end.x, end.y);
        context.strokeStyle = "#e3e8f1";
        context.stroke();
      });

      context.beginPath();
      axes.forEach((axis, index) => {
        const next = point(index, axis.candidate_score / 100);
        if (index === 0) context.moveTo(next.x, next.y);
        else context.lineTo(next.x, next.y);
      });
      context.closePath();
      const fill = context.createLinearGradient(0, centerY - radius, 0, centerY + radius);
      fill.addColorStop(0, "rgba(36, 87, 255, .35)");
      fill.addColorStop(1, "rgba(36, 87, 255, .10)");
      context.fillStyle = fill;
      context.fill();
      context.strokeStyle = "#2457ff";
      context.lineWidth = 3;
      context.stroke();

      axes.forEach((axis, index) => {
        const valuePoint = point(index, axis.candidate_score / 100);
        const labelPoint = point(index, 1.15);
        context.beginPath();
        context.arc(valuePoint.x, valuePoint.y, 4, 0, Math.PI * 2);
        context.fillStyle = "#ff6b35";
        context.fill();
        context.font = "600 11px SFMono-Regular, Consolas, monospace";
        context.fillStyle = "#172033";
        context.textAlign = "center";
        context.textBaseline = "middle";
        context.fillText(String(axis.rank).padStart(2, "0"), labelPoint.x, labelPoint.y);
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
      aria-label={`${label} 简历证据雷达图，包含 ${axes.length} 个能力轴`}
    />
  );
}
