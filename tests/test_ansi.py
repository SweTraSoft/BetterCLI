from cligui.ui.ansi import ansi_to_html


def test_ansi_to_html_renders_colors_and_escapes_text():
    rendered = ansi_to_html("\x1b[1;31m<unsafe>\x1b[0m")
    styled_text = '<span style="color:#cd0000;font-weight:bold">&lt;unsafe&gt;</span>'

    assert styled_text in rendered


def test_ansi_to_html_supports_extended_colors():
    rendered = ansi_to_html("\x1b[38;2;12;34;56mRGB\x1b[0m")

    assert '<span style="color:#0c2238">RGB</span>' in rendered


def test_ansi_to_html_drops_non_style_control_sequences():
    rendered = ansi_to_html("one\x1b[2Jtwo")

    assert rendered == "<pre>onetwo</pre>"


def test_ansi_to_html_cleans_man_page_overstrike():
    assert ansi_to_html("N\x08NA\x08AM\x08ME\x08E") == "<pre>NAME</pre>"
