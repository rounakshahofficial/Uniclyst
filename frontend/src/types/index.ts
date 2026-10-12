/** API types mirroring the backend Pydantic schemas. */

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: "student" | "organizer" | "reviewer" | "admin";
  college_id: number | null;
  bio: string;
  interests: string[];
  skills: string[];
  goals: string;
  links: Record<string, string>;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface College {
  id: number;
  name: string;
  short_name: string;
  city: string;
  region: string;
  country: string;
  website: string | null;
  lat: number | null;
  lng: number | null;
  description: string;
  community_count: number;
}

export interface SkillAssignment {
  name: string;
  kind: "offers" | "seeks";
}

export interface DiscoverySource {
  id: number;
  source_url: string;
  source_title: string;
  evidence_excerpt: string;
  retrieved_at: string;
  last_checked_at: string;
  review_status: "discovered" | "reviewed" | "verified";
  confidence: number;
  review_note: string;
  origin: "scout" | "seed" | "manual";
  extracted: Record<string, unknown>;
}

export interface EventItem {
  id: number;
  community_id: number;
  name: string;
  description: string;
  category: string;
  starts_at: string;
  ends_at: string | null;
  city: string | null;
  is_online: number;
  event_url: string | null;
  source_url: string | null;
  last_checked_at: string | null;
  listing_status: string;
  confidence: number;
  community_name: string | null;
}

export interface Community {
  id: number;
  name: string;
  slug: string;
  college_id: number;
  college_name: string | null;
  college_short: string | null;
  city: string | null;
  description: string;
  category: string;
  interests: string[];
  website: string | null;
  social_links: Record<string, string>;
  verification_status: "discovered" | "reviewed" | "verified";
  confidence: number;
  last_checked_at: string | null;
  is_demo: number;
  created_by: number | null;
  created_at: string | null;
  skills: SkillAssignment[];
  members: { user_id: number; username: string; full_name: string; role: string }[];
  projects: { id: number; title: string; description: string; status: string; needed_skills: string[] }[];
  events: EventItem[];
  sources: DiscoverySource[];
  saved: boolean;
}

export interface ScoreBreakdown {
  interest: number;
  skills: number;
  goal: number;
  geography: number;
  profile: number;
  total: number;
}

export interface MatchResult {
  community: Community;
  score: ScoreBreakdown;
  reasons: string[];
  strongest_factors: string[];
  missing_skills: string[];
  freshness: {
    verification_status: string;
    confidence: number;
    source_count: number;
    last_checked_at: string | null;
  };
  uncertainty: string | null;
}

export interface MatchResponse {
  requester: Community;
  goal: string;
  needed_skills: string[];
  formula: string;
  weights: Record<string, number>;
  matches: MatchResult[];
}

export interface DiscoveryJob {
  id: number;
  query: string;
  region: string;
  interests: string[];
  status: string;
  mode: "live" | "demo";
  result_count: number;
  error: string;
  notes: string[];
  created_by: number | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface ScoutCandidate {
  organization_name: string;
  college: string;
  city: string;
  interests: string[];
  skills: string[];
  official_url: string | null;
  event_names: string[];
  confidence: number;
  verification_status: string;
  missing_or_conflicting: string;
  dedupe_match_org_id: number | null;
}

export interface CollaborationRequest {
  id: number;
  requester_community_id: number;
  target_community_id: number;
  requester_community_name: string | null;
  target_community_name: string | null;
  requester_user_id: number | null;
  title: string;
  goal: string;
  message: string;
  needed_skills: string[];
  proposed_timeline: string;
  status: "pending" | "accepted" | "rejected" | "withdrawn";
  response_note: string;
  created_at: string;
  responded_at: string | null;
  direction: "incoming" | "outgoing";
}

export interface Milestone {
  id: number;
  collaboration_id: number;
  title: string;
  description: string;
  due_date: string | null;
  status: "pending" | "reached";
  order_index: number;
}

export interface Collaboration {
  id: number;
  request_id: number;
  title: string;
  goal: string;
  status: "active" | "completed" | "cancelled";
  summary: string;
  started_at: string;
  completed_at: string | null;
  requester_community_id: number | null;
  target_community_id: number | null;
  requester_community_name: string | null;
  target_community_name: string | null;
  members: {
    user_id: number;
    username: string;
    full_name: string;
    community_id: number;
    community_name: string | null;
    role: string;
  }[];
  milestones: Milestone[];
}
