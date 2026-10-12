import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button, Card, CardBody, ErrorNote, Field, Input } from "../components/ui";
import { useAuth } from "../lib/auth";

const schema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
});

type FormValues = z.infer<typeof schema>;

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: string } };
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setError(null);
    try {
      await login(values.username, values.password);
      navigate(location.state?.from ?? "/dashboard", { replace: true });
    } catch (e: any) {
      setError(e.message ?? "Sign-in failed");
    }
  };

  return (
    <div className="mx-auto max-w-md py-10">
      <Card>
        <CardBody className="p-8">
          <h1 className="text-2xl font-bold tracking-tight text-ink">Welcome back</h1>
          <p className="mt-1 text-sm text-ink-faint">
            Sign in to discover communities and manage collaborations.
          </p>

          {error && <div className="mt-4"><ErrorNote message={error} /></div>}

          <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
            <Field label="Username" htmlFor="username" error={errors.username?.message}>
              <Input id="username" autoComplete="username" {...register("username")} />
            </Field>
            <Field label="Password" htmlFor="password" error={errors.password?.message}>
              <Input id="password" type="password" autoComplete="current-password" {...register("password")} />
            </Field>
            <Button type="submit" loading={isSubmitting} className="w-full">
              Sign in
            </Button>
          </form>

          <div className="mt-6 rounded-lg border border-surface-line bg-surface px-4 py-3 text-xs text-ink-faint">
            <p className="font-medium text-ink-soft">Demo accounts</p>
            <p className="mt-1">
              <code>meera</code> / <code>demo123</code> — organizer · <code>reviewer</code> /{" "}
              <code>demo123</code> — reviewer · <code>admin</code> / <code>demo123</code> — admin
            </p>
          </div>

          <p className="mt-6 text-center text-sm text-ink-faint">
            New here?{" "}
            <Link to="/register" className="font-medium text-accent hover:underline">
              Create an account
            </Link>
          </p>
        </CardBody>
      </Card>
    </div>
  );
}
