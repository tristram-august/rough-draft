"""
Monte Carlo NFL playoff odds from Elo win probabilities.

Results already played are fixed; every remaining regular-season game is
drawn from the Elo win probability (ratings frozen as of the snapshot, the
same simplification 538's "static" sims use). Each simulated season is then
seeded with the NFL's 7-team-per-conference format and the playoffs are
played out the same way, to get division / bye / conference / Super Bowl odds.

Tiebreakers are simplified, and the page says so: teams tied on win
percentage are ordered by head-to-head record among the tied teams, then
division record (only when all tied teams share a division), conference
record, strength of victory, then a coin flip. The real NFL procedure has
more steps (common games, strength of schedule, points-based ranks) and
restarts after each team is separated -- rare enough to matter only at the
margins of a close race.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.elo import win_probability

CONFERENCES = ("AFC", "NFC")

# Each simulated season draws every team's "true" rating as Elo + N(0, RATING_SD).
# Freezing ratings at their point estimate made the odds overconfident in
# backtests (85-95% favorites only made it ~79% of the time). The value comes from
# `python -m scripts.build_playoff_odds --backtest`, tuned on 2010-2019 and checked
# out of sample on 2020+.
RATING_SD = 125.0


@dataclass
class SeasonGame:
    week: int
    home: str
    away: str
    home_score: int | None
    away_score: int | None
    home_pre: float
    away_pre: float

    @property
    def final(self) -> bool:
        return self.home_score is not None and self.away_score is not None


@dataclass
class TeamOdds:
    team: str
    elo: float
    wins: float
    losses: float
    mean_wins: float
    make_playoffs: float
    win_division: float
    first_seed: float
    win_conference: float
    win_super_bowl: float
    seed_probs: list[float] = field(default_factory=list)


def implied_home_field_advantage(games: list[SeasonGame], probs: list[float]) -> float:
    """Recover the HFA the Elo build used from its stored predictions, so it
    never has to be duplicated as a constant here."""
    vals = [
        400 * np.log10(p / (1 - p)) - (g.home_pre - g.away_pre)
        for g, p in zip(games, probs)
        if 0 < p < 1
    ]
    return float(np.median(vals)) if vals else 0.0


def simulate_season(
    games: list[SeasonGame],
    teams: dict[str, tuple[str, str]],  # team -> (conference, division)
    ratings: dict[str, float],
    hfa: float,
    as_of_week: int,
    sims: int = 10_000,
    seed: int | None = None,
    rating_sd: float | None = None,
    wildcards: int = 3,  # 2 before the 2020 expansion; the playoffs are only played out for 3
) -> list[TeamOdds]:
    rng = np.random.default_rng(seed)
    sd = RATING_SD if rating_sd is None else rating_sd
    names = sorted(teams)
    idx = {t: i for i, t in enumerate(names)}
    T = len(names)
    conf_of = np.array([CONFERENCES.index(teams[t][0]) for t in names])
    div_key = [f"{teams[t][0]} {teams[t][1]}" for t in names]

    fixed = [g for g in games if g.final and g.week <= as_of_week]
    open_ = [g for g in games if not (g.final and g.week <= as_of_week)]

    # ── results already in the books ──
    base_w = np.zeros(T)
    base_g = np.zeros(T)
    base_cw, base_cg = np.zeros(T), np.zeros(T)
    base_dw, base_dg = np.zeros(T), np.zeros(T)
    base_beat = np.zeros((T, T))  # base_beat[t, u] = wins by t over u (ties 0.5)
    for g in fixed:
        h, a = idx[g.home], idx[g.away]
        hw = 1.0 if g.home_score > g.away_score else 0.5 if g.home_score == g.away_score else 0.0
        same_conf = conf_of[h] == conf_of[a]
        same_div = div_key[h] == div_key[a]
        for t, w in ((h, hw), (a, 1 - hw)):
            base_w[t] += w
            base_g[t] += 1
            if same_conf:
                base_cw[t] += w
                base_cg[t] += 1
            if same_div:
                base_dw[t] += w
                base_dg[t] += 1
        base_beat[h, a] += hw
        base_beat[a, h] += 1 - hw
    record_w = base_w.copy()
    record_l = base_g - base_w

    # ── simulate the rest ──
    G = len(open_)
    H = np.array([idx[g.home] for g in open_], dtype=int)
    A = np.array([idx[g.away] for g in open_], dtype=int)
    rating_arr = np.array([ratings[t] for t in names])
    sim_ratings = rating_arr + (rng.normal(0.0, sd, (sims, T)) if sd > 0 else np.zeros((sims, T)))
    diff = sim_ratings[:, H] + hfa - sim_ratings[:, A]
    p_home = 1.0 / (1.0 + 10 ** (-diff / 400.0))
    home_won = rng.random((sims, G)) < p_home

    def tally(mask: np.ndarray, base_wins: np.ndarray, base_games: np.ndarray):
        mh = np.zeros((G, T))
        ma = np.zeros((G, T))
        mh[np.arange(G)[mask], H[mask]] = 1
        ma[np.arange(G)[mask], A[mask]] = 1
        w = base_wins + home_won @ mh + (~home_won) @ ma
        n = base_games + mh.sum(0) + ma.sum(0)
        return w, n

    all_mask = np.ones(G, dtype=bool)
    conf_mask = conf_of[H] == conf_of[A] if G else all_mask
    div_mask = np.array([div_key[h] == div_key[a] for h, a in zip(H, A)], dtype=bool) if G else all_mask
    wins, n_games = tally(all_mask, base_w, base_g)
    cw, cn = tally(conf_mask, base_cw, base_cg)
    dw, dn = tally(div_mask, base_dw, base_dg)
    pct = wins / np.maximum(n_games, 1)
    conf_pct = cw / np.maximum(cn, 1)
    div_pct = dw / np.maximum(dn, 1)

    winner = np.where(home_won, H, A)
    loser = np.where(home_won, A, H)
    flat = (np.arange(sims)[:, None] * T * T + winner * T + loser).ravel()
    beat = np.bincount(flat, minlength=sims * T * T).reshape(sims, T, T) + base_beat
    beaten_games = beat.sum(2)
    sov = np.einsum("stu,su->st", beat, pct) / np.maximum(beaten_games, 1)
    tiebreak_noise = rng.random((sims, T))

    conf_members = [[i for i in range(T) if conf_of[i] == c] for c in range(2)]
    divisions: dict[str, list[int]] = {}
    for i, k in enumerate(div_key):
        divisions.setdefault(k, []).append(i)

    make = np.zeros(T)
    div_win = np.zeros(T)
    seed_counts = np.zeros((T, 7))
    conf_win = np.zeros(T)
    sb_win = np.zeros(T)

    for s in range(sims):
        r_s = sim_ratings[s].tolist()

        def p_win(home: int, away: int, neutral: bool = False) -> float:
            return win_probability(r_s[home], r_s[away], 0.0 if neutral else hfa)

        pct_s, conf_s, div_s, sov_s = pct[s].tolist(), conf_pct[s].tolist(), div_pct[s].tolist(), sov[s].tolist()
        beat_s, noise_s = beat[s].tolist(), tiebreak_noise[s].tolist()

        def order(cands: list[int]) -> list[int]:
            cands = sorted(cands, key=lambda t: -pct_s[t])
            out: list[int] = []
            i = 0
            while i < len(cands):
                j = i + 1
                while j < len(cands) and abs(pct_s[cands[j]] - pct_s[cands[i]]) < 1e-9:
                    j += 1
                group = cands[i:j]
                if len(group) > 1:
                    same_div = len({div_key[t] for t in group}) == 1

                    def key(t: int, group: list[int] = group, same_div: bool = same_div):
                        won = sum(beat_s[t][u] for u in group if u != t)
                        played = won + sum(beat_s[u][t] for u in group if u != t)
                        h2h = won / played if played else 0.5
                        return (h2h, div_s[t] if same_div else 0.0, conf_s[t], sov_s[t], noise_s[t])

                    group = sorted(group, key=key, reverse=True)
                out.extend(group)
                i = j
            return out

        for c in range(2):
            leaders = [order(members)[0] for k, members in divisions.items() if conf_of[members[0]] == c]
            seeds = order(leaders)
            rest = [t for t in conf_members[c] if t not in leaders]
            seeds = seeds + order(rest)[:wildcards]
            for pos, t in enumerate(seeds):
                make[t] += 1
                seed_counts[t, pos] += 1
            for t in leaders:
                div_win[t] += 1
            if wildcards != 3:
                continue

            # playoffs: higher seed hosts; 1 seed has the bye
            seed_of = {t: i for i, t in enumerate(seeds)}
            alive = [seeds[0]]
            for hi, lo in ((1, 6), (2, 5), (3, 4)):
                h, a = seeds[hi], seeds[lo]
                alive.append(h if rng.random() < p_win(h, a) else a)
            alive.sort(key=lambda t: seed_of[t])
            div_round = [(alive[0], alive[3]), (alive[1], alive[2])]
            finalists = [h if rng.random() < p_win(h, a) else a for h, a in div_round]
            finalists.sort(key=lambda t: seed_of[t])
            h, a = finalists
            champ = h if rng.random() < p_win(h, a) else a
            conf_win[champ] += 1
            if c == 0:
                afc_champ = champ
            else:
                nfc_champ = champ
        if wildcards == 3:
            sb_win[afc_champ if rng.random() < p_win(afc_champ, nfc_champ, neutral=True) else nfc_champ] += 1

    mean_wins = wins.mean(0)
    return [
        TeamOdds(
            team=t,
            elo=float(rating_arr[i]),
            wins=float(record_w[i]),
            losses=float(record_l[i]),
            mean_wins=float(mean_wins[i]),
            make_playoffs=float(make[i] / sims),
            win_division=float(div_win[i] / sims),
            first_seed=float(seed_counts[i, 0] / sims),
            win_conference=float(conf_win[i] / sims),
            win_super_bowl=float(sb_win[i] / sims),
            seed_probs=[float(x) for x in seed_counts[i] / sims],
        )
        for i, t in enumerate(names)
    ]
