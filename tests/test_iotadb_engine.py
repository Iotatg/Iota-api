"""IotaDB query engine: CRUD, operators, injection guard, vectors."""
from __future__ import annotations

import pytest

from app.iotadb.engine import IotaDBEngine
from app.iotadb.query import apply_query, cosine_similarity, run_aggregation, sanitize_query


def test_sanitize_strips_dangerous_operators():
    dirty = {"name": "a", "$where": "1==1", "nested": {"$eval": "x", "ok": 1}}
    clean = sanitize_query(dirty)
    assert "$where" not in clean
    assert "$eval" not in clean["nested"]
    assert clean["nested"]["ok"] == 1
    assert clean["name"] == "a"


def test_query_eq_and_comparison_ops():
    docs = [
        {"id": "1", "score": 10, "role": "admin"},
        {"id": "2", "score": 90, "role": "member"},
        {"id": "3", "score": 50, "role": "member"},
    ]
    assert [d["id"] for d in apply_query(docs, {"role": "admin"})] == ["1"]
    assert [d["id"] for d in apply_query(docs, {"score": {"$gte": 50}})] == ["2", "3"]
    assert [d["id"] for d in apply_query(docs, {"score": {"$lt": 20}})] == ["1"]
    assert [d["id"] for d in apply_query(docs, {"role": {"$in": ["admin"]}})] == ["1"]
    assert [d["id"] for d in apply_query(docs, {"role": {"$ne": "admin"}})] == ["2", "3"]


def test_query_exists():
    docs = [{"id": "1", "email": "a@x"}, {"id": "2"}]
    assert [d["id"] for d in apply_query(docs, {"email": {"$exists": True}})] == ["1"]
    assert [d["id"] for d in apply_query(docs, {"email": {"$exists": False}})] == ["2"]


def test_aggregation_match_sort_limit_project_count():
    docs = [
        {"id": "1", "score": 10, "name": "a"},
        {"id": "2", "score": 90, "name": "b"},
        {"id": "3", "score": 50, "name": "c"},
    ]
    out = run_aggregation(
        docs,
        [
            {"$match": {"score": {"$gte": 50}}},
            {"$sort": {"score": -1}},
            {"$project": {"name": 1, "score": 1}},
            {"$limit": 1},
        ],
    )
    assert len(out) == 1
    assert out[0]["name"] == "b"
    assert "id" not in out[0]
    counted = run_aggregation(docs, [{"$match": {"score": {"$gt": 10}}}, {"$count": "n"}])
    assert counted == [{"n": 2}]


def test_aggregation_rejects_lookup():
    with pytest.raises(ValueError):
        run_aggregation([], [{"$lookup": {"from": "x"}}])


def test_cosine_similarity():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine_similarity([], [1.0]) == 0.0


@pytest.mark.asyncio
async def test_engine_tenant_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_DB", "iota_test")
    monkeypatch.setenv("POSTGRES_USER", "iota")
    monkeypatch.setenv("POSTGRES_PASSWORD", "iota")
    monkeypatch.setenv("ADMIN_TOKEN", "test_admin_token_" + "x" * 32)

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app import database
    from app.models import iotadb as _iotadb  # noqa: F401

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    async with engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    async with factory() as s1:
        db = IotaDBEngine(s1)
        a = await db.insert("u1", "posts", {"title": "one", "likes": 3})
        await db.insert("u2", "posts", {"title": "secret", "likes": 99})
        found = await db.find("u1", "posts", {})
        assert len(found) == 1
        assert found[0]["title"] == "one"
        got = await db.get("u1", "posts", a["id"])
        assert got["title"] == "one"
        assert await db.get("u2", "posts", a["id"]) is None
        updated = await db.update("u1", "posts", a["id"], {"likes": 4})
        assert updated["likes"] == 4
        assert await db.delete("u1", "posts", a["id"]) is True
        assert await db.find("u1", "posts", {}) == []
        await s1.commit()

    await engine.dispose()
