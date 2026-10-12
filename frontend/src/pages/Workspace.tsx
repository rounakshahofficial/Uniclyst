import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge, Button, Card, CardBody, ErrorNote, Field, Input, PageHeader, Spinner,
} from "../components/ui";
import { get, patch, post } from "../lib/api";
import type { Collaboration } from "../types";

function fmt(iso: string | null) {
  return iso ? new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "—";
}

export default function Workspace() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [due, setDue] = useState("");
  const [error, setError] = useState<string | null>(null);

  const collab = useQuery({
    queryKey: ["collaboration", id],
    queryFn: () => get<Collaboration>(`/collaborations/${id}`),
    enabled: !!id,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["collaboration", id] });
    queryClient.invalidateQueries({ queryKey: ["collaborations"] });
  };

  const addMilestone = useMutation({
    mutationFn: () =>
      post(`/collaborations/${id}/milestones`, { title, due_date: due || null }),
    onSuccess: () => {
      setTitle("");
      setDue("");
      invalidate();
    },
    onError: (e: any) => setError(e.message),
  });

  const setMilestone = useMutation({
    mutationFn: ({ mid, status }: { mid: number; status: string }) =>
      patch(`/milestones/${mid}`, { status }),
    onSuccess: invalidate,
    onError: (e: any) => setError(e.message),
  });

  const setStatus = useMutation({
    mutationFn: (status: string) => patch(`/collaborations/${id}`, { status }),
    onSuccess: invalidate,
    onError: (e: any) => setError(e.message),
  });

  if (collab.isLoading) return <Spinner label="Loading workspace…" />;
  if (collab.isError || !collab.data) {
    return (
      <div className="py-16 text-center">
        <p className="text-lg font-semibold text-ink">Workspace not found or access denied</p>
        <Link to="/collaborations" className="mt-2 inline-block text-sm text-accent hover:underline">
          ← Back to collaborations
        </Link>
      </div>
    );
  }

  const c = collab.data;
  const reached = c.milestones.filter((m) => m.status === "reached").length;

  return (
    <div>
      <PageHeader
        title={c.title}
        subtitle={`${c.requester_community_name} ↔ ${c.target_community_name}${c.goal ? ` · ${c.goal}` : ""}`}
        actions={
          c.status === "active" ? (
            <Button variant="success" loading={setStatus.isPending} onClick={() => setStatus.mutate("completed")}>
              Mark completed
            </Button>
          ) : (
            <Badge tone={c.status === "completed" ? "green" : "gray"}>{c.status}</Badge>
          )
        }
      />

      {error && <div className="mb-4"><ErrorNote message={error} /></div>}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Milestones */}
        <section className="lg:col-span-2">
          <Card>
            <CardBody>
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold text-ink">Milestones</h2>
                <span className="text-sm text-ink-faint">
                  {reached}/{c.milestones.length} reached
                </span>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-accent transition-all"
                  style={{ width: `${c.milestones.length ? (reached / c.milestones.length) * 100 : 0}%` }}
                />
              </div>

              <ul className="mt-5 space-y-3">
                {c.milestones.map((m) => (
                  <li key={m.id} className="flex items-start gap-3 rounded-lg border border-surface-line p-4">
                    <button
                      aria-label={m.status === "reached" ? "Mark pending" : "Mark reached"}
                      className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 transition-colors ${
                        m.status === "reached"
                          ? "border-emerald-500 bg-emerald-500 text-white"
                          : "border-slate-300 hover:border-accent"
                      }`}
                      onClick={() =>
                        setMilestone.mutate({
                          mid: m.id,
                          status: m.status === "reached" ? "pending" : "reached",
                        })
                      }
                    >
                      {m.status === "reached" && (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                          <path d="M20 6 9 17l-5-5" />
                        </svg>
                      )}
                    </button>
                    <div className="flex-1">
                      <p className={`text-sm font-medium ${m.status === "reached" ? "text-ink-faint line-through" : "text-ink"}`}>
                        {m.title}
                      </p>
                      {m.description && <p className="mt-0.5 text-xs text-ink-faint">{m.description}</p>}
                    </div>
                    {m.due_date && <span className="text-xs text-ink-faint">due {fmt(m.due_date)}</span>}
                  </li>
                ))}
              </ul>

              <div className="mt-5 rounded-lg bg-surface p-4">
                <h3 className="text-sm font-medium text-ink">Add milestone</h3>
                <div className="mt-3 flex flex-wrap items-end gap-3">
                  <div className="min-w-[200px] flex-1">
                    <Field label="Title" htmlFor="mt">
                      <Input id="mt" value={title} placeholder="Working perception demo"
                        onChange={(e) => setTitle(e.target.value)} />
                    </Field>
                  </div>
                  <div>
                    <Field label="Due date" htmlFor="md">
                      <Input id="md" type="date" value={due} onChange={(e) => setDue(e.target.value)} />
                    </Field>
                  </div>
                  <Button loading={addMilestone.isPending} disabled={!title}
                    onClick={() => addMilestone.mutate()}>
                    Add
                  </Button>
                </div>
              </div>
            </CardBody>
          </Card>
        </section>

        {/* Sidebar */}
        <aside className="space-y-6">
          <Card>
            <CardBody>
              <h2 className="text-sm font-semibold text-ink">Workspace status</h2>
              <dl className="mt-3 space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-ink-faint">Status</dt>
                  <dd><Badge tone={c.status === "active" ? "green" : "blue"}>{c.status}</Badge></dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-ink-faint">Started</dt>
                  <dd className="text-ink">{fmt(c.started_at)}</dd>
                </div>
                {c.completed_at && (
                  <div className="flex justify-between">
                    <dt className="text-ink-faint">Completed</dt>
                    <dd className="text-ink">{fmt(c.completed_at)}</dd>
                  </div>
                )}
                {c.summary && (
                  <div className="pt-2">
                    <dt className="text-ink-faint">Outcome</dt>
                    <dd className="mt-1 rounded-lg bg-surface p-3 text-ink-soft">{c.summary}</dd>
                  </div>
                )}
              </dl>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <h2 className="text-sm font-semibold text-ink">Participants</h2>
              <ul className="mt-3 space-y-3">
                {c.members.map((m) => (
                  <li key={`${m.user_id}-${m.community_id}`}>
                    <p className="text-sm font-medium text-ink">{m.full_name || m.username}</p>
                    <p className="text-xs text-ink-faint">
                      {m.community_name} · <Badge tone={m.role === "lead" ? "blue" : "gray"}>{m.role}</Badge>
                    </p>
                  </li>
                ))}
              </ul>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <h2 className="text-sm font-semibold text-ink">Sides</h2>
              <div className="mt-3 space-y-2 text-sm">
                <Link to={`/communities/${c.requester_community_id}`}
                  className="block rounded-lg border border-surface-line px-3 py-2 font-medium text-ink hover:border-accent hover:text-accent">
                  {c.requester_community_name}
                </Link>
                <Link to={`/communities/${c.target_community_id}`}
                  className="block rounded-lg border border-surface-line px-3 py-2 font-medium text-ink hover:border-accent hover:text-accent">
                  {c.target_community_name}
                </Link>
              </div>
            </CardBody>
          </Card>
        </aside>
      </div>
    </div>
  );
}
