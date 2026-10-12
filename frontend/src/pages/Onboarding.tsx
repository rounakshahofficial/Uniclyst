import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge, Button, Card, CardBody, ErrorNote, Field, Input, Select, Textarea,
} from "../components/ui";
import { get, patch } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { College, Page } from "../types";

const schema = z.object({
  full_name: z.string().min(1),
  college_id: z.coerce.number().optional(),
  bio: z.string().optional(),
  interests: z.string().optional(),
  skills: z.string().optional(),
  goals: z.string().optional(),
  website: z.string().url().optional().or(z.literal("")),
});

type FormValues = z.infer<typeof schema>;

const csv = (s?: string) =>
  (s ?? "").split(",").map((t) => t.trim()).filter(Boolean);

export default function Onboarding() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const colleges = useQuery({
    queryKey: ["colleges", "options"],
    queryFn: () => get<Page<College>>("/colleges?page_size=100"),
  });

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      full_name: user?.full_name ?? "",
      college_id: user?.college_id ?? undefined,
      bio: user?.bio ?? "",
      interests: (user?.interests ?? []).join(", "),
      skills: (user?.skills ?? []).join(", "),
      goals: user?.goals ?? "",
      website: user?.links?.website ?? "",
    },
  });

  const onSubmit = async (values: FormValues) => {
    setError(null);
    try {
      await patch("/users/me", {
        full_name: values.full_name,
        college_id: values.college_id || null,
        bio: values.bio ?? "",
        interests: csv(values.interests),
        skills: csv(values.skills),
        goals: values.goals ?? "",
        links: values.website ? { website: values.website } : {},
      });
      await refresh();
      await queryClient.invalidateQueries();
      setDone(true);
    } catch (e: any) {
      setError(e.message ?? "Could not save your profile");
    }
  };

  return (
    <div className="mx-auto max-w-2xl py-8">
      <h1 className="text-2xl font-bold tracking-tight text-ink">Tell us about yourself</h1>
      <p className="mt-1 text-sm text-ink-faint">
        Personal profiles power matching recommendations. Your community or club has its own
        organization profile — create or join one from the dashboard.
      </p>

      {error && <div className="mt-4"><ErrorNote message={error} /></div>}
      {done && (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          Profile saved.{" "}
          <button className="font-medium underline" onClick={() => navigate("/dashboard")}>
            Go to dashboard →
          </button>
        </div>
      )}

      <Card className="mt-6">
        <CardBody className="space-y-5 p-8">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <Field label="Full name" htmlFor="full_name" error={errors.full_name?.message}>
              <Input id="full_name" {...register("full_name")} />
            </Field>
            <Field label="Institution / college" htmlFor="college_id">
              <Select id="college_id" {...register("college_id")}>
                <option value="">— Select —</option>
                {colleges.data?.items.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </Select>
            </Field>
            <Field label="Short bio" htmlFor="bio">
              <Textarea id="bio" placeholder="What do you work on?" {...register("bio")} />
            </Field>
            <div className="grid gap-5 sm:grid-cols-2">
              <Field label="Interests" htmlFor="interests"
                     hint="Comma-separated, e.g. robotics, ai, design">
                <Input id="interests" {...register("interests")} />
              </Field>
              <Field label="Skills" htmlFor="skills"
                     hint="Comma-separated, e.g. Python, UI/UX">
                <Input id="skills" {...register("skills")} />
              </Field>
            </div>
            <Field label="Project goals & collaboration preferences" htmlFor="goals"
                   hint="What do you want to build with other communities?">
              <Textarea id="goals" {...register("goals")} />
            </Field>
            <Field label="Website (optional)" htmlFor="website" error={errors.website?.message}>
              <Input id="website" placeholder="https://…" {...register("website")} />
            </Field>
            <div className="flex items-center gap-3 pt-2">
              <Button type="submit" loading={isSubmitting}>Save profile</Button>
              <Button variant="ghost" type="button" onClick={() => navigate("/dashboard")}>
                Skip for now
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>

      <div className="mt-6 rounded-xl border border-surface-line bg-white/70 p-5 text-sm text-ink-soft">
        <p className="font-medium text-ink">Roles on Uniclyst</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <Badge tone="gray">Student — start here</Badge>
          <Badge tone="blue">Organizer — earned by creating a community</Badge>
          <Badge tone="green">Reviewer — assigned by an administrator</Badge>
          <Badge tone="violet">Admin — platform operations</Badge>
        </div>
      </div>
    </div>
  );
}
