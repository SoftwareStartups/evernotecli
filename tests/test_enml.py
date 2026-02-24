"""Tests for ENML <-> Markdown conversion."""

from evernote_mcp.enml import enml_to_markdown, markdown_to_enml


class TestEnmlToMarkdown:
    def test_empty_input(self) -> None:
        assert enml_to_markdown("") == ""

    def test_simple_text(self) -> None:
        enml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
            "<en-note><div>Hello world</div></en-note>"
        )
        assert "Hello world" in enml_to_markdown(enml)

    def test_headings(self) -> None:
        enml = "<en-note><h1>Title</h1><h2>Subtitle</h2></en-note>"
        md = enml_to_markdown(enml)
        assert "# Title" in md
        assert "## Subtitle" in md

    def test_bold_and_italic(self) -> None:
        enml = "<en-note><div><b>bold</b> and <i>italic</i></div></en-note>"
        md = enml_to_markdown(enml)
        assert "**bold**" in md
        assert "*italic*" in md

    def test_link(self) -> None:
        enml = '<en-note><div><a href="https://example.com">link</a></div></en-note>'
        md = enml_to_markdown(enml)
        assert "[link](https://example.com)" in md

    def test_unordered_list(self) -> None:
        enml = "<en-note><ul><li>one</li><li>two</li></ul></en-note>"
        md = enml_to_markdown(enml)
        assert "- one" in md
        assert "- two" in md

    def test_ordered_list(self) -> None:
        enml = "<en-note><ol><li>first</li><li>second</li></ol></en-note>"
        md = enml_to_markdown(enml)
        assert "1. first" in md
        assert "2. second" in md

    def test_todo_checked(self) -> None:
        enml = '<en-note><div><en-todo checked="true"/>Done task</div></en-note>'
        md = enml_to_markdown(enml)
        assert "[x]" in md

    def test_todo_unchecked(self) -> None:
        enml = "<en-note><div><en-todo/>Pending task</div></en-note>"
        md = enml_to_markdown(enml)
        assert "[ ]" in md

    def test_media(self) -> None:
        enml = '<en-note><en-media hash="abc123" type="image/png"/></en-note>'
        md = enml_to_markdown(enml)
        assert "![attachment:image/png](abc123)" in md

    def test_encrypted(self) -> None:
        enml = "<en-note><en-crypt>secret</en-crypt></en-note>"
        md = enml_to_markdown(enml)
        assert "[Encrypted Content]" in md

    def test_horizontal_rule(self) -> None:
        enml = "<en-note><hr/></en-note>"
        md = enml_to_markdown(enml)
        assert "---" in md

    def test_table(self) -> None:
        enml = (
            "<en-note><table>"
            "<tr><th>Name</th><th>Age</th></tr>"
            "<tr><td>Alice</td><td>30</td></tr>"
            "</table></en-note>"
        )
        md = enml_to_markdown(enml)
        assert "| Name | Age |" in md
        assert "| Alice | 30 |" in md

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
        assert "[x]" in md
        assert "[ ]" in md


class TestMarkdownToEnml:
    def test_empty_input(self) -> None:
        result = markdown_to_enml("")
        assert "<en-note>" in result
        assert "</en-note>" in result

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
        assert 'en-todo checked="true"' in result
        assert "Done" in result

    def test_checkbox_unchecked(self) -> None:
        result = markdown_to_enml("- [ ] Todo")
        assert "<en-todo/>" in result
        assert "Todo" in result

    def test_unordered_list(self) -> None:
        result = markdown_to_enml("- one\n- two")
        assert "<ul>" in result
        assert "<li>one</li>" in result
        assert "<li>two</li>" in result

    def test_ordered_list(self) -> None:
        result = markdown_to_enml("1. first\n2. second")
        assert "<ol>" in result
        assert "<li>first</li>" in result

    def test_horizontal_rule(self) -> None:
        result = markdown_to_enml("---")
        assert "<hr/>" in result

    def test_paragraph(self) -> None:
        result = markdown_to_enml("Hello world")
        assert "<div>Hello world</div>" in result

    def test_xml_escaping(self) -> None:
        result = markdown_to_enml("a < b & c > d")
        assert "&lt;" in result
        assert "&amp;" in result
        assert "&gt;" in result

    def test_valid_enml_structure(self) -> None:
        result = markdown_to_enml("test")
        assert result.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert "<!DOCTYPE en-note" in result
        assert result.endswith("</en-note>")
