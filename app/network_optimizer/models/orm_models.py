"""
Three tables:
  nodes         — server/endpoint vertices in the network
  edges         — directed connections with a latency weight
  route_queries — history of every shortest-path computation
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON, Boolean, DateTime, Float,
    ForeignKey, Integer, String, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class NodeModel(Base):
    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    outgoing_edges: Mapped[list["EdgeModel"]] = relationship(
        "EdgeModel", foreign_keys="EdgeModel.source_id",
        back_populates="source_node", cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[list["EdgeModel"]] = relationship(
        "EdgeModel", foreign_keys="EdgeModel.destination_id",
        back_populates="destination_node", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Node id={self.id} name={self.name!r}>"


class EdgeModel(Base):
    __tablename__ = "edges"
    __table_args__ = (
        UniqueConstraint("source_id", "destination_id", name="uq_edge_source_destination"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    destination_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    latency: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    source_node: Mapped["NodeModel"] = relationship(
        "NodeModel", foreign_keys=[source_id], back_populates="outgoing_edges"
    )
    destination_node: Mapped["NodeModel"] = relationship(
        "NodeModel", foreign_keys=[destination_id], back_populates="incoming_edges"
    )

    def __repr__(self) -> str:
        return f"<Edge id={self.id} {self.source_id}→{self.destination_id} latency={self.latency}>"


class RouteQueryModel(Base):
    __tablename__ = "route_queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    destination: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    path: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    total_latency: Mapped[float | None] = mapped_column(Float, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    algorithm_used: Mapped[str] = mapped_column(String(64), nullable=False, default="dijkstra")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<RouteQuery id={self.id} {self.source}→{self.destination} ok={self.success}>"
