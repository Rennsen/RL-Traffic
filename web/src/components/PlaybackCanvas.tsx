"use client";

import { useEffect, useRef } from "react";

import type { District } from "@/lib/types";

interface PlaybackCanvasProps {
  district: District | null;
  series: Record<string, any> | null;
  step: number;
  mode: "rl" | "fixed";
  showHeatmap?: boolean;
  onStepChange?: (maxStep: number) => void;
}

function drawRoad(ctx: CanvasRenderingContext2D, road: any) {
  const [x1, y1] = road.from;
  const [x2, y2] = road.to;

  ctx.strokeStyle = "#7d8aa3";
  ctx.lineCap = "round";
  ctx.lineWidth = Math.max(6, road.lanes * 2.6);
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();

  ctx.setLineDash([10, 8]);
  ctx.strokeStyle = "rgba(255, 255, 255, 0.75)";
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
  ctx.setLineDash([]);
}

function drawWaterFeature(ctx: CanvasRenderingContext2D, water: any) {
  ctx.fillStyle = "rgba(86, 153, 201, 0.36)";
  ctx.fillRect(water.x, water.y, water.w, water.h);

  ctx.strokeStyle = "rgba(38, 98, 150, 0.6)";
  ctx.lineWidth = 1.4;
  ctx.strokeRect(water.x, water.y, water.w, water.h);

  ctx.strokeStyle = "rgba(255, 255, 255, 0.42)";
  for (let offset = 12; offset < water.h - 10; offset += 24) {
    ctx.beginPath();
    ctx.moveTo(water.x + 10, water.y + offset);
    ctx.bezierCurveTo(
      water.x + water.w * 0.3,
      water.y + offset - 7,
      water.x + water.w * 0.6,
      water.y + offset + 7,
      water.x + water.w - 10,
      water.y + offset,
    );
    ctx.stroke();
  }

  if (water.label) {
    ctx.fillStyle = "rgba(22, 66, 108, 0.9)";
    ctx.font = "11px IBM Plex Mono";
    ctx.textAlign = "left";
    ctx.fillText(water.label, water.x + 10, water.y + 18);
  }
}

function drawGreenZone(ctx: CanvasRenderingContext2D, zone: any) {
  ctx.fillStyle = "rgba(99, 164, 101, 0.24)";
  ctx.fillRect(zone.x, zone.y, zone.w, zone.h);
  ctx.strokeStyle = "rgba(68, 132, 75, 0.5)";
  ctx.lineWidth = 1.3;
  ctx.strokeRect(zone.x, zone.y, zone.w, zone.h);

  if (zone.id) {
    ctx.fillStyle = "rgba(40, 91, 47, 0.9)";
    ctx.font = "10px IBM Plex Mono";
    ctx.textAlign = "left";
    ctx.fillText(zone.id, zone.x + 8, zone.y + 16);
  }
}

function drawParkingLot(ctx: CanvasRenderingContext2D, lot: any) {
  ctx.fillStyle = "rgba(71, 78, 95, 0.3)";
  ctx.fillRect(lot.x, lot.y, lot.w, lot.h);
  ctx.strokeStyle = "rgba(66, 73, 88, 0.62)";
  ctx.lineWidth = 1.2;
  ctx.strokeRect(lot.x, lot.y, lot.w, lot.h);

  const slots = Math.max(8, Math.min(48, lot.slots ?? 20));
  const split = lot.w >= lot.h;

  if (split) {
    const pitch = lot.w / slots;
    for (let i = 1; i < slots; i += 1) {
      const x = lot.x + i * pitch;
      ctx.strokeStyle = "rgba(240, 242, 245, 0.65)";
      ctx.beginPath();
      ctx.moveTo(x, lot.y + 5);
      ctx.lineTo(x, lot.y + lot.h - 5);
      ctx.stroke();
    }
  } else {
    const pitch = lot.h / slots;
    for (let i = 1; i < slots; i += 1) {
      const y = lot.y + i * pitch;
      ctx.strokeStyle = "rgba(240, 242, 245, 0.65)";
      ctx.beginPath();
      ctx.moveTo(lot.x + 5, y);
      ctx.lineTo(lot.x + lot.w - 5, y);
      ctx.stroke();
    }
  }

  if (lot.id) {
    ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
    ctx.font = "10px IBM Plex Mono";
    ctx.textAlign = "left";
    ctx.fillText(lot.id, lot.x + 6, lot.y + 15);
  }
}

