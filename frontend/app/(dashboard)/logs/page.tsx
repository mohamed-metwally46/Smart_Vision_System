"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { logsApi } from "@/lib/api";
import { useCamerasStore } from "@/lib/store";
import Table from "@/components/ui/Table";
import Badge from "@/components/ui/Badge";
import type { EventLog, EventType } from "@/types";
import { format } from "date-fns";
import { RefreshCw } from "lucide-react";

const EVENT_TYPES: { label: string; value: EventType | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Entry", value: "entry_event" },
  { label: "Exit", value: "exit_event" },
  { label: "Zone Violation", value: "zone_violation" },
  { label: "Loitering", value: "loitering_alert" },
];

const eventTypeColor: Record<EventType, string> = {
  entry_event: "text-severity-low",
  exit_event: "text-severity-medium",
  zone_violation: "text-severity-high",
  loitering_alert: "text-severity-medium",
};

export default function LogsPage() {
  const [eventType, setEventType] = useState<EventType | "all">("all");
  const [page, setPage] = useState(1);
  const cameras = useCamerasStore((s) => s.cameras);
  const activeCameraId = useCamerasStore((s) => s.activeCameraId);
  const [cameraFilter, setCameraFilter] = useState<number | "all">("all");

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["logs", eventType, cameraFilter, page],
    queryFn: () =>
      logsApi.list({
        page,
        limit: 50,
        ...(eventType !== "all" && { event_type: eventType }),
        ...(cameraFilter !== "all" && { camera_id: cameraFilter }),
      }),
    refetchInterval: 15_000,
  });

  const columns = [
    {
      key: "id",
      header: "ID",
      render: (row: EventLog) => (
        <span className="text-ink-muted font-mono">#{row.id}</span>
      ),
      className: "w-16",
    },
    {
      key: "camera",
      header: "Camera",
      render: (row: EventLog) => (
        <span className="font-mono text-ink-secondary">CAM-{row.camera_id}</span>
      ),
      className: "w-24",
    },
    {
      key: "type",
      header: "Event",
      render: (row: EventLog) => (
        <span
          className={`font-mono text-xs ${
            eventTypeColor[row.event_type] ?? "text-ink-secondary"
          }`}
        >
          {row.event_type}
        </span>
      ),
      className: "w-40",
    },
    {
      key: "message",
      header: "Message",
      render: (row: EventLog) => (
        <span className="text-ink-primary">{row.message}</span>
      ),
    },
    {
      key: "timestamp",
      header: "Timestamp",
      render: (row: EventLog) => (
        <span className="font-mono text-ink-muted text-xs">
          {format(new Date(row.timestamp), "yyyy-MM-dd HH:mm:ss")}
        </span>
      ),
      className: "w-44 text-right",
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-lg text-ink-primary">Event Logs</h1>
          <p className="text-ink-secondary text-xs font-mono mt-0.5">
            Historical entry/exit, zone, and behavior events
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="btn-ghost flex items-center gap-2 text-xs"
        >
          <RefreshCw size={12} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="panel p-3 flex flex-wrap items-center gap-4">
        {/* Event type */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-mono text-ink-muted uppercase tracking-widest">
            Type:
          </span>
          {EVENT_TYPES.map(({ label, value }) => (
            <button
              key={value}
              onClick={() => { setEventType(value); setPage(1); }}
              className={`px-3 py-1 text-xs font-mono rounded border transition-colors ${
                eventType === value
                  ? "bg-accent/10 text-accent border-accent/40"
                  : "text-ink-secondary border-border hover:border-border-bright"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Camera filter */}
        {cameras.length > 1 && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-ink-muted uppercase tracking-widest">
              Camera:
            </span>
            <select
              value={cameraFilter}
              onChange={(e) => {
                const v = e.target.value;
                setCameraFilter(v === "all" ? "all" : parseInt(v));
                setPage(1);
              }}
              className="input-field w-auto py-1"
            >
              <option value="all">All</option>
              {cameras.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="panel">
        {isLoading ? (
          <div className="py-16 flex items-center justify-center">
            <p className="text-ink-muted font-mono text-sm animate-pulse">
              Loading logs...
            </p>
          </div>
        ) : (
          <>
            <Table
              columns={columns}
              data={data?.items ?? []}
              keyExtractor={(row) => row.id}
              emptyMessage="No events found"
            />
            {data && data.total > 0 && (
              <div className="flex items-center justify-between px-3 py-2.5 border-t border-border">
                <span className="text-xs font-mono text-ink-muted">
                  Page {data.page} · Showing {data.items.length} of {data.total}
                </span>
                <div className="flex gap-2">
                  <button
                    disabled={page === 1}
                    onClick={() => setPage((p) => p - 1)}
                    className="btn-ghost text-xs disabled:opacity-40"
                  >
                    Prev
                  </button>
                  <button
                    disabled={page * data.limit >= data.total}
                    onClick={() => setPage((p) => p + 1)}
                    className="btn-ghost text-xs disabled:opacity-40"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
