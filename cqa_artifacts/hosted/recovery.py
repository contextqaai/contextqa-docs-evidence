"""Snapshot the documentation database and restore into an empty migrated database."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile
import psycopg
from psycopg import sql

# Foreign-key order. Expiring connection material is intentionally invalidated on restore.
TABLES = (
    "docs_organizations",
    "docs_memberships",
    "docs_projects",
    "docs_setup",
    "docs_source_deliveries",
    "docs_discoveries",
    "docs_guide_prs",
    "docs_imports",
    "docs_import_files",
    "docs_import_versions",
    "docs_workflows",
    "docs_workflow_versions",
    "docs_runs",
    "docs_run_stages",
    "docs_capture_profiles",
    "docs_capture_jobs",
    "docs_guide_versions",
    "docs_guide_heads",
    "docs_guide_media",
    "docs_enablement",
    "docs_refresh_requests",
    "docs_library_saves",
    "docs_media_edits",
    "docs_publication_checks",
    "docs_reader_redirects",
    "docs_guide_retirements",
)


def snapshot(db, path):
    path = Path(path)
    # Copy from one repeatable snapshot into a private file, then link it exclusively.
    with tempfile.NamedTemporaryFile(dir=path.parent) as tmp:
        rows = {}
        with (
            db.transaction(),
            zipfile.ZipFile(
                tmp.name, "w", zipfile.ZIP_DEFLATED, allowZip64=True
            ) as archive,
        ):
            db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            for table in TABLES:
                digest = hashlib.sha256()
                with (
                    archive.open(table, "w", force_zip64=True) as output,
                    db.cursor().copy(
                        sql.SQL("COPY {} TO STDOUT WITH (FORMAT BINARY)").format(
                            sql.Identifier(table)
                        )
                    ) as cp,
                ):
                    for chunk in cp:
                        digest.update(chunk)
                        output.write(chunk)
                rows[table] = digest.hexdigest()
            archive.writestr("manifest.json", json.dumps(dict(schema=6, tables=rows)))
        os.link(tmp.name, path)


def restore(db, path):
    with zipfile.ZipFile(path) as archive, db.transaction():
        meta = json.loads(archive.read("manifest.json"))
        if meta.get("schema") != 6 or set(meta["tables"]) != set(TABLES):
            raise ValueError("Unexpected backup format.")
        for table in TABLES:
            if db.execute(
                sql.SQL("SELECT EXISTS(SELECT 1 FROM {})").format(sql.Identifier(table))
            ).fetchone()[0]:
                raise ValueError("Restore requires an empty migrated database.")
        for table in TABLES:
            digest = hashlib.sha256()
            with (
                archive.open(table) as source,
                db.cursor().copy(
                    sql.SQL("COPY {} FROM STDIN WITH (FORMAT BINARY)").format(
                        sql.Identifier(table)
                    )
                ) as cp,
            ):
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
                    cp.write(chunk)
            if digest.hexdigest() != meta["tables"][table]:
                raise ValueError("Archive checksum mismatch.")
        # Restored provider starts may already exist remotely; require reconciliation.
        db.execute(
            "UPDATE docs_capture_jobs SET status='reconcile',reason='Reconcile the original provider run after restore' WHERE status IN('starting','queued','running','collecting')"
        )
        db.execute("UPDATE docs_workflows SET active=false")
        db.execute(
            "UPDATE docs_refresh_requests SET status='investigate',reason='Reconcile deployment and capture following restore' WHERE status IN('capturing','waiting')"
        )


def prune(db, days, commit):
    if days < 30:
        raise ValueError("Minimum retention for unused derivatives is 30 days.")
    # Version originals and published media are in different tables and never selected.
    query = " FROM docs_media_edits WHERE created_at < now() - (%s * interval '1 day')"
    count = db.execute("SELECT count(*)" + query, (days,)).fetchone()[0]
    if commit:
        db.execute("DELETE" + query, (days,))
    return count


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("snapshot", "restore"):
        sub.add_parser(name).add_argument("file", type=Path)
    p = sub.add_parser("prune")
    p.add_argument("--days", type=int, default=90)
    p.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with psycopg.connect(os.environ["DATABASE_URL"]) as db:
        if args.action == "snapshot":
            snapshot(db, args.file)
        elif args.action == "restore":
            restore(db, args.file)
        else:
            print(prune(db, args.days, args.apply))


if __name__ == "__main__":
    main()
