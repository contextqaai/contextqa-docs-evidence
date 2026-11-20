"""Tenant-scoped PostgreSQL implementation of the reviewed domain workflow."""
import copy
from contextlib import contextmanager
from psycopg.types.json import Jsonb
from psycopg.errors import UniqueViolation
from ..loop import Store, validate_manifest, text
from ..core import Rejected

class PostgresStore(Store):
    def __init__(self, pool, organization):
        self.pool, self.organization = pool, organization

    @contextmanager
    def transaction(self, project):
        with self.pool.connection() as db, db.transaction():
            db.execute("SET LOCAL statement_timeout = '10s'")
            row = db.execute('SELECT state FROM docs_projects WHERE organization_id=%s AND id=%s FOR UPDATE',
                             (self.organization, project)).fetchone()
            if not row:
                raise Rejected('Project unavailable')
            state = row[0]
            # Authorization data comes from the membership table, never from submitted JSON.
            state['members'] = dict(db.execute('SELECT subject, role FROM docs_memberships WHERE organization_id=%s',
                                              (self.organization,)).fetchall())
            yield state
            db.execute('UPDATE docs_projects SET state=%s, updated_at=now() WHERE organization_id=%s AND id=%s',
                       (Jsonb(state), self.organization, project))

    def create(self, manifest, owner):
        manifest = validate_manifest(manifest)
        text(owner, 'owner', 200)
        with self.pool.connection() as db, db.transaction():
            membership = db.execute('SELECT role FROM docs_memberships WHERE organization_id=%s AND subject=%s',
                                    (self.organization, owner)).fetchone()
            if not membership or membership[0] != 'admin':
                raise Rejected('Organization admin required')
            state = dict(manifest=copy.deepcopy(manifest), members={}, articles={}, events={}, items={}, audit=[])
            try:
                db.execute('INSERT INTO docs_projects (organization_id,id,state) VALUES (%s,%s,%s)',
                           (self.organization, manifest['project_id'], Jsonb(state)))
            except UniqueViolation:
                raise Rejected('Project already exists') from None
        return manifest['project_id']

    def member(self, *args, **kwargs):
        raise Rejected('Manage organization membership through the operator provisioning command')
