import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge, Button, Card, CardBody, EmptyState, ErrorNote, Field, Input, PageHeader, Spinner,
} from "../components/ui";
import { get, patch, post } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { DiscoveryJob, DiscoverySource, Page, ScoutCandidate } from "../types";

function fmt(iso: string) {
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function Discovery() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [region, setRegion] = useState("Delhi NCR");
  const [interests, setInterests] = useState("");
  const [candidates, setCandidates] = useState<ScoutCandidate[]>([]);
  const [lastJob, setLastJob] = useState<DiscoveryJob | null>(null);
  const [error, setError] = useState<string | null>(null);

  const jobs = useQuery({
    queryKey: ["discovery-jobs"],
    queryFn: () => get<{ items: DiscoveryJob[] }>("/discovery/jobs"),
  });

  const sources = useQuery({
    queryKey: ["discovery-sources"],
    queryFn: () => get<{ items: DiscoverySource[] }>("/discovery/sources?page_size=30"),
  });

  const run = useMutation({
    mutationFn: async () => {
      const body = {
        query,
        region,
        interests: interests.split(",").map((s) => s.trim()).filter(Boolean),
      };
      return post<{ job: DiscoveryJob; candidates: ScoutCandidate[] }>("/discovery/jobs", body);
    },
    onSuccess: (data) => {
      setLastJob(data.job);
      setCandidates(data.candidates);
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["discovery-jobs"] });
      queryClient.invalidateQueries({ queryKey: ["discovery-sources"] });
    },
    onError: (e: any) => setError(e.message),
  });

  const review = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      patch(`/discovery/sources/${id}`, { review_status: status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["discovery-sources"] }),
  });

  const importSource = useMutation({
    mutationFn: (id: number) => post(`/discovery/sources/${id}/import`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["discovery-sources"] });
      queryClient.invalidateQueries({ queryKey: ["communities"] });
    },
  });

  return (
    <div>
      <PageHeader
        title="Community Scout"
        subtitle="Discover student communities from public web sources. Extracted records keep their evidence, timestamps and review status — nothing is imported as verified."
      />

      {/* Mode banner */}
      <div className="mb-6 rounded-xl border border-surface-line bg-white p-4 text-sm text-ink-soft shadow-card">
        <strong className="text-ink">How this works:</strong> targeted searches → page fetch →
        structured extraction → validation & dedupe → reviewer approval. Without a TinyFish API key
        the scout runs in <Badge tone="amber">demo mode</Badge> against a clearly-labeled corpus;
        with <code className="mx-1 rounded bg-slate-100 px-1">TINYFISH_API_KEY</code> set on the
        backend it performs live Search + Fetch calls. The API key never reaches the browser.
      </div>

      <Card className="mb-8">
        <CardBody>
          <div className="grid gap-4 md:grid-cols-3">
            <Field label="Discovery query" htmlFor="dq"
                   hint="e.g. active robotics, AI and innovation clubs">
              <Input id="dq" value={query} placeholder="robotics, AI and innovation clubs"
                     onChange={(e) => setQuery(e.target.value)} />
            </Field>
            <Field label="Region" htmlFor="dr">
              <Input id="dr" value={region} onChange={(e) => setRegion(e.target.value)} />
            </Field>
            <Field label="Interests (comma-separated)" htmlFor="di">
              <Input id="di" value={interests} placeholder="robotics, ai"
                     onChange={(e) => setInterests(e.target.value)} />
            </Field>
          </div>
          <div className="mt-4 flex items-center gap-3">
            <Button loading={run.isPending} disabled={query.trim().length < 3} onClick={() => run.mutate()}>
              Run discovery
            </Button>
            {error && <ErrorNote message={error} />}
          </div>
        </CardBody>
      </Card>

      {run.isPending && <Spinner label="Scouting public sources…" />}

      {lastJob && (
        <section className="mb-8">
          <h2 className="mb-3 text-lg font-semibold text-ink">
            Results for “{lastJob.query}”
            <Badge tone={lastJob.mode === "live" ? "green" : "gray"}>
              {lastJob.mode === "live" ? "live · TinyFish" : "demo corpus"}
            </Badge>
          </h2>
          <div className="mb-4 rounded-lg bg-slate-50 p-4 text-xs text-ink-faint">
            {lastJob.notes.map((n, i) => (
              <p key={i}>• {n}</p>
            ))}
          </div>
          {candidates.length === 0 ? (
            <EmptyState title="No candidates extracted" description="Try a broader query or different interests." />
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {candidates.map((c, i) => (
                <Card key={i}>
                  <CardBody>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-base font-semibold text-ink">{c.organization_name}</p>
                        <p className="text-xs text-ink-faint">{c.college} · {c.city}</p>
                      </div>
                      <Badge tone={c.confidence >= 70 ? "green" : c.confidence >= 50 ? "blue" : "amber"}
                             title="Transparent heuristic — not a calibrated probability">
                        confidence {Math.round(c.confidence)}
                      </Badge>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {c.interests.slice(0, 6).map((t) => (
                        <Badge key={t} tone="blue">{t}</Badge>
                      ))}
                    </div>
                    {c.event_names.length > 0 && (
                      <p className="mt-2 text-xs text-ink-soft">Events: {c.event_names.join(", ")}</p>
                    )}
                    {c.missing_or_conflicting && (
                      <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
                        {c.missing_or_conflicting}
                      </p>
                    )}
                    {c.dedupe_match_org_id && (
                      <p className="mt-2 text-xs text-ink-faint">
                        Matches existing community{" "}
                        <Link to={`/communities/${c.dedupe_match_org_id}`} className="text-accent hover:underline">
                          #{c.dedupe_match_org_id}
                        </Link>
                      </p>
                    )}
                  </CardBody>
                </Card>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Review queue */}
      <section>
        <h2 className="mb-3 text-lg font-semibold text-ink">Evidence & review queue</h2>
        {sources.isLoading && <Spinner />}
        {sources.data?.items.length === 0 && (
          <EmptyState
            title="No discovery records yet"
            description="Run a discovery job above — extracted records will appear here with their evidence for review."
          />
        )}
        <div className="space-y-4">
          {sources.data?.items.map((s) => {
            const extracted = s.extracted as Record<string, any>;
            return (
              <Card key={s.id}>
                <CardBody>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-ink">
                        {extracted?.organization_name ?? s.source_title ?? "Extracted record"}
                      </p>
                      <a href={s.source_url} target="_blank" rel="noreferrer"
                         className="mt-0.5 block break-all text-xs text-accent hover:underline">
                        {s.source_url} ↗
                      </a>
                      <p className="mt-1 line-clamp-2 text-xs text-ink-faint">{s.evidence_excerpt}</p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <div className="flex items-center gap-1.5">
                        <Badge tone={s.review_status === "verified" ? "green" : s.review_status === "reviewed" ? "blue" : "amber"}>
                          {s.review_status}
                        </Badge>
                        <Badge tone={s.origin === "scout" ? "violet" : "gray"}>{s.origin}</Badge>
                        <Badge tone="gray">conf {Math.round(s.confidence)}</Badge>
                      </div>
                      <div className="flex gap-1.5">
                        {user?.role === "reviewer" || user?.role === "admin" ? (
                          <>
                            <Button size="sm" variant="secondary" loading={review.isPending}
                              onClick={() => review.mutate({ id: s.id, status: "reviewed" })}>
                              Mark reviewed
                            </Button>
                            <Button size="sm" variant="success" loading={review.isPending}
                              onClick={() => review.mutate({ id: s.id, status: "verified" })}>
                              Verify
                            </Button>
                          </>
                        ) : (
                          <span className="text-[11px] text-ink-faint">reviewer actions</span>
                        )}
                        <Button size="sm" loading={importSource.isPending}
                          onClick={() => importSource.mutate(s.id)}>
                          Import
                        </Button>
                      </div>
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-ink-faint">
                    <span>retrieved {fmt(s.retrieved_at)}</span>
                    <span>· last checked {fmt(s.last_checked_at)}</span>
                    {s.review_note && <span>· {s.review_note}</span>}
                  </div>
                </CardBody>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Job history */}
      {jobs.data && jobs.data.items.length > 0 && (
        <section className="mt-10">
          <h2 className="mb-3 text-lg font-semibold text-ink">Job history</h2>
          <Card>
            <ul className="divide-y divide-surface-line">
              {jobs.data.items.map((j) => (
                <li key={j.id} className="flex items-center justify-between px-5 py-3 text-sm">
                  <div>
                    <p className="font-medium text-ink">{j.query}</p>
                    <p className="text-xs text-ink-faint">
                      {j.region} · {fmt(j.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={j.mode === "live" ? "green" : "gray"}>{j.mode}</Badge>
                    <Badge tone={j.status === "completed" ? "blue" : j.status === "failed" ? "red" : "amber"}>
                      {j.status}
                    </Badge>
                    <span className="text-xs text-ink-faint">{j.result_count} records</span>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        </section>
      )}
    </div>
  );
}
