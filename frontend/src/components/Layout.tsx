import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Button } from "./ui";

const navClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
    isActive ? "bg-accent-soft text-accent" : "text-ink-soft hover:bg-slate-100 hover:text-ink"
  }`;

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-surface-line bg-white/85 backdrop-blur">
        <div className="container-page flex h-16 items-center justify-between gap-4">
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent font-bold text-white">
                U
              </span>
              <span className="text-lg font-bold tracking-tight text-ink">
                Uniclyst
              </span>
            </Link>
            {user && (
              <nav className="hidden items-center gap-1 md:flex">
                <NavLink to="/dashboard" className={navClass}>Dashboard</NavLink>
                <NavLink to="/explore" className={navClass}>Explore</NavLink>
                <NavLink to="/matches" className={navClass}>Matches</NavLink>
                <NavLink to="/discovery" className={navClass}>Discovery</NavLink>
                <NavLink to="/collaborations" className={navClass}>Collaborations</NavLink>
              </nav>
            )}
          </div>
          <div className="flex items-center gap-2">
            {user ? (
              <>
                <div className="hidden text-right sm:block">
                  <div className="text-sm font-medium leading-tight text-ink">{user.full_name}</div>
                  <div className="text-xs capitalize leading-tight text-ink-faint">{user.role}</div>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={async () => {
                    await logout();
                    navigate("/");
                  }}
                >
                  Sign out
                </Button>
              </>
            ) : (
              <>
                <Button variant="ghost" size="sm" onClick={() => navigate("/login")}>
                  Sign in
                </Button>
                <Button size="sm" onClick={() => navigate("/register")}>
                  Get started
                </Button>
              </>
            )}
          </div>
        </div>
        {user && (
          <nav className="flex gap-1 overflow-x-auto border-t border-surface-line px-4 py-2 md:hidden">
            <NavLink to="/dashboard" className={navClass}>Dashboard</NavLink>
            <NavLink to="/explore" className={navClass}>Explore</NavLink>
            <NavLink to="/matches" className={navClass}>Matches</NavLink>
            <NavLink to="/discovery" className={navClass}>Discovery</NavLink>
            <NavLink to="/collaborations" className={navClass}>Collaborations</NavLink>
          </nav>
        )}
      </header>

      <main className="container-page flex-1 py-8">{children}</main>

      <footer className="border-t border-surface-line bg-white">
        <div className="container-page flex flex-col items-start justify-between gap-2 py-6 text-xs text-ink-faint sm:flex-row sm:items-center">
          <p>
            <span className="font-semibold text-ink-soft">Uniclyst</span> — Connect Beyond
            Boundaries. Built for AZINHACK 2026.
          </p>
          <p>Discovered records are never auto-verified · API docs at /docs</p>
        </div>
      </footer>
    </div>
  );
}
