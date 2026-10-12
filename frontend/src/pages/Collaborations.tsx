import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge, Button, Card, CardBody, EmptyState, ErrorNote, Field, Input, PageHeader, Select, Spinner, Textarea,
} from "../components/ui";
import { get, patch, post } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Collaboration, CollaborationRequest, Community, Page } from "../types";

function fmt(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

const statusTone: Record<string, "blue" | "green" | "red" | "gray" | "amber"> = {
  pending: "amber",
  accepted: "green",
  rejected: "red",
  withdrawn: "gray",
};

export default function Collaborations() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [direction, setDirection] = useState("all");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    target_community_id: "", title: "", goal: "", message: "", needed_skills: "", proposed_timeline: "",
  });
  const [error, setError] = useState<string | null>(null);

  const requests = useQuery({
    queryKey: ["requests", direction],
    queryFn: () => get<{ items: CollaborationRequest[] }>(`/collaboration-requests?direction=${direction}`),
  });
  const collabs = useQuery({
    queryKey: ["collaborations"],
    queryFn: () => get<{ items: Collaboration[] }>("/collaborations"),
  });
  const communities = useQuery({
    queryKey: ["communities", "all-for-proposal"],
    queryFn: () => get<Page<Community>>("/communities?page_size=50"),
  });

  const act = useMutation({
    mutationFn: ({ id, action }: { id: number; action: string }) =>
      patch(`/collaboration-requests/${id}`, { action }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["requests"] });
      queryClient.invalidateQueries({ queryKey: ["collaborations"] });
    },
    onError: (e: any) => setError(e.message),
  });

  const send = useMutation({
    mutationFn: async () => {
      const mine = communities.data?.items.find((c) =>
        c.members.some((m) => m.user_id === user?.id && m.role === "organizer")
      );
      if (!mine) throw new Error("You need to organize a community before sending proposals.");
      await post("/collaboration-requests", {
        requester_community_id: mine.id,
        target_community_id: Number(form.target_community_id),
        title: form.title,
        goal: form.goal,
        message: form.message,
        needed_skills: form.needed_skills.split(",").map((s) => s.trim()).filter(Boolean),
        proposed_timeline: form.proposed_timeline,
      });
    },
    onSuccess: () => {
      setShowForm(false);
      setForm({ target_community_id: "", title: "", goal: "", message: "", needed_skills: "", proposed_timeline: "" });
      queryClient.invalidateQueries({ queryKey: ["requests"] });
    },
    onError: (e: any) => setError(e.message),
  });

  return (
    <div>
      <PageHeader
        title="Collaborations"
        subtitle="Proposals move one way at a time: send, accept or reject, then track the joint work. A partnership exists only after explicit acceptance."
        actions={<Button onClick={() => setShowForm((s) => !s)}>New proposal</Button>}
      />

      {error && <div className="mb-4"><ErrorNote message={error} /></div>}

      {showForm && (
        <Card className="mb-6 border-accent/40">
          <CardBody className="space-y-4">
            <h2 className="text-base font-semibold text-ink">Send a collaboration proposal</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Target community" htmlFor="tc">
                <Select id="tc" value={form.target_community_id}
                  onChange={(e) => setForm({ ...form, target_community_id: e.target.value })}>
                  <option value="">— Select —</option>
                  {communities.data?.items
                    .filter((c) => !c.members.some((m) => m.user_id === user?.id && m.role === "organizer"))
                    .map((c) => (
                      <option key={c.id} value={c.id}>{c.name} ({c.college_short})</option>
                    ))}
                </Select>
              </Field>
              <Field label="Title" htmlFor="ct">
                <Input id="ct" value={form.title} placeholder="Joint perception build"
                  onChange={(e) => setForm({ ...form, title: e.target.value })} />
              </Field>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Goal" htmlFor="cg">
                <Input id="cg" value={form.goal} onChange={(e) => setForm({ ...form, goal: e.target.value })} />
              </Field>
              <Field label="Timeline" htmlFor="ctl">
                <Input id="ctl" value={form.proposed_timeline} placeholder="8 weeks"
                  onChange={(e) => setForm({ ...form, proposed_timeline: e.target.value })} />
              </Field>
            </div>
            <Field label="Needed skills (comma-separated)" htmlFor="cs">
              <Input id="cs" value={form.needed_skills} placeholder="Computer Vision"
                onChange={(e) => setForm({ ...form, needed_skills: e.target.value })} />
            </Field>
            <Field label="Message" htmlFor="cm">
              <Textarea id="cm" value={form.message} placeholder="Why this collaboration, why them?"
                onChange={(e) => setForm({ ...form, message: e.target.value })} />
            </Field>
            <div className="flex gap-2">
              <Button loading={send.isPending} disabled={!form.target_community_id || !form.title}
                onClick={() => send.mutate()}>
                Send proposal
              </Button>
              <Button variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Workspaces */}
      <section className="mb-10">
        <h2 className="mb-3 text-lg font-semibold text-ink">Active collaborations</h2>
        {collabs.isLoading && <Spinner />}
        {collabs.data?.items.length === 0 ? (
          <EmptyState
            title="No collaborations yet"
            description="When a proposal is accepted, both communities get a shared workspace with milestones."
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {collabs.data?.items.map((c) => (
              <Card key={c.id} className="transition-shadow hover:shadow-pop">
                <CardBody>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <Link to={`/collaborations/${c.id}`}
                        className="text-base font-semibold text-ink hover:text-accent hover:underline">
                        {c.title}
                      </Link>
                      <p className="mt-0.5 text-xs text-ink-faint">
                        {c.requester_community_name} ↔ {c.target_community_name}
                      </p>
                    </div>
                    <Badge tone={c.status === "active" ? "green" : c.status === "completed" ? "blue" : "gray"}>
                      {c.status}
                    </Badge>
                  </div>
                  <div className="mt-3 flex items-center gap-3 text-xs text-ink-faint">
                    <span>{c.milestones.filter((m) => m.status === "reached").length}/{c.milestones.length} milestones</span>
                    <span>started {fmt(c.started_at)}</span>
                  </div>
                  <div className="mt-3">
                    <Button size="sm" variant="secondary" onClick={() => navigate(`/collaborations/${c.id}`)}>
                      Open workspace
                    </Button>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </section>

      {/* Requests */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-ink">Proposals</h2>
          <Select value={direction} onChange={(e) => setDirection(e.target.value)} className="w-auto">
            <option value="all">All</option>
            <option value="incoming">Incoming</option>
            <option value="outgoing">Outgoing</option>
          </Select>
        </div>

        {requests.isLoading && <Spinner />}
        {requests.data?.items.length === 0 ? (
          <EmptyState
            title="No proposals"
            description="Send one from a community profile or the button above — matches on the Matches page can send proposals in one click."
          />
        ) : (
          <div className="space-y-3">
            {requests.data?.items.map((r) => (
              <Card key={r.id}>
                <CardBody>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <Badge tone={r.direction === "incoming" ? "violet" : "blue"}>{r.direction}</Badge>
                        <Badge tone={statusTone[r.status] ?? "gray"}>{r.status}</Badge>
                      </div>
                      <p className="mt-1.5 text-sm font-semibold text-ink">{r.title}</p>
                      <p className="text-xs text-ink-faint">
                        {r.requester_community_name} → {r.target_community_name} · sent {fmt(r.created_at)}
                        {r.proposed_timeline ? ` · ${r.proposed_timeline}` : ""}
                      </p>
                      {r.goal && <p className="mt-1 text-sm text-ink-soft">Goal: {r.goal}</p>}
                      {r.message && <p className="mt-1 text-sm text-ink-soft">{r.message}</p>}
                      {r.needed_skills.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {r.needed_skills.map((s) => <Badge key={s} tone="gray">{s}</Badge>)}
                        </div>
                      )}
                      {r.response_note && (
                        <p className="mt-2 rounded-lg bg-surface px-3 py-2 text-xs text-ink-soft">
                          Response: {r.response_note}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-col gap-2">
                      {r.status === "pending" && r.direction === "incoming" && (
                        <>
                          <Button size="sm" variant="success" loading={act.isPending}
                            onClick={() => act.mutate({ id: r.id, action: "accept" })}>
                            Accept
                          </Button>
                          <Button size="sm" variant="danger" loading={act.isPending}
                            onClick={() => act.mutate({ id: r.id, action: "reject" })}>
                            Reject
                          </Button>
                        </>
                      )}
                      {r.status === "pending" && r.direction === "outgoing" && (
                        <Button size="sm" variant="secondary" loading={act.isPending}
                          onClick={() => act.mutate({ id: r.id, action: "withdraw" })}>
                          Withdraw
                        </Button>
                      )}
                    </div>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
