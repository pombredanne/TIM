"""add tables for calendar events

Revision ID: 95e86dded40a
Revises: 98d090356548
Create Date: 2022-03-28 12:35:07.941335

"""

# revision identifiers, used by Alembic.
revision = "95e86dded40a"
down_revision = "98d090356548"

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "enrollmenttype",
        sa.Column("enroll_type_id", sa.Integer(), nullable=False),
        sa.Column("enroll_type", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("enroll_type_id"),
    )
    op.create_table(
        "event",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("max_size", sa.Integer(), nullable=True),
        sa.Column("event_tag", sa.Text(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("signup_before", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creator_user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["creator_user_id"],
            ["useraccount.id"],
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_table(
        "enrollment",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("usergroup_id", sa.Integer(), nullable=False),
        sa.Column("enroll_type_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["enroll_type_id"],
            ["enrollmenttype.enroll_type_id"],
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["event.event_id"],
        ),
        sa.ForeignKeyConstraint(
            ["usergroup_id"],
            ["usergroup.id"],
        ),
        sa.PrimaryKeyConstraint("event_id", "usergroup_id"),
    )
    op.create_table(
        "eventgroup",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("usergroup_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["event.event_id"],
        ),
        sa.ForeignKeyConstraint(
            ["usergroup_id"],
            ["usergroup.id"],
        ),
        sa.PrimaryKeyConstraint("event_id", "usergroup_id"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("eventgroup")
    op.drop_table("enrollment")
    op.drop_table("event")
    op.drop_table("enrollmenttype")
    # ### end Alembic commands ###
