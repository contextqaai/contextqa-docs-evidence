"""Workspace writing defaults. Every published profile revision remains addressable."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from psycopg.rows import dict_row
from pydantic import BaseModel, Field, StringConstraints

from .onboarding import PREFIX, admin, setup

Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120, pattern=r"^[^\r\n]+$")]


class ProfileEdit(BaseModel):
    revision: int = Field(ge=0)
    brand: Label
    audience: Label
    voice: Literal["Technical", "Business outcome"]


def profile(db, org, project, revision=None):
    with db.cursor(row_factory=dict_row) as cur:
        statement = """SELECT revision, brand, audience, voice, actor FROM docs_writing_profiles
                       WHERE organization_id=%s AND project_id=%s"""
        params = [org, project]
        if revision is not None:
            statement += " AND revision=%s"
            params.append(revision)
        return cur.execute(statement + " ORDER BY revision DESC LIMIT 1", params).fetchone()


def router(pool, auth):
    routes = APIRouter()

    @routes.get(PREFIX + "/writing-profile")
    def read(org: str, project: str, actor=Depends(auth)):
        with pool.connection() as db:
            allowed = db.execute(
                """SELECT 1 FROM docs_projects p JOIN docs_memberships m USING (organization_id)
                   WHERE p.organization_id=%s AND p.id=%s AND m.subject=%s AND m.role IN ('admin','editor')""",
                (org, project, actor)).fetchone()
            if not allowed:
                raise HTTPException(404, "Writing profile unavailable.")
            return profile(db, org, project) or {"revision": 0}

    @routes.post(PREFIX + "/writing-profile")
    def save(org: str, project: str, body: ProfileEdit, actor=Depends(auth)):
        with pool.connection() as db:
            admin(db, org, actor)
            setup(db, org, project)
            current = profile(db, org, project) or {"revision": 0}
            if current["revision"] != body.revision:
                raise HTTPException(409, "Writing profile changed. Reload before saving.")
            if all(current.get(k) == getattr(body, k) for k in ("brand", "audience", "voice")):
                return current
            db.execute("""INSERT INTO docs_writing_profiles
                          (organization_id,project_id,revision,brand,audience,voice,actor)
                          VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                       (org, project, body.revision + 1, body.brand, body.audience, body.voice, actor))
            return profile(db, org, project)

    return routes
