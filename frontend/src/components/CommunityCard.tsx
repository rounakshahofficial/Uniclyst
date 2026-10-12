import { Link } from "react-router-dom";
import type { Community } from "../types";
import { Badge, Card, CardBody, TrustBadge } from "./ui";

export default function CommunityCard({
  community,
  footer,
}: {
  community: Community;
  footer?: React.ReactNode;
}) {
  const offers = community.skills.filter((s) => s.kind === "offers").map((s) => s.name);
  const seeks = community.skills.filter((s) => s.kind === "seeks").map((s) => s.name);

  return (
    <Card className="flex h-full flex-col transition-shadow hover:shadow-pop">
      <CardBody className="flex h-full flex-col gap-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <Link
              to={`/communities/${community.id}`}
              className="text-base font-semibold text-ink hover:text-accent hover:underline"
            >
              {community.name}
            </Link>
            <p className="mt-0.5 text-xs text-ink-faint">
              {community.college_short ?? community.college_name}
              {community.city ? ` · ${community.city}` : ""}
            </p>
          </div>
          <TrustBadge status={community.verification_status} confidence={community.confidence} />
        </div>

        <p className="line-clamp-2 text-sm text-ink-soft">
          {community.description || "No description yet."}
        </p>

        <div className="flex flex-wrap gap-1.5">
          {community.interests.slice(0, 4).map((t) => (
            <Badge key={t} tone="blue">{t}</Badge>
          ))}
          {community.is_demo === 1 && <Badge tone="gray" title="Clearly labeled demo/seed data">demo</Badge>}
        </div>

        {(offers.length > 0 || seeks.length > 0) && (
          <div className="mt-auto space-y-1 border-t border-surface-line pt-3 text-xs">
            {offers.length > 0 && (
              <p className="text-ink-soft">
                <span className="font-medium text-emerald-700">Offers:</span> {offers.slice(0, 5).join(", ")}
              </p>
            )}
            {seeks.length > 0 && (
              <p className="text-ink-soft">
                <span className="font-medium text-accent">Seeks:</span> {seeks.slice(0, 5).join(", ")}
              </p>
            )}
          </div>
        )}

        {footer && <div className="pt-1">{footer}</div>}
      </CardBody>
    </Card>
  );
}
