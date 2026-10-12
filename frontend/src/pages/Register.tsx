import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { Button, Card, CardBody, ErrorNote, Field, Input, Select } from "../components/ui";
import { get } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { College, Page } from "../types";

const schema = z.object({
  username: z.string().min(3, "At least 3 characters").regex(/^[a-zA-Z0-9_.-]+$/, "Letters, numbers, _ . - only"),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "At least 8 characters"),
  full_name: z.string().min(1, "Required"),
  college_id: z.coerce.number().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function Register() {
  const { register: signup } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const colleges = useQuery({
    queryKey: ["colleges", "options"],
    queryFn: () => get<Page<College>>("/colleges?page_size=100"),
  });

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setError(null);
    try {
      await signup({
        username: values.username,
        email: values.email,
        password: values.password,
        full_name: values.full_name,
        college_id: values.college_id || undefined,
      });
      navigate("/onboarding", { replace: true });
    } catch (e: any) {
      setError(e.message ?? "Registration failed");
    }
  };

  return (
    <div className="mx-auto max-w-md py-10">
      <Card>
        <CardBody className="p-8">
          <h1 className="text-2xl font-bold tracking-tight text-ink">Create your account</h1>
          <p className="mt-1 text-sm text-ink-faint">
            Every public account starts as a <strong>student</strong>. Organizer status is earned by
            creating a community; reviewer/admin roles are assigned only by platform administrators.
          </p>

          {error && <div className="mt-4"><ErrorNote message={error} /></div>}

          <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
            <Field label="Full name" htmlFor="full_name" error={errors.full_name?.message}>
              <Input id="full_name" autoComplete="name" {...register("full_name")} />
            </Field>
            <Field label="Username" htmlFor="username" error={errors.username?.message}>
              <Input id="username" autoComplete="username" {...register("username")} />
            </Field>
            <Field label="Email" htmlFor="email" error={errors.email?.message}>
              <Input id="email" type="email" autoComplete="email" {...register("email")} />
            </Field>
            <Field label="Password" htmlFor="password" error={errors.password?.message}
                   hint="At least 8 characters">
              <Input id="password" type="password" autoComplete="new-password" {...register("password")} />
            </Field>
            <Field label="College (optional)" htmlFor="college_id">
              <Select id="college_id" {...register("college_id")}>
                <option value="">— Select later —</option>
                {colleges.data?.items.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.short_name})
                  </option>
                ))}
              </Select>
            </Field>
            <Button type="submit" loading={isSubmitting} className="w-full">
              Create account
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-ink-faint">
            Already have an account?{" "}
            <Link to="/login" className="font-medium text-accent hover:underline">
              Sign in
            </Link>
          </p>
        </CardBody>
      </Card>
    </div>
  );
}
