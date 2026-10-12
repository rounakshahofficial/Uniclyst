import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import CommunityCard from "../components/CommunityCard";
import {
  Button, EmptyState, Field, Input, PageHeader, Select, Spinner,
} from "../components/ui";
import { get } from "../lib/api";
import type { College, Community, Page } from "../types";

export default function Explore() {
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [city, setCity] = useState(params.get("city") ?? "");
  const [category, setCategory] = useState(params.get("category") ?? "");
  const [skill, setSkill] = useState(params.get("skill") ?? "");
  const [verification, setVerification] = useState(params.get("verification") ?? "");
  const [sort, setSort] = useState("relevance");
  const [page, setPage] = useState(1);

  const colleges = useQuery({
    queryKey: ["colleges", "options"],
    queryFn: () => get<Page<College>>("/colleges?page_size=100"),
  });
  const collegeParam = params.get("college");

  const query = new URLSearchParams();
  if (q) query.set("q", q);
  if (city) query.set("city", city);
  if (category) query.set("category", category);
  if (skill) query.set("skill", skill);
  if (verification) query.set("verification", verification);
  if (collegeParam) query.set("college_id", collegeParam);
  query.set("sort", sort);
  query.set("page", String(page));
  query.set("page_size", "12");

  const communities = useQuery({
    queryKey: ["communities", query.toString()],
    queryFn: () => get<Page<Community>>(`/communities?${query.toString()}`),
    placeholderData: (prev) => prev,
  });

  const apply = () => {
    setPage(1);
    const next = new URLSearchParams();
    if (q) next.set("q", q);
    if (city) next.set("city", city);
    if (category) next.set("category", category);
    if (skill) next.set("skill", skill);
    if (verification) next.set("verification", verification);
    if (collegeParam) next.set("college", collegeParam);
    setParams(next);
  };

  const collegeName = collegeParam
    ? colleges.data?.items.find((c) => String(c.id) === collegeParam)?.short_name
    : null;

  return (
    <div>
      <PageHeader
        title="Explore communities"
        subtitle="Search across colleges, skills and interests. Every profile shows its source status — discovered records are never presented as verified."
      />

      <div className="mb-6 rounded-xl border border-surface-line bg-white p-4 shadow-card">
        <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-6">
          <div className="lg:col-span-2">
            <Field label="Search" htmlFor="q">
              <Input
                id="q"
                placeholder="Robotics, design, CTF…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && apply()}
              />
            </Field>
          </div>
          <Field label="City" htmlFor="city">
            <Select id="city" value={city} onChange={(e) => setCity(e.target.value)}>
              <option value="">All</option>
              <option value="Delhi">Delhi</option>
              <option value="Noida">Noida</option>
              <option value="Greater Noida">Greater Noida</option>
            </Select>
          </Field>
          <Field label="Category" htmlFor="category">
            <Select id="category" value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">All</option>
              <option value="Technical">Technical</option>
              <option value="Cultural">Cultural</option>
              <option value="Entrepreneurship">Entrepreneurship</option>
            </Select>
          </Field>
          <Field label="Skill" htmlFor="skill">
            <Input
              id="skill"
              placeholder="e.g. Computer Vision"
              value={skill}
              onChange={(e) => setSkill(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && apply()}
            />
          </Field>
          <Field label="Source status" htmlFor="verification">
            <Select
              id="verification"
              value={verification}
              onChange={(e) => setVerification(e.target.value)}
            >
              <option value="">Any</option>
              <option value="verified">Verified</option>
              <option value="reviewed">Reviewed</option>
              <option value="discovered">Discovered</option>
            </Select>
          </Field>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button onClick={apply} size="sm">Apply filters</Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setQ(""); setCity(""); setCategory(""); setSkill(""); setVerification("");
              setParams(collegeParam ? { college: collegeParam } : {});
              setPage(1);
            }}
          >
            Reset
          </Button>
          <div className="ml-auto flex items-center gap-2">
            {collegeName && (
              <span className="rounded-full bg-accent-soft px-3 py-1 text-xs font-medium text-accent">
                College: {collegeName} ✕
              </span>
            )}
            <Select value={sort} onChange={(e) => setSort(e.target.value)} className="w-auto">
              <option value="relevance">Sort: A–Z</option>
              <option value="updated">Recently updated</option>
              <option value="confidence">Confidence</option>
            </Select>
          </div>
        </div>
      </div>

      {communities.isLoading && <Spinner label="Loading communities…" />}

      {communities.data && communities.data.items.length === 0 && (
        <EmptyState
          title="No communities match these filters"
          description="Try a broader search, or run the Community Scout to discover new communities from public sources."
        />
      )}

      {communities.data && communities.data.items.length > 0 && (
        <>
          <p className="mb-3 text-sm text-ink-faint">
            {communities.data.total} communit{communities.data.total === 1 ? "y" : "ies"}
          </p>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {communities.data.items.map((c) => (
              <CommunityCard key={c.id} community={c} />
            ))}
          </div>

          {communities.data.pages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-3">
              <Button
                variant="secondary"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                ← Previous
              </Button>
              <span className="text-sm text-ink-faint">
                Page {communities.data.page} of {communities.data.pages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= communities.data.pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next →
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
