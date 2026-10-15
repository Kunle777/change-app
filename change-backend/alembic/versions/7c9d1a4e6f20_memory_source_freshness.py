"""track memory source edits and invalidate stale chunks

Revision ID: 7c9d1a4e6f20
Revises: 5a1c7e9b3d20
"""
from alembic import op
import sqlalchemy as sa


revision = "7c9d1a4e6f20"
down_revision = "5a1c7e9b3d20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "brain_dumps",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "checkins",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE public.brain_dumps SET updated_at = created_at WHERE updated_at IS NULL"
    )
    op.execute(
        "UPDATE public.checkins SET updated_at = created_at WHERE updated_at IS NULL"
    )
    op.alter_column(
        "brain_dumps",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )
    op.alter_column(
        "checkins",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )

    op.execute(
        """
        CREATE FUNCTION public.touch_memory_source_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        SET search_path = pg_catalog, public
        AS $function$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $function$
        """
    )
    op.execute(
        """
        CREATE TRIGGER brain_dumps_touch_updated_at
        BEFORE UPDATE ON public.brain_dumps
        FOR EACH ROW
        EXECUTE FUNCTION public.touch_memory_source_updated_at()
        """
    )
    op.execute(
        """
        CREATE TRIGGER checkins_touch_updated_at
        BEFORE UPDATE ON public.checkins
        FOR EACH ROW
        EXECUTE FUNCTION public.touch_memory_source_updated_at()
        """
    )

    op.execute(
        """
        CREATE FUNCTION public.invalidate_memory_source_chunks()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            source_kind text;
        BEGIN
            IF TG_TABLE_NAME = 'brain_dumps' THEN
                source_kind = 'brain_dump';
            ELSE
                source_kind = 'check_in';
            END IF;

            IF TG_OP = 'DELETE' THEN
                DELETE FROM public.memory_chunks
                WHERE source_type = source_kind
                  AND source_id = OLD.id
                  AND user_id = OLD.user_id;
                RETURN OLD;
            END IF;

            DELETE FROM public.memory_chunks
            WHERE source_type = source_kind
              AND source_id = NEW.id
              AND user_id = NEW.user_id;
            RETURN NEW;
        END;
        $function$
        """
    )
    op.execute(
        """
        CREATE TRIGGER brain_dumps_invalidate_memory_after_delete
        AFTER DELETE ON public.brain_dumps
        FOR EACH ROW
        EXECUTE FUNCTION public.invalidate_memory_source_chunks()
        """
    )
    op.execute(
        """
        CREATE TRIGGER brain_dumps_invalidate_memory_after_content_update
        AFTER UPDATE OF content ON public.brain_dumps
        FOR EACH ROW
        EXECUTE FUNCTION public.invalidate_memory_source_chunks()
        """
    )
    op.execute(
        """
        CREATE TRIGGER checkins_invalidate_memory_after_delete
        AFTER DELETE ON public.checkins
        FOR EACH ROW
        EXECUTE FUNCTION public.invalidate_memory_source_chunks()
        """
    )
    op.execute(
        """
        CREATE TRIGGER checkins_invalidate_memory_after_content_update
        AFTER UPDATE OF type, mood, goal_today, goal_status, reflection
        ON public.checkins
        FOR EACH ROW
        EXECUTE FUNCTION public.invalidate_memory_source_chunks()
        """
    )
    op.execute(
        """
        REVOKE ALL ON FUNCTION public.invalidate_memory_source_chunks() FROM PUBLIC
        """
    )

    op.execute(
        """
        CREATE FUNCTION public.purge_memory_chunks_when_ai_disabled()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        BEGIN
            IF NEW.ai_enabled IS FALSE THEN
                DELETE FROM public.memory_chunks WHERE user_id = NEW.user_id;
            END IF;
            RETURN NEW;
        END;
        $function$
        """
    )
    op.execute(
        """
        CREATE TRIGGER feature_entitlements_purge_memory_on_insert
        AFTER INSERT ON public.feature_entitlements
        FOR EACH ROW
        EXECUTE FUNCTION public.purge_memory_chunks_when_ai_disabled()
        """
    )
    op.execute(
        """
        CREATE TRIGGER feature_entitlements_purge_memory_on_ai_disable
        AFTER UPDATE OF ai_enabled ON public.feature_entitlements
        FOR EACH ROW
        WHEN (NEW.ai_enabled IS FALSE)
        EXECUTE FUNCTION public.purge_memory_chunks_when_ai_disabled()
        """
    )
    op.execute(
        """
        REVOKE ALL ON FUNCTION public.purge_memory_chunks_when_ai_disabled() FROM PUBLIC
        """
    )

    op.execute(
        """
        DELETE FROM public.memory_chunks mc
        WHERE NOT EXISTS (
            SELECT 1
            FROM public.feature_entitlements fe
            WHERE fe.user_id = mc.user_id
              AND fe.ai_enabled IS TRUE
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS feature_entitlements_purge_memory_on_ai_disable
        ON public.feature_entitlements
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS feature_entitlements_purge_memory_on_insert
        ON public.feature_entitlements
        """
    )
    op.execute(
        "DROP FUNCTION IF EXISTS public.purge_memory_chunks_when_ai_disabled()"
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS checkins_invalidate_memory_after_content_update
        ON public.checkins
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS checkins_invalidate_memory_after_delete
        ON public.checkins
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS brain_dumps_invalidate_memory_after_content_update
        ON public.brain_dumps
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS brain_dumps_invalidate_memory_after_delete
        ON public.brain_dumps
        """
    )
    op.execute("DROP FUNCTION IF EXISTS public.invalidate_memory_source_chunks()")
    op.execute(
        "DROP TRIGGER IF EXISTS checkins_touch_updated_at ON public.checkins"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS brain_dumps_touch_updated_at ON public.brain_dumps"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS public.touch_memory_source_updated_at()"
    )
    op.drop_column("checkins", "updated_at")
    op.drop_column("brain_dumps", "updated_at")