function drawPortYard(ctx: CanvasRenderingContext2D, yard: any) {
  ctx.fillStyle = "rgba(204, 182, 145, 0.34)";
  ctx.fillRect(yard.x, yard.y, yard.w, yard.h);
  ctx.strokeStyle = "rgba(141, 109, 65, 0.66)";
  ctx.lineWidth = 1.2;
  ctx.strokeRect(yard.x, yard.y, yard.w, yard.h);

  const cols = Math.max(4, Math.floor(yard.w / 36));
  const rows = Math.max(2, Math.floor(yard.h / 18));
  const blockW = Math.max(14, Math.floor((yard.w - 12) / cols));
  const blockH = Math.max(8, Math.floor((yard.h - 10) / rows));

  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const x = yard.x + 6 + col * blockW;
      const y = yard.y + 5 + row * blockH;
      const colorShade = (row + col) % 2 === 0 ? "rgba(168, 106, 51, 0.48)" : "rgba(120, 89, 49, 0.48)";
      ctx.fillStyle = colorShade;
      ctx.fillRect(x, y, blockW - 2, blockH - 2);
    }
  }

  if (yard.id) {
    ctx.fillStyle = "rgba(104, 73, 33, 0.92)";
    ctx.font = "10px IBM Plex Mono";
    ctx.textAlign = "left";
    ctx.fillText(yard.id, yard.x + 8, yard.y + 14);
  }
}

function drawDistrictFeatures(ctx: CanvasRenderingContext2D, district: District) {
  const { layout, district_id: districtId } = district;

  if (districtId === "university_ring") {
    (layout as any).green_zones?.forEach((zone: any) => drawGreenZone(ctx, zone));
    (layout as any).parking_lots?.forEach((lot: any) => drawParkingLot(ctx, lot));
  }

  if (districtId === "industrial_port") {
    const water = (layout as any).water;
    if (water) {
      drawWaterFeature(ctx, water);
    }
    (layout as any).port_yards?.forEach((yard: any) => drawPortYard(ctx, yard));
  }
}

function drawIntersection(ctx: CanvasRenderingContext2D, node: any, phase: number, queue = 0, emergency = 0) {
  const radius = 8 + Math.min(10, queue / 8);
  ctx.fillStyle = phase === 0 ? "rgba(35, 103, 226, 0.9)" : "rgba(241, 153, 64, 0.9)";
  ctx.beginPath();
  ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
  ctx.fill();

  if (emergency > 0) {
    ctx.strokeStyle = "rgba(197, 54, 46, 0.95)";
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius + 4, 0, Math.PI * 2);
    ctx.stroke();
  }

  ctx.fillStyle = "#f8fbff";
  ctx.font = "10px IBM Plex Mono";
  ctx.textAlign = "center";
  ctx.fillText(node.id, node.x, node.y + 3);
}

function normalizedLoad(value: number, divisor = 6) {
  return Math.max(0, Math.min(24, Math.round(value / divisor)));
}

