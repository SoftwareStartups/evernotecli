"""Tests for ENML <-> Markdown conversion."""

import logging

from evernote_client.enml import enml_to_markdown, markdown_to_enml


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

    def test_media(self) -> None:
        enml = '<en-note><en-media hash="abc123" type="image/png"/></en-note>'
        md = enml_to_markdown(enml)
        assert md == "![attachment:image/png](abc123)"

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


class TestMarkdownToEnml:
    def test_empty_input(self) -> None:
        result = markdown_to_enml("")
        assert result == (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
            "<en-note></en-note>"
        )

    def test_heading(self) -> None:
        result = markdown_to_enml("# Hello")
        assert "<h1>Hello</h1>" in result

    def test_bold(self) -> None:
        result = markdown_to_enml("**bold text**")
        assert "<b>bold text</b>" in result

    def test_italic(self) -> None:
        result = markdown_to_enml("*italic text*")
        assert "<i>italic text</i>" in result

    def test_link(self) -> None:
        result = markdown_to_enml("[click](https://example.com)")
        assert '<a href="https://example.com">click</a>' in result

    def test_checkbox_checked(self) -> None:
        result = markdown_to_enml("- [x] Done")
        assert '<en-todo checked="true"/>' in result
        assert "Done" in result

    def test_checkbox_unchecked(self) -> None:
        result = markdown_to_enml("- [ ] Todo")
        assert "<en-todo/>" in result
        assert "Todo" in result

    def test_unordered_list(self) -> None:
        result = markdown_to_enml("- one\n- two")
        assert "<ul><li>one</li><li>two</li></ul>" in result

    def test_ordered_list(self) -> None:
        result = markdown_to_enml("1. first\n2. second")
        assert "<ol><li>first</li><li>second</li></ol>" in result

    def test_horizontal_rule(self) -> None:
        result = markdown_to_enml("---")
        assert "<hr/>" in result

    def test_paragraph(self) -> None:
        result = markdown_to_enml("Hello world")
        assert "<div>Hello world</div>" in result

    def test_xml_escaping(self) -> None:
        result = markdown_to_enml("a < b & c > d")
        assert "a &lt; b &amp; c &gt; d" in result

    def test_code_block(self) -> None:
        result = markdown_to_enml("```\nprint('hi')\n```")
        assert "<pre><code>print('hi')</code></pre>" in result

    def test_code_block_with_language(self) -> None:
        result = markdown_to_enml("```python\nx = 1\n```")
        assert "<pre><code>x = 1</code></pre>" in result

    def test_table(self) -> None:
        md = "| Name | Age |\n| --- | --- |\n| Alice | 30 |"
        result = markdown_to_enml(md)
        assert "<table>" in result
        assert "<tr><th>Name</th><th>Age</th></tr>" in result
        assert "<tr><td>Alice</td><td>30</td></tr>" in result
        assert "</table>" in result

    def test_valid_enml_structure(self) -> None:
        result = markdown_to_enml("test")
        assert result.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert "<!DOCTYPE en-note" in result
        assert result.endswith("</en-note>")

    def test_special_characters_in_text(self) -> None:
        result = markdown_to_enml('He said "hello" & <goodbye>')
        assert "&amp;" in result
        assert "&lt;goodbye&gt;" in result
        assert "&quot;hello&quot;" in result

    def test_empty_unordered_list_items(self) -> None:
        """A single list item should produce a valid list."""
        result = markdown_to_enml("- only one")
        assert "<ul><li>only one</li></ul>" in result

    def test_inline_code(self) -> None:
        result = markdown_to_enml("Use `foo()` here")
        assert "<code>foo()</code>" in result


class TestRoundTrip:
    def test_code_block_round_trip(self) -> None:
        md = "```\nx = 1\n```"
        enml = markdown_to_enml(md)
        result = enml_to_markdown(enml)
        lines = result.splitlines()
        assert lines[0] == "```"
        assert lines[1] == "x = 1"
        assert lines[2] == "```"

    def test_table_round_trip(self) -> None:
        md = "| Name | Age |\n| --- | --- |\n| Alice | 30 |"
        enml = markdown_to_enml(md)
        result = enml_to_markdown(enml)
        lines = [ln for ln in result.splitlines() if ln.strip()]
        assert lines[0] == "| Name | Age |"
        assert lines[1] == "| --- | --- |"
        assert lines[2] == "| Alice | 30 |"
