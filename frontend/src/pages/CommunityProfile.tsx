import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge, Button, Card, CardBody, ErrorNote, Field, Input, PageHeader, Spinner, Textarea, TrustBadge,
} from "../components/ui";
import { del, get, post } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Community, EventItem, Page } from "../types";

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function CommunityProfile() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showProposal, setShowProposal] = useState(false);
  const [proposal, setProposal] = useState({ title: "", goal: "", message: "", needed_skills: "", proposed_timeline: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const community = useQuery({
    queryKey: ["community", id],
    queryFn: () => get<Community>(`/communities/${id}`),
    enabled: !!id,
  });

  if (community.isLoading) return <Spinner label="Loading community…" />;
  if (community.isError || !community.data) {
    return <EmptyOrMissing />;
  }

  const c = community.data;
  const offers = c.skills.filter((s) => s.kind === "offers");
  const seeks = c.skills.filter((s) => s.kind === "seeks");

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["community", id] });

  const sendProposal = async () => {
    if (!user) return navigate("/login");
    setError(null);
    setBusy(true);
    try {
      // Find "my" community — the first community where I'm an organizer, or any I belong to.
      const mine = await get<Page<Community>>(`/communities?page_size=50`);
      const myCommunity = mine.items.find((m) =>
        m.members.some((mem) => mem.user_id === user.id && mem.role === "organizer")
      );
      if (!myCommunity) {
        setError("You need to organize a community first (create one from Explore → or join one) before sending proposals.");
        return;
      }
      if (myCommunity.id === c.id) {
        setError("You cannot propose a collaboration with your own community.");
        return;
      }
      await post("/collaboration-requests", {
        requester_community_id: myCommunity.id,
        target_community_id: c.id,
        title: proposal.title,
        goal: proposal.goal,
        message: proposal.message,
        needed_skills: proposal.needed_skills.split(",").map((s) => s.trim()).filter(Boolean),
        proposed_timeline: proposal.proposed_timeline,
      });
      setShowProposal(false);
      navigate("/collaborations");
    } catch (e: any) {
      setError(e.message ?? "Could not send proposal");
    } finally {
      setBusy(false);
    }
  };

  const toggleSave = async () => {
    if (!user) return navigate("/login");
    if (c.saved) await del(`/users/me/saved/${c.id}`);
    else await post(`/users/me/saved/${c.id}`);
    invalidate();
    queryClient.invalidateQueries({ queryKey: ["saved"] });
  };

  return (
    <div>
      <PageHeader
        title={c.name}
        subtitle={`${c.college_name ?? ""}${c.city ? ` · ${c.city}` : ""} · ${c.category}`}
        actions={
          <>
            <Button variant="secondary" onClick={toggleSave}>
              {c.saved ? "★ Saved" : "☆ Save"}
            </Button>
            <Button onClick={() => setShowProposal((s) => !s)}>Propose collaboration</Button>
          </>
        }
      />

      <div className="mb-6 flex flex-wrap items-center gap-2">
        <TrustBadge status={c.verification_status} confidence={c.confidence} />
        {c.is_demo === 1 && <Badge tone="gray">demo data</Badge>}
        {c.last_checked_at && (
          <Badge tone="gray" title="Source freshness">
            last checked {fmtDate(c.last_checked_at)}
          </Badge>
        )}
        {c.interests.map((t) => (
          <Badge key={t} tone="blue">{t}</Badge>
        ))}
      </div>

      {error && <div className="mb-4"><ErrorNote message={error} /></div>}

      {showProposal && (
        <Card className="mb-6 border-accent/40">
          <CardBody className="space-y-4">
            <h2 className="text-base font-semibold text-ink">Propose a collaboration</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Title" htmlFor="pt">
                <Input id="pt" value={proposal.title} placeholder="Joint rover perception build"
                  onChange={(e) => setProposal({ ...proposal, title: e.target.value })} />
              </Field>
              <Field label="Goal" htmlFor="pg">
                <Input id="pg" value={proposal.goal} placeholder="What you want to achieve together"
                  onChange={(e) => setProposal({ ...proposal, goal: e.target.value })} />
              </Field>
            </div>
            <Field label="Message" htmlFor="pm">
              <Textarea id="pm" value={proposal.message} placeholder="Explain the idea and why them…"
                onChange={(e) => setProposal({ ...proposal, message: e.target.value })} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Needed skills (comma-separated)" htmlFor="ps">
                <Input id="ps" value={proposal.needed_skills} placeholder="Computer Vision, ML"
                  onChange={(e) => setProposal({ ...proposal, needed_skills: e.target.value })} />
              </Field>
              <Field label="Proposed timeline" htmlFor="ptl">
                <Input id="ptl" value={proposal.proposed_timeline} placeholder="8 weeks"
                  onChange={(e) => setProposal({ ...proposal, proposed_timeline: e.target.value })} />
              </Field>
            </div>
            <div className="flex gap-2">
              <Button loading={busy} disabled={!proposal.title} onClick={sendProposal}>
                Send proposal
              </Button>
              <Button variant="ghost" onClick={() => setShowProposal(false)}>Cancel</Button>
            </div>
          </CardBody>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardBody>
              <h2 className="text-base font-semibold text-ink">About</h2>
              <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-ink-soft">
                {c.description || "No description provided."}
              </p>
              <div className="mt-5 grid gap-5 sm:grid-cols-2">
                <div>
                  <h3 className="text-sm font-medium text-emerald-700">Offers</h3>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {offers.length ? offers.map((s) => (
                      <Badge key={s.name} tone="green">{s.name}</Badge>
                    )) : <span className="text-xs text-ink-faint">Nothing listed yet.</span>}
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-accent">Looking for</h3>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {seeks.length ? seeks.map((s) => (
                      <Badge key={s.name} tone="blue">{s.name}</Badge>
                    )) : <span className="text-xs text-ink-faint">Open to ideas.</span>}
                  </div>
                </div>
              </div>
            </CardBody>
          </Card>

          {c.projects.length > 0 && (
            <Card>
              <CardBody>
                <h2 className="text-base font-semibold text-ink">Current projects</h2>
                <ul className="mt-3 space-y-3">
                  {c.projects.map((p) => (
                    <li key={p.id} className="rounded-lg border border-surface-line p-4">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-ink">{p.title}</p>
                        <Badge tone={p.status === "active" ? "green" : "gray"}>{p.status}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-ink-soft">{p.description}</p>
                      {p.needed_skills.length > 0 && (
                        <p className="mt-2 text-xs text-ink-faint">
                          Needs: {p.needed_skills.join(", ")}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              </CardBody>
            </Card>
          )}

          <Card>
            <CardBody>
              <h2 className="text-base font-semibold text-ink">Upcoming events</h2>
              {c.events.filter((e) => e.listing_status !== "past").length === 0 ? (
                <p className="mt-2 text-sm text-ink-faint">No upcoming events listed.</p>
              ) : (
                <ul className="mt-3 divide-y divide-surface-line">
                  {c.events
                    .filter((e: EventItem) => e.listing_status !== "past")
                    .map((e) => (
                      <li key={e.id} className="flex items-center justify-between gap-2 py-3">
                        <div>
                          <p className="text-sm font-medium text-ink">{e.name}</p>
                          <p className="text-xs text-ink-faint">{fmtDate(e.starts_at)}{e.city ? ` · ${e.city}` : ""}</p>
                        </div>
                        <div className="flex gap-1.5">
                          <Badge tone="blue">{e.category}</Badge>
                          {e.listing_status === "uncertain" && (
                            <Badge tone="amber" title="Source dates conflict or are missing">uncertain</Badge>
                          )}
                        </div>
                      </li>
                    ))}
                </ul>
              )}
            </CardBody>
          </Card>
        </div>

        <aside className="space-y-6">
          <Card>
            <CardBody>
              <h2 className="text-sm font-semibold text-ink">Trust & sources</h2>
              <div className="mt-3 space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-ink-faint">Source status</span>
                  <TrustBadge status={c.verification_status} confidence={c.confidence} />
                </div>
                <p className="text-xs leading-relaxed text-ink-faint">
                  Confidence is a transparent heuristic (official domain, structured details,
                  freshness) — not a calibrated probability. Only reviewers promote a record to
                  <em> verified</em>.
                </p>
                {c.sources.length === 0 ? (
                  <p className="text-xs text-ink-faint">No evidence records on file.</p>
                ) : (
                  <ul className="space-y-3">
                    {c.sources.map((s) => (
                      <li key={s.id} className="rounded-lg border border-surface-line p-3">
                        <a
                          href={s.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="break-all text-xs font-medium text-accent hover:underline"
                        >
                          {s.source_title || s.source_url}
                        </a>
                        <p className="mt-1 line-clamp-2 text-xs text-ink-faint">{s.evidence_excerpt}</p>
                        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                          <Badge tone={s.review_status === "verified" ? "green" : s.review_status === "reviewed" ? "blue" : "amber"}>
                            {s.review_status}
                          </Badge>
                          <Badge tone="gray">{s.origin}</Badge>
                          <span className="text-[11px] text-ink-faint">
                            checked {fmtDate(s.last_checked_at)}
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <h2 className="text-sm font-semibold text-ink">Members</h2>
              <ul className="mt-2 space-y-1.5">
                {c.members.map((m) => (
                  <li key={m.user_id} className="flex items-center justify-between text-sm">
                    <span className="text-ink">{m.full_name || m.username}</span>
                    <Badge tone={m.role === "organizer" ? "blue" : "gray"}>{m.role}</Badge>
                  </li>
                ))}
              </ul>
              {c.website && (
                <a
                  href={c.website}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-4 block break-all text-xs font-medium text-accent hover:underline"
                >
                  {c.website} ↗
                </a>
              )}
            </CardBody>
          </Card>
        </aside>
      </div>
    </div>
  );
}

function EmptyOrMissing() {
  return (
    <div className="py-16 text-center">
      <p className="text-lg font-semibold text-ink">Community not found</p>
      <Link to="/explore" className="mt-2 inline-block text-sm font-medium text-accent hover:underline">
        ← Back to explore
      </Link>
    </div>
  );
}
