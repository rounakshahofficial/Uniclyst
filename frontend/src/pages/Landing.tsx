import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Badge, Button, Card, CardBody } from "../components/ui";
import { useAuth } from "../lib/auth";
import { get } from "../lib/api";
import type { College, Page } from "../types";

const steps = [
  {
    title: "Discover",
    text: "Explore student communities across colleges — with every profile linked to its public source and marked discovered, reviewed, or verified.",
  },
  {
    title: "Match",
    text: "Describe your project and get ranked, explainable partner recommendations: complementary skills, shared goals, travel feasibility and profile freshness.",
  },
  {
    title: "Collaborate",
    text: "Send a proposal, get an explicit acceptance, and track the joint work in a shared workspace with milestones — partnerships exist only when both sides agree.",
  },
];

export default function Landing() {
  const { user } = useAuth();
  const colleges = useQuery({
    queryKey: ["colleges", "landing"],
    queryFn: () => get<Page<College>>("/colleges?page_size=50"),
    retry: false,
  });

  const collegeCount = colleges.data?.total;
  const communityCount = colleges.data?.items.reduce((s, c) => s + c.community_count, 0);

  return (
    <div className="space-y-16 pb-8">
      {/* Hero */}
      <section className="pt-10 sm:pt-16">
        <div className="mx-auto max-w-3xl text-center">
          <Badge tone="blue">AZINHACK 2026 · AI-powered inter-college collaboration</Badge>
          <h1 className="mt-5 text-4xl font-extrabold tracking-tight text-ink sm:text-5xl">
            Connect beyond <span className="text-accent">boundaries</span>.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-ink-soft">
            Student communities work in isolation — scattered across Instagram pages, WhatsApp
            groups and college websites. Uniclyst turns them into a connected network: source-backed
            discovery, explainable matching, and collaborations that actually get accepted.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link to={user ? "/dashboard" : "/register"}>
              <Button size="md">{user ? "Go to dashboard" : "Create your account"}</Button>
            </Link>
            <Link to="/explore">
              <Button variant="secondary" size="md">Explore communities</Button>
            </Link>
          </div>
          <p className="mt-4 text-xs text-ink-faint">
            Sample statistics below come from the demo dataset (clearly marked seed data), not live
            platform metrics.
          </p>
        </div>

        {/* Stats strip */}
        <div className="mx-auto mt-10 grid max-w-3xl grid-cols-3 gap-4">
          {[
            { value: collegeCount ?? "—", label: "colleges in the graph" },
            { value: communityCount ?? "—", label: "demo communities" },
            { value: "3", label: "trust levels, never auto-verified" },
          ].map((s) => (
            <Card key={s.label}>
              <CardBody className="text-center">
                <div className="text-3xl font-bold text-accent">{s.value}</div>
                <div className="mt-1 text-xs text-ink-faint">{s.label}</div>
              </CardBody>
            </Card>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section>
        <h2 className="text-center text-2xl font-bold tracking-tight text-ink">
          How cross-college collaboration works
        </h2>
        <div className="mt-8 grid gap-6 md:grid-cols-3">
          {steps.map((s, i) => (
            <Card key={s.title} className="relative">
              <CardBody>
                <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-accent-soft text-sm font-bold text-accent">
                  {i + 1}
                </div>
                <h3 className="text-lg font-semibold text-ink">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-soft">{s.text}</p>
              </CardBody>
            </Card>
          ))}
        </div>
      </section>

      {/* Differentiators */}
      <section>
        <div className="rounded-2xl bg-ink px-8 py-12 text-white">
          <h2 className="text-center text-2xl font-bold tracking-tight">
            Not a directory. Not an event board.
          </h2>
          <div className="mx-auto mt-8 grid max-w-4xl gap-8 text-sm leading-relaxed text-slate-300 sm:grid-cols-2">
            <div>
              <h3 className="font-semibold text-white">Evidence-backed discovery</h3>
              <p className="mt-1">
                A Community Scout (TinyFish Search + Fetch) finds public pages and extracts records —
                each one keeps its source URL, retrieval timestamps and confidence notes. Reviewers
                promote discovered → reviewed → verified. An accessible page is never automatically
                true.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-white">Explainable matching</h3>
              <p className="mt-1">
                Every recommendation shows its score breakdown — interest compatibility,
                complementary skills, goal alignment, geography and freshness — plus plain-language
                reasons and honest uncertainty notes.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-white">Collaboration conversion</h3>
              <p className="mt-1">
                Proposals can be accepted, rejected or withdrawn. Only acceptance creates a shared
                workspace with milestones — the platform tracks whether matches become real
                partnerships.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-white">Trust signals built in</h3>
              <p className="mt-1">
                Discovered ≠ verified. Follower counts are not evidence of activity. Stale and
                conflicting sources are flagged — so you can tell a scraped lead from a genuinely
                active community.
              </p>
            </div>
          </div>
          <div className="mt-10 text-center">
            <Link to={user ? "/matches" : "/register"}>
              <Button size="md">{user ? "Find your match" : "Start connecting"}</Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Colleges */}
      {colleges.data && colleges.data.items.length > 0 && (
        <section>
          <h2 className="text-center text-2xl font-bold tracking-tight text-ink">
            Colleges in the Campus Graph
            <Badge tone="gray">demo data</Badge>
          </h2>
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            {colleges.data.items.map((c) => (
              <Link key={c.id} to={`/explore?college=${c.id}`}>
                <span className="rounded-full border border-surface-line bg-white px-4 py-1.5 text-sm text-ink-soft shadow-sm transition-colors hover:border-accent hover:text-accent">
                  {c.short_name} · {c.city}
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
