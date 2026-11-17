"""Tests for the `crucible browse` renderer and server state."""

import os

from crucible.browse import BibCache, org_to_html

ENTRY_A = "@misc{alpha2026,\n  title = {Alpha},\n  year = {2026},\n}\n"
ENTRY_B = "@online{beta2026,\n  title = {Beta},\n  url = {https://example.com},\n}\n"


def test_bib_cache_picks_up_entries_added_after_start(tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text(ENTRY_A, encoding="utf-8")
    cache = BibCache(bib)
    assert set(cache.get()) == {"alpha2026"}

    # A source ingested while the server runs appends to references.bib.
    bib.write_text(ENTRY_A + "\n" + ENTRY_B, encoding="utf-8")
    st = bib.stat()
    os.utime(bib, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))

    assert set(cache.get()) == {"alpha2026", "beta2026"}
    assert cache.get()["beta2026"]["url"] == "https://example.com"


def test_bib_cache_does_not_reparse_unchanged_file(tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text(ENTRY_A, encoding="utf-8")
    cache = BibCache(bib)
    assert cache.get() is cache.get()


def test_bib_cache_handles_missing_file(tmp_path):
    bib = tmp_path / "references.bib"
    cache = BibCache(bib)
    assert cache.get() == {}

    bib.write_text(ENTRY_A, encoding="utf-8")
    assert set(cache.get()) == {"alpha2026"}

    bib.unlink()
    assert cache.get() == {}


def test_table_cells_render_inline_math_and_markup():
    text = (
        "* A\n\n"
        "| Outcome | $H_0$ true | Note |\n"
        "|---------+------------+------|\n"
        "| Sig.    | $V$        | /it/ |\n"
    )
    _, body, _ = org_to_html(text)
    assert r'<span class="math-inline">\(H_0\)</span>' in body
    assert r'<span class="math-inline">\(V\)</span>' in body
    assert "<em>it</em>" in body
    assert "$V$" not in body


def _bump_mtime(*paths):
    for p in paths:
        if p.exists():
            st = p.stat()
            os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))


def test_article_cache_picks_up_articles_synced_after_start(tmp_path):
    from crucible.browse import ArticleCache
    from crucible.database import CrucibleDB

    db_path = tmp_path / "crucible.db"
    db = CrucibleDB(db_path)
    db.initialize()
    db.add_article(path="concepts/first.org", title="First Article",
                   article_type="concept")
    articles = db.list_articles()
    db.close()

    cache = ArticleCache(db_path, articles)
    assert "First Article" in cache.nav_html
    assert "Second Article" not in cache.nav_html

    # `crucible sync` adds an article while the server runs.
    db = CrucibleDB(db_path)
    db.add_article(path="concepts/second.org", title="Second Article",
                   article_type="concept")
    db.close()
    _bump_mtime(db_path, db_path.with_name("crucible.db-wal"))

    assert "Second Article" in cache.nav_html
    assert {a["title"] for a in cache.articles} == {"First Article", "Second Article"}


def test_article_cache_handles_missing_db(tmp_path):
    from crucible.browse import ArticleCache

    cache = ArticleCache(tmp_path / "crucible.db")
    assert cache.articles == []
    assert not (tmp_path / "crucible.db").exists()


def test_article_cache_keeps_previous_list_when_db_unreadable(tmp_path):
    from crucible.browse import ArticleCache

    db_path = tmp_path / "crucible.db"
    seed = [{"path": "concepts/a.org", "title": "Seeded", "article_type": "concept"}]
    db_path.write_bytes(b"")  # exists but has no schema
    cache = ArticleCache(db_path, seed)
    _bump_mtime(db_path)
    assert cache.articles == seed
