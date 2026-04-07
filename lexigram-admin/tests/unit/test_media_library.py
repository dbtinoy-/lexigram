"""Tests for the media library."""

from __future__ import annotations

import pytest

from lexigram.admin.media import MediaItem, MediaLibrary, MediaPage


# ---------------------------------------------------------------------------
# MediaItem
# ---------------------------------------------------------------------------

class TestMediaItem:
    def test_extension(self) -> None:
        item = MediaItem(filename="photo.JPG")
        assert item.extension == "jpg"

    def test_extension_no_dot(self) -> None:
        item = MediaItem(filename="README")
        assert item.extension == ""

    def test_is_image(self) -> None:
        item = MediaItem(mime_type="image/png")
        assert item.is_image is True
        assert item.is_video is False

    def test_is_video(self) -> None:
        item = MediaItem(mime_type="video/mp4")
        assert item.is_video is True
        assert item.is_image is False

    def test_is_document_pdf(self) -> None:
        item = MediaItem(mime_type="application/pdf")
        assert item.is_document is True

    def test_to_dict_includes_extension(self) -> None:
        item = MediaItem(filename="cat.png", mime_type="image/png")
        d = item.to_dict()
        assert d["extension"] == "png"
        assert d["is_image"] is True


# ---------------------------------------------------------------------------
# MediaLibrary — register
# ---------------------------------------------------------------------------

class TestMediaLibraryRegister:
    @pytest.mark.asyncio
    async def test_register_returns_item(self) -> None:
        lib = MediaLibrary()
        item = await lib.register("uploads/cat.jpg", mime_type="image/jpeg", size_bytes=1000)
        assert item.path == "uploads/cat.jpg"
        assert item.filename == "cat.jpg"
        assert item.mime_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_folder_derived_from_path(self) -> None:
        lib = MediaLibrary()
        item = await lib.register("uploads/2024/photo.png")
        assert item.folder == "uploads/2024"

    @pytest.mark.asyncio
    async def test_filename_derived_from_path(self) -> None:
        lib = MediaLibrary()
        item = await lib.register("uploads/doc.pdf")
        assert item.filename == "doc.pdf"

    @pytest.mark.asyncio
    async def test_explicit_item_id(self) -> None:
        lib = MediaLibrary()
        item = await lib.register("uploads/x.jpg", item_id="custom-id")
        assert item.item_id == "custom-id"

    @pytest.mark.asyncio
    async def test_tags_stored(self) -> None:
        lib = MediaLibrary()
        item = await lib.register("uploads/x.jpg", tags=["hero", "banner"])
        assert "hero" in item.tags


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

class TestMediaLibraryUpdate:
    @pytest.mark.asyncio
    async def test_update_alt_text(self) -> None:
        lib = MediaLibrary()
        item = await lib.register("uploads/cat.jpg")
        updated = lib.update(item.item_id, alt_text="A cute cat")
        assert updated is not None
        assert updated.alt_text == "A cute cat"

    @pytest.mark.asyncio
    async def test_update_tags(self) -> None:
        lib = MediaLibrary()
        item = await lib.register("uploads/cat.jpg")
        lib.update(item.item_id, tags=["nature", "animals"])
        refreshed = lib.get(item.item_id)
        assert refreshed is not None
        assert "nature" in refreshed.tags

    def test_update_missing_returns_none(self) -> None:
        lib = MediaLibrary()
        assert lib.update("ghost", alt_text="x") is None


# ---------------------------------------------------------------------------
# List folder
# ---------------------------------------------------------------------------

