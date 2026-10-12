import { Link, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import CommunityCard from "../components/CommunityCard";
import {
  Badge, Button, Card, CardBody, EmptyState, PageHeader, Spinner, TrustBadge,
} from "../components/ui";
import { get, post } from "../lib/api";
import { useAuth } from "../lib/auth";
import type {
  CollaborationRequest, Community, DiscoveryJob, EventItem, Page,
} from "../types";

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const saved = useQuery({ queryKey: ["saved"], queryFn: () => get<Community[]>("/users/me/saved") });
  const requests = useQuery({
    queryKey: ["requests"],
    queryFn: () => get<{ items: CollaborationRequest[] }>("/collaboration-requests"),
  });
  const events = useQuery({
    queryKey: ["events", "dash"],
    queryFn: () => get<Page<EventItem>>("/events?page_size=5"),
  });
  const jobs = useQuery({
    queryKey: ["discovery-jobs"],
    queryFn: () => get<{ items: DiscoveryJob[] }>("/discovery/jobs"),
  });
  const recommended = useQuery({
    queryKey: ["communities", "recommended"],
    queryFn: () => get<Page<Community>>("/communities?page_size=3&sort=confidence"),
  });

  const pendingIncoming = requests.data?.items.filter((r) => r.direction === "incoming" && r.status === "pending") ?? [];
  const pendingOutgoing = requests.data?.items.filter((r) => r.direction === "outgoing" && r.status === "pending") ?? [];

  return (
    <div>
      <PageHeader
        title={`Welcome back, ${user?.full_name.split(" ")[0] ?? "there"}`}
        subtitle="Your collaboration hub: recommendations, opportunities, requests and discovery activity."
        actions={
          <>
            <Button onClick={() => navigate("/matches")}>Find collaborators</Button>
            <Button variant="secondary" onClick={() => navigate("/discovery")}>Run Community Scout</Button>
          </>
        }
      />

      {/* Incoming requests — the actionable core */}
      {pendingIncoming.length > 0 && (
        <div className="mb-6 rounded-xl border border-accent/30 bg-accent-soft/60 p-5">
          <h2 className="text-sm font-semibold text-accent">
            {pendingIncoming.length} incoming collaboration proposal{pendingIncoming.length > 1 ? "s" : ""}
          </h2>
          <div className="mt-3 space-y-2">
            {pendingIncoming.slice(0, 3).map((r) => (
              <div key={r.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-ink">{r.title}</p>
                  <p className="text-xs text-ink-faint">
                    From {r.requester_community_name} → {r.target_community_name}
                  </p>
                </div>
                <Link to="/collaborations">
                  <Button size="sm">Review & respond</Button>
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recommended */}
        <section className="lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-ink">Communities to know</h2>
            <Link to="/explore" className="text-sm font-medium text-accent hover:underline">
              Explore all →
            </Link>
          </div>
          {recommended.isLoading ? (
            <Spinner />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {recommended.data?.items.map((c) => (
                <CommunityCard key={c.id} community={c} />
              ))}
            </div>
          )}

          {/* Events */}
          <h2 className="mb-3 mt-8 text-lg font-semibold text-ink">Upcoming opportunities</h2>
          <Card>
            {events.data?.items.length === 0 ? (
              <CardBody>
                <EmptyState
                  title="No upcoming events"
                  description="Events published by communities will appear here."
                />
              </CardBody>
            ) : (
              <ul className="divide-y divide-surface-line">
                {events.data?.items.map((ev) => (
                  <li key={ev.id} className="flex items-center justify-between gap-3 px-5 py-4">
                    <div>
                      <p className="text-sm font-medium text-ink">{ev.name}</p>
                      <p className="text-xs text-ink-faint">
                        {ev.community_name} · {fmtDate(ev.starts_at)}
                        {ev.city ? ` · ${ev.city}` : ""} {ev.is_online ? "· Online" : ""}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge tone={ev.listing_status === "uncertain" ? "amber" : "blue"}>
                        {ev.category}
                      </Badge>
                      {ev.listing_status === "uncertain" && (
                        <Badge tone="amber" title="Source dates conflict or are missing">uncertain</Badge>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </section>

        {/* Side column */}
        <aside className="space-y-6">
          <Card>
            <CardBody>
              <h2 className="text-sm font-semibold text-ink">Quick actions</h2>
              <div className="mt-3 space-y-2">
                <Button className="w-full" onClick={() => navigate("/matches")}>
                  Start a collaboration match
                </Button>
                <Button variant="secondary" className="w-full" onClick={() => navigate("/discovery")}>
                  Discover new communities
                </Button>
                <Button variant="secondary" className="w-full" onClick={() => navigate("/onboarding")}>
                  Complete your profile
                </Button>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <h2 className="text-sm font-semibold text-ink">Your requests</h2>
              <div className="mt-3 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-ink-faint">Incoming, pending</span>
                  <span className="font-semibold text-ink">{pendingIncoming.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-ink-faint">Outgoing, pending</span>
                  <span className="font-semibold text-ink">{pendingOutgoing.length}</span>
                </div>
                <Link to="/collaborations" className="mt-2 block text-sm font-medium text-accent hover:underline">
                  Manage collaborations →
                </Link>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <h2 className="text-sm font-semibold text-ink">Saved communities</h2>
              {saved.data?.length === 0 ? (
                <p className="mt-2 text-sm text-ink-faint">
                  Nothing saved yet — bookmark communities you want to revisit.
                </p>
              ) : (
                <ul className="mt-2 space-y-2">
                  {saved.data?.slice(0, 5).map((c) => (
                    <li key={c.id}>
                      <Link to={`/communities/${c.id}`} className="text-sm font-medium text-ink hover:text-accent">
                        {c.name}
                      </Link>
                      <div className="mt-0.5"><TrustBadge status={c.verification_status} /></div>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <h2 className="text-sm font-semibold text-ink">Recent discovery activity</h2>
              {jobs.data?.items.length === 0 ? (
                <p className="mt-2 text-sm text-ink-faint">No scout runs yet.</p>
              ) : (
                <ul className="mt-2 space-y-2">
                  {jobs.data?.items.slice(0, 4).map((j) => (
                    <li key={j.id} className="text-sm">
                      <span className="font-medium text-ink">{j.query}</span>
                      <div className="text-xs text-ink-faint">
                        <Badge tone={j.mode === "live" ? "green" : "gray"}>{j.mode}</Badge>{" "}
                        {j.result_count} records · {j.status}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        </aside>
      </div>
    </div>
  );
}
