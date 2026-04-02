"use client";

import { useEffect, useMemo, useRef } from "react";

import type { RunResult } from "@/lib/types";

interface SumoNetworkViewerProps {
  result: RunResult | null;
  step?: number;
}

interface Bounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

function computeBounds(
  nodes: Array<{ x: number; y: number }>,
  edges: Array<{ x1: number; y1: number; x2: number; y2: number }>,
  frames: Array<{ vehicles?: Array<{ x: number; y: number }> }>,
): Bounds | null {
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;

  const include = (x: number, y: number) => {
    const px = Number(x);
    const py = Number(y);
    if (!Number.isFinite(px) || !Number.isFinite(py)) return;
    minX = Math.min(minX, px);
    maxX = Math.max(maxX, px);
    minY = Math.min(minY, py);
    maxY = Math.max(maxY, py);
  };

  nodes.forEach((node) => include(node.x, node.y));
  edges.forEach((edge) => {
    include(edge.x1, edge.y1);
    include(edge.x2, edge.y2);
  });
  frames.forEach((frame) => {
    (frame.vehicles ?? []).forEach((vehicle) => include(vehicle.x, vehicle.y));
  });

  if (!Number.isFinite(minX) || !Number.isFinite(minY) || !Number.isFinite(maxX) || !Number.isFinite(maxY)) {
    return null;
  }

  const spanX = Math.max(1, maxX - minX);
  const spanY = Math.max(1, maxY - minY);
  const marginX = Math.max(16, spanX * 0.06);
  const marginY = Math.max(16, spanY * 0.06);

  return {
    minX: minX - marginX,
    maxX: maxX + marginX,
    minY: minY - marginY,
    maxY: maxY + marginY,
  };
}

export function SumoNetworkViewer({ result, step = 0 }: SumoNetworkViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const visualization = result?.backend?.visualization;
  const nodes = visualization?.nodes ?? [];
  const edges = visualization?.edges ?? [];
  const flows = visualization?.flows ?? [];
  const runtimeFrames = result?.backend?.runtime?.trace?.frames ?? [];

  const currentFrame = useMemo(() => {
    if (!runtimeFrames.length) return null;
    const index = Math.max(0, Math.min(step, runtimeFrames.length - 1));
    return runtimeFrames[index] ?? null;
  }, [runtimeFrames, step]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#2f7d32";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "rgba(0, 0, 0, 0.08)";
    for (let x = 0; x < canvas.width; x += 80) {
      for (let y = 0; y < canvas.height; y += 80) {
        ctx.fillRect(x + 18, y + 12, 40, 30);
      }
    }

    if (nodes.length === 0 || edges.length === 0) {
      ctx.fillStyle = "#31405b";
      ctx.font = "14px IBM Plex Mono";
      ctx.textAlign = "center";
      ctx.fillText(
        "Run a simulation with SUMO backend to view generated network geometry.",
        canvas.width / 2,
        canvas.height / 2,
      );
      return;
    }

    const bounds = computeBounds(nodes, edges, runtimeFrames);
    if (!bounds) return;

    const { minX, maxX, minY, maxY } = bounds;
    const pad = 14;
    const spanX = Math.max(1, maxX - minX);
    const spanY = Math.max(1, maxY - minY);
    const scale = Math.min((canvas.width - pad * 2) / spanX, (canvas.height - pad * 2) / spanY);
    const offsetX = (canvas.width - spanX * scale) / 2;
    const offsetY = (canvas.height - spanY * scale) / 2;

    const project = (x: number, y: number) => ({
      x: offsetX + (x - minX) * scale,
      y: offsetY + (y - minY) * scale,
    });

    const edgeMidpoints: Record<string, { x: number; y: number }> = {};

    edges.forEach((edge) => {
      const from = project(edge.x1, edge.y1);
      const to = project(edge.x2, edge.y2);
      const laneCount = Math.max(1, Number(edge.lanes) || 1);
      const roadWidth = Math.max(12, Math.min(34, laneCount * 6.4));

      ctx.strokeStyle = "rgba(31, 41, 55, 0.98)";
      ctx.lineCap = "round";
      ctx.lineWidth = roadWidth;
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();

      ctx.strokeStyle = "rgba(255, 255, 255, 0.75)";
      ctx.lineWidth = Math.max(2.4, roadWidth * 0.3);
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();

      if (roadWidth >= 11) {
        ctx.strokeStyle = "rgba(255, 255, 255, 0.9)";
        ctx.lineWidth = Math.max(1.2, roadWidth * 0.12);
        ctx.setLineDash([7, 7]);
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      edgeMidpoints[edge.id] = { x: (from.x + to.x) / 2, y: (from.y + to.y) / 2 };
    });

    if (currentFrame) {
      (currentFrame.vehicles ?? []).forEach((vehicle) => {
        const point = project(Number(vehicle.x) || 0, Number(vehicle.y) || 0);
        const speed = Number(vehicle.speed) || 0;
        const angle = Number(vehicle.angle) || 0;
        const carLength = 10 + Math.min(4, speed / 3);
        const carWidth = 5 + Math.min(2, speed / 6);
        const angleRad = ((90 - angle) * Math.PI) / 180;

        ctx.save();
        ctx.translate(point.x, point.y);
        ctx.rotate(angleRad);
        ctx.fillStyle = speed < 0.2 ? "#f97316" : "#2563eb";
        ctx.fillRect(-carLength / 2, -carWidth / 2, carLength, carWidth);
        ctx.strokeStyle = "rgba(0,0,0,0.35)";
        ctx.lineWidth = 0.9;
        ctx.strokeRect(-carLength / 2, -carWidth / 2, carLength, carWidth);
        ctx.restore();
      });
    } else {
      flows.slice(0, 30).forEach((flow) => {
        const origin = edgeMidpoints[flow.from];
        if (!origin) return;
        const intensity = Math.max(0.1, Math.min(1.0, Number(flow.probability) || 0.1));
        ctx.fillStyle = `rgba(222, 107, 26, ${0.35 + intensity * 0.55})`;
        ctx.beginPath();
        ctx.arc(origin.x, origin.y, 2 + intensity * 2.5, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    nodes.forEach((node) => {
      const point = project(node.x, node.y);
      const isTrafficLight = node.type === "traffic_light";
      const radius = isTrafficLight ? 6.1 : 4.2;

      ctx.fillStyle = isTrafficLight ? "rgba(0, 133, 121, 0.95)" : "rgba(33, 100, 212, 0.85)";
      ctx.beginPath();
      ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
      ctx.fill();

      if (isTrafficLight) {
        ctx.fillStyle = "#13243a";
        ctx.font = "10px IBM Plex Mono";
        ctx.textAlign = "left";
        ctx.fillText(node.id, point.x + 6, point.y - 6);
      }
    });

    ctx.fillStyle = "#1f2940";
    ctx.font = "12px IBM Plex Mono";
    ctx.textAlign = "left";
    if (currentFrame) {
      ctx.fillText(
        `SUMO Runtime | Step ${currentFrame.step ?? step} | Vehicles ${currentFrame.vehicle_count ?? 0}`,
        14,
        18,
      );
      if (currentFrame.truncated) {
        ctx.fillStyle = "#7c4b21";
        ctx.fillText("Vehicle drawing truncated for performance.", 14, 36);
      }
    } else {
      ctx.fillText(`SUMO Network | Nodes: ${nodes.length} Edges: ${edges.length} Flows: ${flows.length}`, 14, 18);
    }
  }, [nodes, edges, flows, runtimeFrames, currentFrame, step]);

  return <canvas ref={canvasRef} width={960} height={560} className="w-full h-auto" />;
}
