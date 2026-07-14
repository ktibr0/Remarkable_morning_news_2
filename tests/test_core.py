import asyncio

import remarkable_news.delivery as delivery
from remarkable_news.fetcher import clean_html, text_length
from remarkable_news.delivery import RmapiResult, _add_lead_image, _image_mime, summarize_rmapi_output


def test_clean_html_removes_scripts_and_resolves_links():
    value = '<script>alert(1)</script><p>Hello <a href="/news">world</a></p>'
    result = clean_html(value, "https://example.org/base", images=False)
    assert "<script" not in result
    assert 'href="https://example.org/news"' in result
    assert text_length(result) >= 10


def test_clean_html_can_drop_images():
    result = clean_html('<p>Text</p><img src="https://example.org/a.jpg">', "https://example.org", images=False)
    assert "<img" not in result


def test_lead_image_is_added_when_extracted_article_has_none():
    result = _add_lead_image("<p>Article body</p>", "https://example.org/lead.jpg")
    assert result.startswith("<figure>")
    assert 'src="https://example.org/lead.jpg"' in result


def test_existing_article_image_is_not_duplicated():
    content = '<p>Text</p><img src="https://example.org/inside.jpg">'
    assert _add_lead_image(content, "https://example.org/lead.jpg") == content


def test_image_type_can_be_detected_when_server_uses_generic_content_type():
    assert _image_mime("application/octet-stream", b"\x89PNG\r\n\x1a\ncontent") == "image/png"


def test_rmapi_summary_keeps_cause_and_drops_large_worker_dump():
    raw = "fatal error: test failure\nError: auth failed\n" + ("goroutine worker\n" * 500)
    result = summarize_rmapi_output(raw)
    assert "fatal error: test failure" in result
    assert "auth failed" in result
    assert len(result) <= 2000
    assert "полный дамп сохранён" in result


def test_authorization_uses_a_real_cloud_command(monkeypatch, tmp_path):
    config = tmp_path / "rmapi.conf"
    calls = []

    async def fake_run(arguments, **kwargs):
        calls.append((arguments, kwargs))
        config.write_text("devicetoken: token\nusertoken: token\n", encoding="utf-8")
        return RmapiResult(True, "[]", "[]", 0)

    monkeypatch.setattr(delivery, "RMAPI_CONFIG", config)
    monkeypatch.setattr(delivery, "run_rmapi", fake_run)
    result = asyncio.run(delivery.authorize_rmapi("one-time-code"))
    assert result["success"] is True
    assert calls[0][0] == ["-json", "ls", "/"]
    assert calls[0][1]["input_text"] == "one-time-code\n"