class TestListFolder:
    @pytest.mark.asyncio
    async def test_list_all(self) -> None:
        lib = MediaLibrary()
        await lib.register("uploads/a.jpg")
        await lib.register("uploads/b.png")
        page = lib.list_folder()
        assert page.total == 2

    @pytest.mark.asyncio
    async def test_list_by_folder(self) -> None:
        lib = MediaLibrary()
        await lib.register("uploads/2024/a.jpg")
        await lib.register("uploads/2025/b.jpg")
        page = lib.list_folder("uploads/2024")
        assert page.total == 1
        assert page.items[0].filename == "a.jpg"

    @pytest.mark.asyncio
    async def test_pagination(self) -> None:
        lib = MediaLibrary()
        for i in range(5):
            await lib.register(f"uploads/{i}.jpg")
        page = lib.list_folder(page=1, page_size=3)
        assert len(page.items) == 3
        assert page.total == 5
        assert page.has_next is True
        assert page.has_prev is False

    @pytest.mark.asyncio
    async def test_page_2(self) -> None:
        lib = MediaLibrary()
        for i in range(5):
            await lib.register(f"uploads/{i}.jpg")
        page = lib.list_folder(page=2, page_size=3)
        assert len(page.items) == 2
        assert page.has_next is False
        assert page.has_prev is True

    @pytest.mark.asyncio
    async def test_deleted_excluded_by_default(self) -> None:
        lib = MediaLibrary()
        item = await lib.register("uploads/a.jpg")
        lib.soft_delete(item.item_id)
        page = lib.list_folder()
        assert page.total == 0

    @pytest.mark.asyncio
    async def test_include_deleted(self) -> None:
        lib = MediaLibrary()
        item = await lib.register("uploads/a.jpg")
        lib.soft_delete(item.item_id)
        page = lib.list_folder(include_deleted=True)
        assert page.total == 1


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class TestSearch:
    @pytest.mark.asyncio
    async def test_search_by_filename(self) -> None:
        lib = MediaLibrary()
        await lib.register("uploads/cat.jpg", filename="cat.jpg")
        await lib.register("uploads/dog.jpg", filename="dog.jpg")
        results = lib.search("cat")
        assert len(results) == 1
        assert results[0].filename == "cat.jpg"

    @pytest.mark.asyncio
    async def test_search_by_alt_text(self) -> None:
        lib = MediaLibrary()
        item = await lib.register("uploads/photo.jpg", alt_text="sunny beach day")
        results = lib.search("beach")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_by_mime_prefix(self) -> None:
        lib = MediaLibrary()
        await lib.register("uploads/img.jpg", mime_type="image/jpeg")
        await lib.register("uploads/doc.pdf", mime_type="application/pdf")
        results = lib.search("", mime_prefix="image/")
        assert len(results) == 1
        assert results[0].mime_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_search_by_tags(self) -> None:
        lib = MediaLibrary()
        await lib.register("uploads/a.jpg", tags=["hero"])
        await lib.register("uploads/b.jpg", tags=["banner"])
        results = lib.search("", tags=["hero"])
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self) -> None:
        lib = MediaLibrary()
        await lib.register("uploads/MyPhoto.jpg", filename="MyPhoto.jpg")
        results = lib.search("myphoto")
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Soft delete / restore / purge
# ---------------------------------------------------------------------------

class TestSoftDeleteRestorePurge:
    @pytest.mark.asyncio
    async def test_soft_delete_marks_deleted(self) -> None:
        lib = MediaLibrary()
        item = await lib.register("uploads/a.jpg")
        lib.soft_delete(item.item_id)
        assert lib.get(item.item_id) is not None
        assert lib.get(item.item_id).is_deleted is True  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_restore_unmarks_deleted(self) -> None:
        lib = MediaLibrary()
        item = await lib.register("uploads/a.jpg")
        lib.soft_delete(item.item_id)
        lib.restore(item.item_id)
        assert lib.get(item.item_id).is_deleted is False  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_trash_returns_deleted(self) -> None:
        lib = MediaLibrary()
        item = await lib.register("uploads/a.jpg")
        lib.soft_delete(item.item_id)
        assert len(lib.trash()) == 1

    @pytest.mark.asyncio
    async def test_purge_removes_item(self) -> None:
        lib = MediaLibrary()
        item = await lib.register("uploads/a.jpg")
        result = await lib.purge(item.item_id)
        assert result is True
        assert lib.get(item.item_id) is None

    @pytest.mark.asyncio
    async def test_purge_missing_returns_false(self) -> None:
        lib = MediaLibrary()
        result = await lib.purge("ghost")
        assert result is False


# ---------------------------------------------------------------------------
# list_folders
# ---------------------------------------------------------------------------

class TestListFolders:
    @pytest.mark.asyncio
    async def test_returns_unique_sorted_folders(self) -> None:
        lib = MediaLibrary()
        await lib.register("uploads/2024/a.jpg")
        await lib.register("uploads/2025/b.jpg")
        await lib.register("uploads/2024/c.jpg")
        folders = lib.list_folders()
        assert folders == ["uploads/2024", "uploads/2025"]
