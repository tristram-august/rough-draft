from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0021_team_game_stat_detail"
down_revision = "0020_team_game_stat"
branch_labels = None
depends_on = None

NEW_COLUMNS = [
    "sacks_suffered", "sack_yards_lost", "passing_air_yards", "passing_yards_after_catch",
    "passing_first_downs", "rushing_first_downs", "passing_20", "passing_40", "rushing_20", "rushing_40",
    "fumbles_lost_total", "fumble_recovery_opp", "def_pass_defended", "def_safeties", "special_teams_tds",
    "fg_long",
    "fg_made_0_19", "fg_made_20_29", "fg_made_30_39", "fg_made_40_49", "fg_made_50_59", "fg_made_60_",
    "fg_missed_0_19", "fg_missed_20_29", "fg_missed_30_39", "fg_missed_40_49", "fg_missed_50_59", "fg_missed_60_",
    "pt_att", "pt_yards", "pt_net_yards", "pt_inside_20", "pt_touchback",
    "punt_returns", "punt_return_yards", "kickoff_returns", "kickoff_return_yards",
]


def upgrade() -> None:
    for name in NEW_COLUMNS:
        op.add_column("team_game_stat", sa.Column(name, sa.Integer(), nullable=True))


def downgrade() -> None:
    for name in reversed(NEW_COLUMNS):
        op.drop_column("team_game_stat", name)
