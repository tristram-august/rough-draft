from alembic import op
import sqlalchemy as sa

revision = '594be24f1f16'
down_revision = '0003_career_summary'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "player_dim",
        sa.Column("gsis_id", sa.String(length=16), primary_key=True),
        sa.Column("pfr_id", sa.String(length=32), nullable=True, index=True),
        sa.Column("espn_id", sa.String(length=32), nullable=True, index=True),
        sa.Column("pff_id", sa.String(length=32), nullable=True, index=True),
        sa.Column("nfl_id", sa.String(length=32), nullable=True, index=True),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("first_name", sa.String(length=64), nullable=True),
        sa.Column("last_name", sa.String(length=64), nullable=True),
        sa.Column("short_name", sa.String(length=64), nullable=True),
        sa.Column("football_name", sa.String(length=64), nullable=True),
        sa.Column("suffix", sa.String(length=16), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=True),
        sa.Column("headshot", sa.Text(), nullable=True),
        sa.Column("position", sa.String(length=8), nullable=True),
        sa.Column("position_group", sa.String(length=16), nullable=True),
        sa.Column("ngs_position", sa.String(length=16), nullable=True),
        sa.Column("ngs_position_group", sa.String(length=16), nullable=True),
        sa.Column("latest_team", sa.String(length=8), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("ngs_status", sa.String(length=32), nullable=True),
        sa.Column("ngs_status_short_description", sa.String(length=64), nullable=True),
        sa.Column("years_of_experience", sa.Integer(), nullable=True),
        sa.Column("rookie_season", sa.Integer(), nullable=True),
        sa.Column("last_season", sa.Integer(), nullable=True),
        sa.Column("draft_year", sa.Integer(), nullable=True),
        sa.Column("draft_round", sa.Integer(), nullable=True),
        sa.Column("draft_pick", sa.Integer(), nullable=True),
        sa.Column("draft_team", sa.String(length=8), nullable=True),
        sa.Column("college_name", sa.String(length=128), nullable=True),
        sa.Column("college_conference", sa.String(length=64), nullable=True),
        sa.Column("jersey_number", sa.Integer(), nullable=True),
    )
    op.create_index("ix_player_dim_display_name", "player_dim", ["display_name"])
    op.create_index("ix_player_dim_position", "player_dim", ["position"])
    op.create_index("ix_player_dim_position_group", "player_dim", ["position_group"])
    op.create_index("ix_player_dim_latest_team", "player_dim", ["latest_team"])
    op.create_index("ix_player_dim_draft_year", "player_dim", ["draft_year"])
    op.create_index("ix_player_dim_draft_team", "player_dim", ["draft_team"])

    op.create_table(
        "player_game_stat",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_gsis_id", sa.String(length=16), sa.ForeignKey("player_dim.gsis_id"), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=True),
        sa.Column("season_type", sa.String(length=8), nullable=True),
        sa.Column("game_id", sa.String(length=32), nullable=False),
        sa.Column("team", sa.String(length=8), nullable=False),
        sa.Column("opponent_team", sa.String(length=8), nullable=True),
        sa.Column("position_group", sa.String(length=16), nullable=True),

        sa.Column("pass_completions", sa.Integer(), nullable=True),
        sa.Column("pass_attempts", sa.Integer(), nullable=True),
        sa.Column("pass_yards", sa.Integer(), nullable=True),
        sa.Column("pass_tds", sa.Integer(), nullable=True),
        sa.Column("pass_ints", sa.Integer(), nullable=True),
        sa.Column("passing_epa", sa.Float(), nullable=True),
        sa.Column("passing_cpoe", sa.Float(), nullable=True),

        sa.Column("rush_attempts", sa.Integer(), nullable=True),
        sa.Column("rush_yards", sa.Integer(), nullable=True),
        sa.Column("rush_tds", sa.Integer(), nullable=True),
        sa.Column("rushing_epa", sa.Float(), nullable=True),

        sa.Column("targets", sa.Integer(), nullable=True),
        sa.Column("receptions", sa.Integer(), nullable=True),
        sa.Column("rec_yards", sa.Integer(), nullable=True),
        sa.Column("rec_tds", sa.Integer(), nullable=True),
        sa.Column("receiving_epa", sa.Float(), nullable=True),
        sa.Column("target_share", sa.Float(), nullable=True),
        sa.Column("air_yards", sa.Integer(), nullable=True),
        sa.Column("air_yards_share", sa.Float(), nullable=True),

        sa.Column("fumbles_lost", sa.Integer(), nullable=True),

        sa.Column("def_tackles", sa.Integer(), nullable=True),
        sa.Column("def_sacks", sa.Float(), nullable=True),
        sa.Column("def_ints", sa.Integer(), nullable=True),
        sa.Column("def_forced_fumbles", sa.Integer(), nullable=True),
        sa.Column("def_fumble_recoveries", sa.Integer(), nullable=True),
        sa.Column("def_tds", sa.Integer(), nullable=True),

        sa.UniqueConstraint("player_gsis_id", "game_id", "team", name="uq_player_game_team"),
    )
    op.create_index("ix_pgs_player_season", "player_game_stat", ["player_gsis_id", "season"])
    op.create_index("ix_pgs_player_team_season", "player_game_stat", ["player_gsis_id", "team", "season"])
    op.create_index("ix_pgs_game_id", "player_game_stat", ["game_id"])
    op.create_index("ix_pgs_team", "player_game_stat", ["team"])


def downgrade() -> None:
    op.drop_index("ix_pgs_team", table_name="player_game_stat")
    op.drop_index("ix_pgs_game_id", table_name="player_game_stat")
    op.drop_index("ix_pgs_player_team_season", table_name="player_game_stat")
    op.drop_index("ix_pgs_player_season", table_name="player_game_stat")
    op.drop_table("player_game_stat")

    op.drop_index("ix_player_dim_draft_team", table_name="player_dim")
    op.drop_index("ix_player_dim_draft_year", table_name="player_dim")
    op.drop_index("ix_player_dim_latest_team", table_name="player_dim")
    op.drop_index("ix_player_dim_position_group", table_name="player_dim")
    op.drop_index("ix_player_dim_position", table_name="player_dim")
    op.drop_index("ix_player_dim_display_name", table_name="player_dim")
    op.drop_table("player_dim")