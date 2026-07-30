import Link from "next/link";
import { PostCard } from "./ui/post-card";
import { ModLink } from "./ui/mod-link";
import { NewsWidget } from "./ui/widget-news";
import { FantasyLeadersWidget } from "./ui/widget-fantasy-leaders";
import { fetchPosts, type PostSummary } from "./lib/posts";
import { fetchNews, type NewsFeed } from "./lib/dashboard";
import { fetchFantasySeasons, fetchLeaderboard, type FantasyLeaderRow } from "./lib/fantasy";

// Every panel is live data; nothing here can be built ahead of time.
export const dynamic = "force-dynamic";

async function loadFantasyLeaders(): Promise<{ rows: FantasyLeaderRow[]; season: number | null }> {
  const seasons = await fetchFantasySeasons();
  const season = seasons[0];
  if (season == null) return { rows: [], season: null };
  const board = await fetchLeaderboard({
    season,
    position: "ALL",
    scoring: "ppr",
    sort: "total",
    limit: 8,
  });
  return { rows: board.rows, season };
}

export default async function Page() {
  // Each panel fails independently — a dead upstream shouldn't blank the page.
  const [postsResult, newsResult, fantasyResult] = await Promise.allSettled([
    fetchPosts({ limit: 6 }),
    fetchNews(6),
    loadFantasyLeaders(),
  ]);

  const posts: PostSummary[] = postsResult.status === "fulfilled" ? postsResult.value.posts : [];
  const news: NewsFeed | null = newsResult.status === "fulfilled" ? newsResult.value : null;
  const fantasy = fantasyResult.status === "fulfilled" ? fantasyResult.value : { rows: [], season: null };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      {/* Slim hero */}
      <div className="mb-8 border-b border-slate-800/60 pb-6">
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
          Rough Draft <span className="font-light text-slate-500">Football</span>
        </h1>
        <p className="mt-1.5 text-sm text-slate-400">
          Draft picks re-graded with hindsight, fantasy production from real games, and
          whatever the league is arguing about today.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Takes */}
        <div className="lg:col-span-2">
          <div className="mb-4 flex items-baseline justify-between gap-3">
            <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-400">
              Latest takes
            </h2>
            <div className="flex items-center gap-3">
              <ModLink href="/admin/posts/new" label="Write" />
              <Link
                href="/blog"
                className="text-sm font-medium text-sky-400 transition-colors hover:text-sky-300"
              >
                All posts <span aria-hidden>→</span>
              </Link>
            </div>
          </div>

          {posts.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-slate-800 px-5 py-10 text-center">
              <p className="text-sm text-slate-500">Nothing written yet.</p>
              <p className="mt-1 text-xs text-slate-600">
                Sign in as a mod to publish the first one.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {posts.map((post) => (
                <PostCard key={post.id} post={post} />
              ))}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {news && <NewsWidget feed={news} />}
          {fantasy.season != null && (
            <FantasyLeadersWidget rows={fantasy.rows} season={fantasy.season} />
          )}
        </div>
      </div>
    </div>
  );
}
