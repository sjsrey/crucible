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
