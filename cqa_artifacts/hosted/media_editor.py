"""Pixel-only derivatives of immutable, traceable ContextQA guide images."""

import io
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb
from PIL import Image, ImageDraw
from .. import core
from ..loop import fingerprint
from .library import edition, scope
from .onboarding import PREFIX


class Box(BaseModel):
    x: int = Field(ge=0, le=16000)
    y: int = Field(ge=0, le=16000)
    width: int = Field(ge=1, le=16000)
    height: int = Field(ge=1, le=16000)


class Edit(BaseModel):
    path: str
    version: str
    image: str = Field(pattern="^[a-f0-9]{64}$")
    operation: Literal["redact", "crop", "outline"]
    box: Box


def transform(raw, op, box):
    with Image.open(io.BytesIO(raw)) as source:
        if source.width * source.height > 20_000_000:
            raise core.Rejected("Choose a smaller source image.")
        x, y, w, h = box.x, box.y, box.width, box.height
        if x + w > source.width or y + h > source.height:
            raise core.Rejected("The rectangle extends beyond the image.")
        pixels = source.convert("RGB")
        if op == "crop":
            pixels = pixels.crop((x, y, x + w, y + h))
        else:
            draw = ImageDraw.Draw(pixels)
            draw.rectangle(
                (x, y, x + w - 1, y + h - 1),
                fill="black" if op == "redact" else None,
                outline=None if op == "redact" else "#7040ff",
                width=3,
            )
        # Export only flattened pixels, with no copied metadata or original layers.
        result = Image.new("RGB", pixels.size)
        result.paste(pixels)
        output = io.BytesIO()
        result.save(output, format="PNG")
        return output.getvalue()


def router(pool, auth):
    r = APIRouter()

    @r.post(PREFIX + "/media/edits")
    def edit(org: str, project: str, body: Edit, actor=Depends(auth)):
        with pool.connection() as db:
            scope(db, org, project, actor, True)
            v = edition(db, org, project, body.path, body.version)
            if not any(
                m["digest"] == body.image and m["kind"] == "screenshot"
                for m in v["media"]
            ):
                raise HTTPException(404, "Select a screenshot from this guide version.")
            source = db.execute(
                "SELECT content FROM docs_guide_media WHERE organization_id=%s AND project_id=%s AND digest=%s",
                (org, project, body.image),
            ).fetchone()
            if not source or core.digest(bytes(source[0])) != body.image:
                raise core.Rejected("Original media failed verification.")
            recipe = body.model_dump()
            ident = fingerprint(recipe)
            old = db.execute(
                "SELECT id FROM docs_media_edits WHERE organization_id=%s AND project_id=%s AND id=%s",
                (org, project, ident),
            ).fetchone()
            if not old:
                raw = transform(bytes(source[0]), body.operation, body.box)
                db.execute(
                    """INSERT INTO docs_media_edits(organization_id,project_id,path,version,id,source_digest,recipe,content,actor)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                    (
                        org,
                        project,
                        body.path,
                        body.version,
                        ident,
                        body.image,
                        Jsonb(recipe),
                        raw,
                        actor,
                    ),
                )
            return dict(id=ident, parent=body.image, recipe=recipe)

    @r.get(PREFIX + "/media/edits/{ident}")
    def get(org: str, project: str, ident: str, actor=Depends(auth)):
        with pool.connection() as db:
            scope(db, org, project, actor)
            row = db.execute(
                "SELECT content FROM docs_media_edits WHERE organization_id=%s AND project_id=%s AND id=%s",
                (org, project, ident),
            ).fetchone()
            if not row:
                raise HTTPException(404, "Edited image unavailable.")
            return Response(bytes(row[0]), media_type="image/png")

    return r
