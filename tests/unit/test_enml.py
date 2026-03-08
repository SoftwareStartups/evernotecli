"""Tests for ENML <-> Markdown conversion."""

import logging
import tempfile
from pathlib import Path

from evernote_client.enml import enml_to_markdown, markdown_to_enml
from evernote_client.enml.types import ResourceInfo


class TestEnmlToMarkdown:
    def test_empty_input(self) -> None:
        assert enml_to_markdown("") == ""

    def test_simple_text(self) -> None:
        enml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
            "<en-note><div>Hello world</div></en-note>"
        )
        assert enml_to_markdown(enml) == "Hello world"

    def test_headings(self) -> None:
        enml = "<en-note><h1>Title</h1><h2>Subtitle</h2></en-note>"
        md = enml_to_markdown(enml)
        lines = [ln for ln in md.splitlines() if ln.strip()]
        assert lines[0] == "# Title"
        assert lines[1] == "## Subtitle"

    def test_bold_and_italic(self) -> None:
        enml = "<en-note><div><b>bold</b> and <i>italic</i></div></en-note>"
        md = enml_to_markdown(enml)
        assert md.strip() == "**bold** and *italic*"

    def test_link(self) -> None:
        enml = '<en-note><div><a href="https://example.com">link</a></div></en-note>'
        md = enml_to_markdown(enml)
        assert md.strip() == "[link](https://example.com)"

    def test_unordered_list(self) -> None:
        enml = "<en-note><ul><li>one</li><li>two</li></ul></en-note>"
        md = enml_to_markdown(enml)
        lines = md.strip().splitlines()
        assert lines[0] == "- one"
        assert lines[1] == "- two"

    def test_ordered_list(self) -> None:
        enml = "<en-note><ol><li>first</li><li>second</li></ol></en-note>"
        md = enml_to_markdown(enml)
        lines = md.strip().splitlines()
        assert lines[0] == "1. first"
        assert lines[1] == "2. second"

    def test_ordered_list_with_non_li_children(self) -> None:
        """OL numbering should only count <li> elements, not other children."""
        enml = (
            "<en-note><ol>"
            "<div>ignored</div>"
            "<li>first</li>"
            "<li>second</li>"
            "</ol></en-note>"
        )
        md = enml_to_markdown(enml)
        assert "1. first" in md
        assert "2. second" in md
        # Should NOT have "3. second" from counting the div
        assert "3." not in md

    def test_todo_checked(self) -> None:
        enml = '<en-note><div><en-todo checked="true"/>Done task</div></en-note>'
        md = enml_to_markdown(enml)
        assert "- [x]" in md
        assert "Done task" in md

    def test_todo_unchecked(self) -> None:
        enml = "<en-note><div><en-todo/>Pending task</div></en-note>"
        md = enml_to_markdown(enml)
        assert "- [ ]" in md
        assert "Pending task" in md

    def test_media_no_resource_info(self) -> None:
        enml = '<en-note><en-media hash="abc123ef" type="image/png"/></en-note>'
        md = enml_to_markdown(enml)
        # Falls back: hash[:8] as display, evernote-resource: URL scheme, image → ![]()
        assert md == "![abc123ef](evernote-resource:abc123ef)"

    def test_encrypted(self) -> None:
        enml = "<en-note><en-crypt>secret</en-crypt></en-note>"
        md = enml_to_markdown(enml)
        assert md == "[Encrypted Content]"

    def test_horizontal_rule(self) -> None:
        enml = "<en-note><hr/></en-note>"
        md = enml_to_markdown(enml)
        assert md == "---"

    def test_table(self) -> None:
        enml = (
            "<en-note><table>"
            "<tr><th>Name</th><th>Age</th></tr>"
            "<tr><td>Alice</td><td>30</td></tr>"
            "</table></en-note>"
        )
        md = enml_to_markdown(enml)
        lines = [ln for ln in md.splitlines() if ln.strip()]
        assert lines[0] == "| Name | Age |"
        assert lines[1] == "| --- | --- |"
        assert lines[2] == "| Alice | 30 |"

    def test_pre_block(self) -> None:
        enml = "<en-note><pre>some code</pre></en-note>"
        md = enml_to_markdown(enml)
        lines = md.splitlines()
        assert lines[0] == "```"
        assert lines[1] == "some code"
        assert lines[2] == "```"

    def test_pre_with_code(self) -> None:
        enml = "<en-note><pre><code>x = 1</code></pre></en-note>"
        md = enml_to_markdown(enml)
        lines = md.splitlines()
        assert lines[0] == "```"
        assert lines[1] == "x = 1"
        assert lines[2] == "```"

    def test_complex_note(self) -> None:
        enml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
            "<en-note>"
            "<h1>Meeting Notes</h1>"
            "<div>Discussed <b>project</b> timeline.</div>"
            '<div><en-todo checked="true"/>Review PRs</div>'
            "<div><en-todo/>Write docs</div>"
            "</en-note>"
        )
        md = enml_to_markdown(enml)
        assert "# Meeting Notes" in md
        assert "**project**" in md
        assert "- [x]" in md
        assert "- [ ]" in md

    def test_parse_error_falls_back_to_strip(self, caplog: object) -> None:
        """Invalid XML should log a warning and fall back to tag stripping."""
        import _pytest.logging

        assert isinstance(caplog, _pytest.logging.LogCaptureFixture)
        logger = "evernote_client.enml.to_markdown"
        with caplog.at_level(logging.WARNING, logger=logger):
            result = enml_to_markdown("<en-note><unclosed>hello</en-note>")
        assert "hello" in result
        assert "Failed to parse ENML" in caplog.text

    def test_empty_list(self) -> None:
        enml = "<en-note><ul></ul></en-note>"
        md = enml_to_markdown(enml)
        # Empty list should produce no list items
        assert "- " not in md

    def test_enml_to_markdown_image_resource(self) -> None:
        """en-media image resource with info → ![name](evernote-resource:hash)"""
        hash_hex = "a" * 32
        enml = f'<en-note><en-media hash="{hash_hex}" type="image/png"/></en-note>'
        resources = [
            ResourceInfo(hash_hex=hash_hex, mime_type="image/png", filename="photo.png")
        ]
        md = enml_to_markdown(enml, resources=resources)
        assert f"![photo.png](evernote-resource:{hash_hex})" == md

    def test_enml_to_markdown_non_image_resource(self) -> None:
        """en-media with non-image mime type → [name](evernote-resource:hash)"""
        hash_hex = "b" * 32
        enml = (
            f'<en-note><en-media hash="{hash_hex}" type="application/pdf"/></en-note>'
        )
        resources = [
            ResourceInfo(
                hash_hex=hash_hex, mime_type="application/pdf", filename="doc.pdf"
            )
        ]
        md = enml_to_markdown(enml, resources=resources)
        assert f"[doc.pdf](evernote-resource:{hash_hex})" == md


