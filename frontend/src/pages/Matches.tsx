import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Badge, Button, Card, CardBody, EmptyState, ErrorNote, Field, Input, PageHeader, ScoreBar,
  Spinner, Textarea, TrustBadge,
} from "../components/ui";
import { get, post } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Community, MatchResponse, Page } from "../types";

const componentLabels: Record<string, { label: string; weight: string; tone: string }> = {
  interest: { label: "Interest compatibility", weight: "25%", tone: "bg-indigo-500" },
  skills: { label: "Complementary skills", weight: "35%", tone: "bg-accent" },
  goal: { label: "Goal alignment", weight: "25%", tone: "bg-violet-500" },
  geography: { label: "Geography", weight: "10%", tone: "bg-emerald-500" },
  profile: { label: "Profile & freshness", weight: "5%", tone: "bg-amber-500" },
};

export default function Matches() {
  const { user } = useAuth();
  const [communityId, setCommunityId] = useState<number | null>(null);
  const [goal, setGoal] = useState("");
  const [skills, setSkills] = useState("");
  const [result, setResult] = useState<MatchResponse | null>(null);

  // My communities: ones where I'm a member
  const mine = useQuery({
    queryKey: ["communities", "mine"],
    queryFn: async () => {
      const page = await get<Page<Community>>("/communities?page_size=50");
      return page.items.filter((c) => c.members.some((m) => m.user_id === user?.id));
    },
    enabled: !!user,
  });

  const runMatch = useMutation({
    mutationFn: async () => {
      const params = new URLSearchParams({ community_id: String(communityId) });
      if (goal) params.set("goal", goal);
      if (skills) params.set("needed_skills", skills);
      params.set("limit", "6");
      return get<MatchResponse>(`/matches?${params.toString()}`);
    },
    onSuccess: (data) => setResult(data),
  });

  return (
    <div>
      <PageHeader
        title="Collaboration Matchmaker"
        subtitle="Describe what you're building. The engine ranks potential partners and explains every score — complementary capabilities matter more than similar names."
      />

      <Card className="mb-8">
        <CardBody>
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Your community" htmlFor="mc">
              <select
                id="mc"
                className="input"
                value={communityId ?? ""}
                onChange={(e) => setCommunityId(Number(e.target.value))}
              >
                <option value="">— Select —</option>
                {mine.data?.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </Field>
            <Field
              label="Skills your partner should bring"
              htmlFor="ms"
              hint="Comma-separated, e.g. Computer Vision, Machine Learning"
            >
              <Input id="ms" value={skills} onChange={(e) => setSkills(e.target.value)} />
            </Field>
          </div>
          <div className="mt-4">
            <Field label="Project goal" htmlFor="mg" hint="What do you want to build together?">
              <Textarea
                id="mg"
                value={goal}
                placeholder="e.g. An autonomous rover that needs a computer-vision perception stack"
                onChange={(e) => setGoal(e.target.value)}
              />
            </Field>
          </div>
          <div className="mt-4 flex items-center gap-3">
            <Button
              loading={runMatch.isPending}
              disabled={!communityId}
              onClick={() => runMatch.mutate()}
            >
              Find matches
            </Button>
            {runMatch.isError && (
              <span className="text-sm text-red-600">{(runMatch.error as Error).message}</span>
            )}
          </div>
          {!user && (
            <p className="mt-3 text-xs text-ink-faint">
              <Link to="/login" className="text-accent">Sign in</Link> to see matches for your own
              communities.
            </p>
          )}
        </CardBody>
      </Card>

      {runMatch.isPending && <Spinner label="Scoring candidate partners…" />}

      {result && (
        <>
          <div className="mb-5 flex flex-wrap items-center gap-2 text-xs text-ink-faint">
            <Badge tone="blue">{result.formula}</Badge>
            {result.needed_skills.length > 0 && (
              <span>needs: {result.needed_skills.join(", ")}</span>
            )}
            {result.goal && <span>goal: “{result.goal}”</span>}
          </div>

          {result.matches.length === 0 ? (
            <EmptyState
              title="No relevant partners found"
              description="Try relaxing the required skills or run the Community Scout to discover more communities first."
            />
          ) : (
            <div className="space-y-5">
              {result.matches.map((m, i) => (
                <Card key={m.community.id} className={i === 0 ? "border-accent/50" : ""}>
                  <CardBody>
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          {i === 0 && <Badge tone="blue">Best match</Badge>}
                          <Link
                            to={`/communities/${m.community.id}`}
                            className="text-lg font-semibold text-ink hover:text-accent hover:underline"
                          >
                            {m.community.name}
                          </Link>
                        </div>
                        <p className="mt-0.5 text-xs text-ink-faint">
                          {m.community.college_short ?? m.community.college_name}
                          {m.community.city ? ` · ${m.community.city}` : ""}
                        </p>
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <TrustBadge
                            status={m.freshness.verification_status}
                            confidence={m.freshness.confidence}
                          />
                          {m.strongest_factors.map((f) => (
                            <Badge key={f} tone="violet">strong: {f}</Badge>
                          ))}
                        </div>
                      </div>
                      <div className="rounded-xl bg-accent-soft px-4 py-2 text-center">
                        <div className="text-2xl font-bold text-accent">
                          {Math.round(m.score.total)}
                        </div>
                        <div className="text-[10px] font-medium uppercase tracking-wide text-accent/80">
                          match score
                        </div>
                      </div>
                    </div>

                    <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                      {(["interest", "skills", "goal", "geography", "profile"] as const).map((key) => {
                        const cfg = componentLabels[key];
                        return (
                          <ScoreBar
                            key={key}
                            label={cfg.label}
                            weight={cfg.weight}
                            value={m.score[key]}
                            tone={cfg.tone}
                          />
                        );
                      })}
                    </div>

                    <div className="mt-5 rounded-lg bg-surface p-4">
                      <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
                        Why this match
                      </h3>
                      <ul className="mt-2 space-y-1 text-sm text-ink-soft">
                        {m.reasons.map((r, idx) => (
                          <li key={idx} className="flex gap-2">
                            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent/60" />
                            {r}
                          </li>
                        ))}
                      </ul>
                    </div>

                    {(m.uncertainty || m.missing_skills.length > 0) && (
                      <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                        {m.missing_skills.length > 0 && (
                          <p>
                            <strong>Not listed by them:</strong> {m.missing_skills.join(", ")}.
                          </p>
                        )}
                        {m.uncertainty && <p className="mt-1">{m.uncertainty}</p>}
                      </div>
                    )}

                    <div className="mt-4 flex flex-wrap items-center gap-2">
                      <Link to={`/communities/${m.community.id}`}>
                        <Button variant="secondary" size="sm">View profile</Button>
                      </Link>
                      <ProposalButton
                        targetId={m.community.id}
                        targetName={m.community.name}
                        defaultTitle={`Collaboration with ${m.community.name}`}
                        defaultGoal={result.goal}
                        defaultSkills={m.missing_skills.concat(result.needed_skills).slice(0, 4)}
                      />
                    </div>
                  </CardBody>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {!result && !runMatch.isPending && (
        <EmptyState
          title="Get ranked, explainable partner recommendations"
          description="Select your community, describe the project goal and the skills you need — the engine scores interest compatibility (25%), complementary skills (35%), goal alignment (25%), geography (10%) and profile freshness (5%)."
        />
      )}
    </div>
  );
}

function ProposalButton({
  targetId,
  targetName,
  defaultTitle,
  defaultGoal,
  defaultSkills,
}: {
  targetId: number;
  targetName: string;
  defaultTitle: string;
  defaultGoal: string;
  defaultSkills: string[];
}) {
  const { user } = useAuth();
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = useMutation({
    mutationFn: async () => {
      const page = await get<Page<Community>>("/communities?page_size=50");
      const mine = page.items.find((c) =>
        c.members.some((m) => m.user_id === user?.id && m.role === "organizer")
      );
      if (!mine) throw new Error("Create or organize a community first — proposals are sent on behalf of a community.");
      await post("/collaboration-requests", {
        requester_community_id: mine.id,
        target_community_id: targetId,
        title: defaultTitle,
        goal: defaultGoal,
        message: `We'd like to collaborate with ${targetName}.`,
        needed_skills: defaultSkills,
        proposed_timeline: "",
      });
    },
    onSuccess: () => setSent(true),
    onError: (e: any) => setError(e.message),
  });

  if (!user) return null;
  if (sent)
    return <Badge tone="green">Proposal sent — track it in Collaborations</Badge>;

  return (
    <>
      <Button size="sm" loading={send.isPending} onClick={() => send.mutate()}>
        Send proposal
      </Button>
      {error && <span className="text-xs text-red-600">{error}</span>}
    </>
  );
}
