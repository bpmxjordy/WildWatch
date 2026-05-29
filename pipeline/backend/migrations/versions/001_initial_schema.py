"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(20), server_default="stopped"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("framework", sa.String(50), nullable=False),
        sa.Column("class_names", postgresql.JSONB(), server_default="[]"),
        sa.Column("input_size", sa.Integer(), server_default="640"),
        sa.Column("gpu_memory_mb", sa.Integer()),
        sa.Column("precision", sa.String(10), server_default="fp16"),
        sa.Column("file_size_bytes", sa.BigInteger()),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "streams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(30), nullable=False),
        sa.Column("location_name", sa.String(200)),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("timezone", sa.String(50)),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("models.id")),
        sa.Column("active_classes", postgresql.JSONB(), server_default="[]"),
        sa.Column("min_confidence", sa.Float(), server_default="0.5"),
        sa.Column("frame_interval_seconds", sa.Integer(), server_default="60"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("status", sa.String(20), server_default="idle"),
        sa.Column("last_frame_at", sa.DateTime(timezone=True)),
        sa.Column("consecutive_failures", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "detections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("stream_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("streams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("species_label", sa.String(200)),
        sa.Column("common_name", sa.String(200)),
        sa.Column("confidence", sa.Float()),
        sa.Column("bbox_x1", sa.Float()),
        sa.Column("bbox_y1", sa.Float()),
        sa.Column("bbox_x2", sa.Float()),
        sa.Column("bbox_y2", sa.Float()),
        sa.Column("thumbnail_path", sa.String(500)),
        sa.Column("frame_path", sa.String(500)),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_detections_stream_detected", "detections", ["stream_id", "detected_at"])

    op.create_table(
        "notification_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stream_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("streams.id")),
        sa.Column("species_filter", postgresql.JSONB(), server_default="[]"),
        sa.Column("min_confidence", sa.Float(), server_default="0.5"),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("destination", sa.Text(), nullable=False),
        sa.Column("cooldown_seconds", sa.Integer(), server_default="300"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "gpu_inventory",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("device_index", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("total_memory_mb", sa.Integer(), nullable=False),
        sa.Column("compute_capability", sa.String(20)),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("gpu_inventory")
    op.drop_table("notification_rules")
    op.drop_index("ix_detections_stream_detected", table_name="detections")
    op.drop_table("detections")
    op.drop_table("streams")
    op.drop_table("models")
    op.drop_table("projects")
