"""Initial schema — nodes, edges, route_queries tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-03-25
"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nodes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_nodes_name", "nodes", ["name"], unique=True)

    op.create_table(
        "edges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("destination_id", sa.Integer(), nullable=False),
        sa.Column("latency", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["source_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["destination_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "destination_id", name="uq_edge_source_destination"),
    )
    op.create_index("ix_edges_source_id", "edges", ["source_id"])
    op.create_index("ix_edges_destination_id", "edges", ["destination_id"])

    op.create_table(
        "route_queries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("destination", sa.String(length=255), nullable=False),
        sa.Column("path", sa.JSON(), nullable=False),
        sa.Column("total_latency", sa.Float(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("algorithm_used", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_route_queries_source", "route_queries", ["source"])
    op.create_index("ix_route_queries_destination", "route_queries", ["destination"])
    op.create_index("ix_route_queries_created_at", "route_queries", ["created_at"])


def downgrade() -> None:
    op.drop_table("route_queries")
    op.drop_table("edges")
    op.drop_table("nodes")
