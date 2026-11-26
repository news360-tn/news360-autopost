"""owner 26 Nov: the website keeps its own small copy of each story's pictures (R2 links are deleted after 24 hours)."""
import base64
import io
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))
import thumb_sync as ts      # noqa: E402
from PIL import Image        # noqa: E402


def jpeg(w=1600, h=900, color=(200, 80, 40)):
    b = io.BytesIO()
    Image.new("RGB", (w, h), color).save(b, "JPEG")
    return b.getvalue()


class ThumbSyncTest(unittest.TestCase):
    def test_shrink_makes_a_small_webp(self):
        b64 = ts.shrink(jpeg())
        im = Image.open(io.BytesIO(base64.b64decode(b64)))
        self.assertEqual(im.format, "WEBP")
        self.assertLessEqual(max(im.size), 720)
        self.assertLessEqual(len(b64), ts.MAX_CHARS)
        self.assertIsNone(ts.shrink(b"not an image"))

    def test_only_stories_without_a_copy_and_with_picture_links(self):
        items = [{"id": "RN-1", "thumbs": 0, "images": ["https://r2/a.jpg"]}, {"id": "RN-2", "thumbs": 1, "images": ["https://r2/b.jpg"]},
                 {"id": "RN-3", "thumbs": 0, "images": []}, {"id": "RN-4", "images": ["http://insecure/x.jpg"]}]
        get = mock.Mock(return_value=mock.Mock(status_code=200, json=lambda: {"items": items}))
        got = ts.stories_without_copy(pages=3, get=get)
        self.assertEqual([s["id"] for s in got], ["RN-1"])
        self.assertEqual(get.call_count, 1)      # fewer than a full page: no more pages asked

    def test_build_keeps_the_pictures_that_still_load_and_leaves_gone_stories_out(self):
        pics = {"https://r2/a.jpg": jpeg(), "https://r2/c.jpg": jpeg(800, 800)}
        stories = [{"id": "RN-1", "images": ["https://r2/a.jpg", "https://r2/gone.jpg", "https://r2/c.jpg"]}, {"id": "RN-9", "images": ["https://r2/gone2.jpg"]}]
        out = ts.build(stories, fetch=lambda u: pics.get(u))
        self.assertEqual([o["id"] for o in out], ["RN-1"])
        self.assertEqual(len(out[0]["thumbs"]), 2)

    def test_fetch_accepts_only_images(self):
        ok = mock.Mock(return_value=mock.Mock(status_code=200, headers={"content-type": "image/jpeg"}, content=b"x" * 10))
        self.assertEqual(ts.fetch_image("https://r2/a.jpg", get=ok), b"x" * 10)
        html = mock.Mock(return_value=mock.Mock(status_code=200, headers={"content-type": "text/html"}, content=b"x"))
        self.assertIsNone(ts.fetch_image("https://r2/a.jpg", get=html))
        gone = mock.Mock(return_value=mock.Mock(status_code=404, headers={}, content=b""))
        self.assertIsNone(ts.fetch_image("https://r2/a.jpg", get=gone))
        self.assertIsNone(ts.fetch_image("https://r2/a.jpg", get=mock.Mock(side_effect=OSError("down"))))

    def test_send_groups_of_5_and_a_wrong_key_stops(self):
        items = [{"id": f"RN-{i}", "thumbs": ["A" * 200]} for i in range(12)]
        sizes = []

        def ok(url, json, **k):
            sizes.append(len(json))
            return mock.Mock(status_code=200, json=lambda: {"saved": [x["id"] for x in json], "skipped": []})
        self.assertEqual(ts.send(items, "KEY", post=ok), (12, 0))
        self.assertEqual(sizes, [5, 5, 2])
        bad = mock.Mock(return_value=mock.Mock(status_code=401, text="unauthorized"))
        self.assertEqual(ts.send(items, "BAD", post=bad), (0, 0))
        self.assertEqual(bad.call_count, 1)

    def test_no_key_sends_nothing_and_never_fails(self):
        with mock.patch.object(ts, "stories_without_copy", return_value=[{"id": "RN-1", "images": ["https://r2/a.jpg"]}]), \
                mock.patch.object(ts, "build", return_value=[{"id": "RN-1", "thumbs": ["A"]}]), \
                mock.patch.dict("os.environ", {"WEBSITE_INGEST_KEY": ""}), mock.patch.object(ts, "send") as s:
            self.assertEqual(ts.main([]), 0)
        s.assert_not_called()


if __name__ == "__main__":
    unittest.main()