function drawCarsAlongRoad(ctx: CanvasRenderingContext2D, road: any, step: number, positive: number, negative: number, emergencyShare: number) {
  const [x1, y1] = road.from;
  const [x2, y2] = road.to;

  const dx = x2 - x1;
  const dy = y2 - y1;
  const length = Math.max(1, Math.hypot(dx, dy));
  const nx = -dy / length;
  const ny = dx / length;

  function drawDirection(count: number, reverse: boolean, laneOffset: number, speed: number, color: string) {
    for (let i = 0; i < count; i += 1) {
      const seed = ((i * 0.173) + (road.lanes * 0.03)) % 1;
      let t = (step * speed * 0.01 + seed) % 1;
      if (reverse) {
        t = 1 - t;
      }
      const x = x1 + dx * t + nx * laneOffset;
      const y = y1 + dy * t + ny * laneOffset;

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, 2.4, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  const normalColor = "rgba(35, 103, 226, 0.9)";
  const emergencyColor = "rgba(220, 70, 70, 0.95)";

  drawDirection(normalizedLoad(positive, 4.5), false, 4, 1.4, normalColor);
  drawDirection(normalizedLoad(negative, 4.5), true, -4, 1.25, normalColor);
  drawDirection(Math.max(0, Math.min(6, Math.round(emergencyShare / 2))), false, 8.5, 1.8, emergencyColor);
}

export function PlaybackCanvas({
  district,
  series,
  step,
  mode,
  showHeatmap = false,
  onStepChange,
}: PlaybackCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !district) {
      return;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }

    const maxStep = series ? Math.max(0, (series.queue?.length ?? 1) - 1) : 0;
    onStepChange?.(maxStep);
    const stepIndex = Math.max(0, Math.min(step, maxStep));

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = "#eef3f9";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = "rgba(31, 52, 86, 0.05)";
    for (let x = 0; x < canvas.width; x += 40) {
      ctx.fillRect(x, 0, 1, canvas.height);
    }
    for (let y = 0; y < canvas.height; y += 40) {
      ctx.fillRect(0, y, canvas.width, 1);
    }

    drawDistrictFeatures(ctx, district);

    for (const road of district.layout.roads) {
      drawRoad(ctx, road);
    }

    const phase = series?.phase?.[stepIndex] ?? 0;
    const intersectionPhase = series?.intersection_phase ?? {};
    const intersectionQueue = series?.intersection_queue ?? {};
    const intersectionEmergency = series?.intersection_emergency ?? {};
    for (const intersection of district.layout.intersections) {
      const localPhase = intersectionPhase?.[intersection.id]?.[stepIndex] ?? phase;
      const queue = intersectionQueue?.[intersection.id]?.[stepIndex] ?? 0;
      const emergency = intersectionEmergency?.[intersection.id]?.[stepIndex] ?? 0;
      drawIntersection(ctx, intersection, localPhase, queue, emergency);
    }

    if (series) {
      const dq = series.directional_queue ?? {};
      const de = series.directional_emergency ?? {};

      for (const road of district.layout.roads) {
        const [x1, y1] = road.from;
        const [x2, y2] = road.to;
        const horizontal = Math.abs(y2 - y1) < Math.abs(x2 - x1);

        if (horizontal) {
          drawCarsAlongRoad(
            ctx,
            road,
            stepIndex,
            (dq.E?.[stepIndex] ?? 0) + (de.E?.[stepIndex] ?? 0),
            (dq.W?.[stepIndex] ?? 0) + (de.W?.[stepIndex] ?? 0),
            (de.E?.[stepIndex] ?? 0) + (de.W?.[stepIndex] ?? 0),
          );
        } else {
          drawCarsAlongRoad(
            ctx,
            road,
            stepIndex,
            (dq.S?.[stepIndex] ?? 0) + (de.S?.[stepIndex] ?? 0),
            (dq.N?.[stepIndex] ?? 0) + (de.N?.[stepIndex] ?? 0),
            (de.S?.[stepIndex] ?? 0) + (de.N?.[stepIndex] ?? 0),
          );
        }
      }
    }

    if (showHeatmap && series?.queue?.length) {
      const intensity = Math.min(1, (series.queue[stepIndex] ?? 0) / 300);
      for (const intersection of district.layout.intersections) {
        const radius = 18 + intensity * 22;
        const gradient = ctx.createRadialGradient(
          intersection.x,
          intersection.y,
          0,
          intersection.x,
          intersection.y,
          radius,
        );
        gradient.addColorStop(0, `rgba(255, 99, 71, ${0.35 + intensity * 0.25})`);
        gradient.addColorStop(1, "rgba(255, 99, 71, 0)");
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(intersection.x, intersection.y, radius, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    ctx.fillStyle = "#1f2940";
    ctx.font = "12px IBM Plex Mono";
    ctx.fillText(`${district.name} | ${mode.toUpperCase()} Playback`, 16, 20);
  }, [district, series, step, mode, showHeatmap, onStepChange]);

  return <canvas ref={canvasRef} width={960} height={560} className="w-full h-auto" />;
}
