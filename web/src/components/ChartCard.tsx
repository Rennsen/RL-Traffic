"use client";

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

interface ChartCardProps {
  title: string;
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    borderColor: string;
    backgroundColor: string;
  }[];
}

export function ChartCard({ title, labels, datasets }: ChartCardProps) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4 shadow-soft hover-lift">
      <h4 className="text-sm font-semibold text-ink">{title}</h4>
      <div className="mt-3 h-64">
        <Line
          data={{ labels, datasets }}
          options={{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: "bottom",
                labels: { color: "#5b6b80", boxWidth: 10, usePointStyle: true },
              },
            },
            scales: {
              x: {
                ticks: { color: "#5b6b80" },
                grid: { color: "rgba(15, 23, 42, 0.08)" },
              },
              y: {
                ticks: { color: "#5b6b80" },
                grid: { color: "rgba(15, 23, 42, 0.08)" },
                beginAtZero: true,
              },
            },
          }}
        />
      </div>
    </div>
  );
}
