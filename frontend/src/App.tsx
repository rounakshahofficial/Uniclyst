import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Layout from "./components/Layout";
import { Spinner } from "./components/ui";
import { useAuth } from "./lib/auth";
import CommunityProfile from "./pages/CommunityProfile";
import Collaborations from "./pages/Collaborations";
import Dashboard from "./pages/Dashboard";
import Discovery from "./pages/Discovery";
import Explore from "./pages/Explore";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Matches from "./pages/Matches";
import Onboarding from "./pages/Onboarding";
import Register from "./pages/Register";
import Workspace from "./pages/Workspace";

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <Spinner label="Checking your session…" />;
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  return <>{children}</>;
}

export default function App() {
  const { loading } = useAuth();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner label="Starting Uniclyst…" />
      </div>
    );
  }
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/onboarding"
          element={
            <Protected>
              <Onboarding />
            </Protected>
          }
        />
        <Route
          path="/dashboard"
          element={
            <Protected>
              <Dashboard />
            </Protected>
          }
        />
        <Route path="/explore" element={<Explore />} />
        <Route path="/communities/:id" element={<CommunityProfile />} />
        <Route
          path="/matches"
          element={
            <Protected>
              <Matches />
            </Protected>
          }
        />
        <Route
          path="/discovery"
          element={
            <Protected>
              <Discovery />
            </Protected>
          }
        />
        <Route
          path="/collaborations"
          element={
            <Protected>
              <Collaborations />
            </Protected>
          }
        />
        <Route
          path="/collaborations/:id"
          element={
            <Protected>
              <Workspace />
            </Protected>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
