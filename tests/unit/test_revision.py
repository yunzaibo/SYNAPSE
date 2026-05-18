"""Tests for Thesis append-only revision management."""

import pytest

from synapse.core.revision import (
    ThesisDir,
    create_revision,
    get_current_revision,
    list_revisions,
)


@pytest.fixture
def thesis_workspace(tmp_path):
    """Create a thesis directory structure in a temp workspace."""
    thesis_id = "ths_7f8c91"
    slug = "consumer-recovery"
    thesis_dir = tmp_path / "thesis" / f"{thesis_id}_{slug}"
    thesis_dir.mkdir(parents=True)
    return tmp_path, thesis_id


class TestCreateRevision:
    """Tests for create_revision()."""

    def test_creates_rev_001(self, thesis_workspace):
        ws, tid = thesis_workspace
        rev_path = create_revision(tid, "# Revision 1", workspace=ws)
        assert rev_path.name == "rev-001.md"
        assert rev_path.exists()

    def test_content_written(self, thesis_workspace):
        ws, tid = thesis_workspace
        rev_path = create_revision(tid, "Hello world", workspace=ws)
        assert rev_path.read_text(encoding="utf-8") == "Hello world"

    def test_meta_yaml_updated(self, thesis_workspace):
        ws, tid = thesis_workspace
        create_revision(tid, "Rev 1", workspace=ws)
        meta_path = ws / "thesis" / f"{tid}_consumer-recovery" / "meta.yaml"
        assert meta_path.exists()
        import yaml

        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        assert meta["revision"] == 1
        assert "updated_at" in meta

    def test_append_only_second_revision(self, thesis_workspace):
        ws, tid = thesis_workspace
        create_revision(tid, "Rev 1", workspace=ws)
        rev2 = create_revision(tid, "Rev 2", workspace=ws)
        assert rev2.name == "rev-002.md"
        # Rev 001 still exists and is unchanged
        rev1 = ws / "thesis" / f"{tid}_consumer-recovery" / "rev-001.md"
        assert rev1.read_text(encoding="utf-8") == "Rev 1"

    def test_meta_points_to_latest(self, thesis_workspace):
        ws, tid = thesis_workspace
        create_revision(tid, "Rev 1", workspace=ws)
        create_revision(tid, "Rev 2", workspace=ws)
        import yaml

        meta_path = ws / "thesis" / f"{tid}_consumer-recovery" / "meta.yaml"
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        assert meta["revision"] == 2

    def test_raises_on_missing_thesis(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            create_revision("ths_nonexistent", "content", workspace=tmp_path)

    def test_three_revisions_sequential(self, thesis_workspace):
        ws, tid = thesis_workspace
        for i in range(1, 4):
            rev = create_revision(tid, f"Rev {i}", workspace=ws)
            assert rev.name == f"rev-{i:03d}.md"


class TestGetCurrentRevision:
    """Tests for get_current_revision()."""

    def test_no_revisions_returns_zero(self, thesis_workspace):
        ws, tid = thesis_workspace
        assert get_current_revision(tid, workspace=ws) == 0

    def test_after_one_revision(self, thesis_workspace):
        ws, tid = thesis_workspace
        create_revision(tid, "Rev 1", workspace=ws)
        assert get_current_revision(tid, workspace=ws) == 1

    def test_after_three_revisions(self, thesis_workspace):
        ws, tid = thesis_workspace
        for i in range(1, 4):
            create_revision(tid, f"Rev {i}", workspace=ws)
        assert get_current_revision(tid, workspace=ws) == 3

    def test_nonexistent_thesis(self, tmp_path):
        assert get_current_revision("ths_nope", workspace=tmp_path) == 0


class TestListRevisions:
    """Tests for list_revisions()."""

    def test_empty(self, thesis_workspace):
        ws, tid = thesis_workspace
        assert list_revisions(tid, workspace=ws) == []

    def test_returns_sorted(self, thesis_workspace):
        ws, tid = thesis_workspace
        create_revision(tid, "Rev 1", workspace=ws)
        create_revision(tid, "Rev 2", workspace=ws)
        create_revision(tid, "Rev 3", workspace=ws)
        assert list_revisions(tid, workspace=ws) == [1, 2, 3]

    def test_nonexistent_thesis(self, tmp_path):
        assert list_revisions("ths_nope", workspace=tmp_path) == []


class TestThesisDir:
    """Tests for ThesisDir helper."""

    def test_list_revisions_empty(self, tmp_path):
        td = ThesisDir(tmp_path)
        assert td.list_revisions() == []

    def test_next_revision_starts_at_1(self, tmp_path):
        td = ThesisDir(tmp_path)
        assert td.next_revision() == 1

    def test_next_revision_after_adding(self, tmp_path):
        (tmp_path / "rev-001.md").touch()
        td = ThesisDir(tmp_path)
        assert td.next_revision() == 2