class TestMarkdownToEnml:
    def test_empty_input(self) -> None:
        result = markdown_to_enml("")
        assert result.enml == (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
            "<en-note></en-note>"
        )
        assert result.attachments == []

    def test_heading(self) -> None:
        result = markdown_to_enml("# Hello")
        assert "<h1>Hello</h1>" in result.enml

    def test_bold(self) -> None:
        result = markdown_to_enml("**bold text**")
        assert "<b>bold text</b>" in result.enml

    def test_italic(self) -> None:
        result = markdown_to_enml("*italic text*")
        assert "<i>italic text</i>" in result.enml

    def test_link(self) -> None:
        result = markdown_to_enml("[click](https://example.com)")
        assert '<a href="https://example.com">click</a>' in result.enml

    def test_checkbox_checked(self) -> None:
        result = markdown_to_enml("- [x] Done")
        assert '<en-todo checked="true"/>' in result.enml
        assert "Done" in result.enml

    def test_checkbox_unchecked(self) -> None:
        result = markdown_to_enml("- [ ] Todo")
        assert "<en-todo/>" in result.enml
        assert "Todo" in result.enml

    def test_unordered_list(self) -> None:
        result = markdown_to_enml("- one\n- two")
        assert "<ul><li>one</li><li>two</li></ul>" in result.enml

    def test_ordered_list(self) -> None:
        result = markdown_to_enml("1. first\n2. second")
        assert "<ol><li>first</li><li>second</li></ol>" in result.enml

    def test_horizontal_rule(self) -> None:
        result = markdown_to_enml("---")
        assert "<hr/>" in result.enml

    def test_paragraph(self) -> None:
        result = markdown_to_enml("Hello world")
        assert "<div>Hello world</div>" in result.enml

    def test_xml_escaping(self) -> None:
        result = markdown_to_enml("a < b & c > d")
        assert "a &lt; b &amp; c &gt; d" in result.enml

    def test_code_block(self) -> None:
        result = markdown_to_enml("```\nprint('hi')\n```")
        assert "<pre><code>print('hi')</code></pre>" in result.enml

    def test_code_block_with_language(self) -> None:
        result = markdown_to_enml("```python\nx = 1\n```")
        assert "<pre><code>x = 1</code></pre>" in result.enml

    def test_table(self) -> None:
        md = "| Name | Age |\n| --- | --- |\n| Alice | 30 |"
        result = markdown_to_enml(md)
        assert "<table>" in result.enml
        assert "<tr><th>Name</th><th>Age</th></tr>" in result.enml
        assert "<tr><td>Alice</td><td>30</td></tr>" in result.enml
        assert "</table>" in result.enml

    def test_valid_enml_structure(self) -> None:
        result = markdown_to_enml("test")
        assert result.enml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert "<!DOCTYPE en-note" in result.enml
        assert result.enml.endswith("</en-note>")

    def test_special_characters_in_text(self) -> None:
        result = markdown_to_enml('He said "hello" & <goodbye>')
        assert "&amp;" in result.enml
        assert "&lt;goodbye&gt;" in result.enml
        assert "&quot;hello&quot;" in result.enml

    def test_empty_unordered_list_items(self) -> None:
        """A single list item should produce a valid list."""
        result = markdown_to_enml("- only one")
        assert "<ul><li>only one</li></ul>" in result.enml

    def test_inline_code(self) -> None:
        result = markdown_to_enml("Use `foo()` here")
        assert "<code>foo()</code>" in result.enml

    def test_image_evernote_resource_known(self) -> None:
        """evernote-resource: URL with known resource → <en-media>"""
        hash_hex = "a" * 32
        resources = [
            ResourceInfo(hash_hex=hash_hex, mime_type="image/png", filename="photo.png")
        ]
        md = f"![photo](evernote-resource:{hash_hex})"
        result = markdown_to_enml(md, existing_resources=resources)
        assert f'<en-media type="image/png" hash="{hash_hex}"/>' in result.enml
        assert result.attachments == []

    def test_image_evernote_resource_unknown(self) -> None:
        """evernote-resource: URL with unknown hash → fallback link"""
        hash_hex = "b" * 32
        md = f"![photo](evernote-resource:{hash_hex})"
        result = markdown_to_enml(md)
        assert "<a href=" in result.enml
        assert result.attachments == []

    def test_image_local_file(self) -> None:
        """Local image file → <en-media> + Attachment"""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
            tmp_path = f.name
        try:
            result = markdown_to_enml(f"![alt]({tmp_path})")
            assert '<en-media type="image/png"' in result.enml
            assert len(result.attachments) == 1
            att = result.attachments[0]
            assert att.mime_type == "image/png"
            assert att.filename == Path(tmp_path).name
            assert len(att.data) > 0
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_image_http_url(self) -> None:
        """HTTP image URL → <a href> link"""
        result = markdown_to_enml("![pic](https://example.com/img.png)")
        assert "<a href=" in result.enml
        assert result.attachments == []

    def test_image_deduplication(self) -> None:
        """Same local file referenced twice → one Attachment"""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
            tmp_path = f.name
        try:
            md = f"![a]({tmp_path})\n![b]({tmp_path})"
            result = markdown_to_enml(md)
            assert len(result.attachments) == 1
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestRoundTrip:
    def test_code_block_round_trip(self) -> None:
        md = "```\nx = 1\n```"
        enml = markdown_to_enml(md).enml
        result = enml_to_markdown(enml)
        lines = result.splitlines()
        assert lines[0] == "```"
        assert lines[1] == "x = 1"
        assert lines[2] == "```"

    def test_table_round_trip(self) -> None:
        md = "| Name | Age |\n| --- | --- |\n| Alice | 30 |"
        enml = markdown_to_enml(md).enml
        result = enml_to_markdown(enml)
        lines = [ln for ln in result.splitlines() if ln.strip()]
        assert lines[0] == "| Name | Age |"
        assert lines[1] == "| --- | --- |"
        assert lines[2] == "| Alice | 30 |"
