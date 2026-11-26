"""owner 26 Nov: the News360 Backend website (Cloudflare Pages) is built from Index.html and talks to the store only through /api."""
import shutil, subprocess, sys, unittest, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "dashboard"
sys.path.insert(0, str(D))
import build_worker      # noqa: E402


class BackendSite(unittest.TestCase):
    def test_built_files_match_the_page(self):
        before = (D / "pages" / "_worker.js").read_text(encoding="utf-8")
        build_worker.build()
        after = (D / "pages" / "_worker.js").read_text(encoding="utf-8")
        self.assertEqual(before, after, "dashboard/pages/_worker.js is out of date - run python dashboard/build_worker.py")
        z = zipfile.ZipFile(D / "pages" / "news360-backend.zip")
        self.assertEqual(z.namelist(), ["_worker.js"])
        self.assertEqual(z.read("_worker.js").decode("utf-8"), after)

    def test_no_secret_or_store_link_in_the_site(self):
        js = (D / "pages" / "_worker.js").read_text(encoding="utf-8")
        self.assertNotIn("script.google.com/macros/s/", js.replace("https://script.google.com/macros/s/.../exec", ""))
        self.assertIn("env.DASH_URL", js)
        self.assertIn("'/api/login'", js)

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_end_to_end_with_the_store(self):
        p = subprocess.run(["node", str(D / "e2e_test.mjs"), str(D)], capture_output=True, text=True, timeout=120)
        self.assertNotIn("FAIL", p.stdout, p.stdout + p.stderr)
        self.assertGreaterEqual(p.stdout.count("PASS"), 9, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()


class NoIndexTest(unittest.TestCase):
    def test_the_private_dashboard_is_never_indexed(self):
        html = (ROOT / "dashboard" / "Index.html").read_text(encoding="utf-8")
        self.assertIn('name="robots" content="noindex, nofollow, noarchive"', html)
        w = (ROOT / "dashboard" / "worker_template.js").read_text(encoding="utf-8")
        self.assertIn("'X-Robots-Tag': 'noindex, nofollow, noarchive'", w)
        self.assertIn("url.pathname === '/robots.txt'", w)
        self.assertIn("Disallow: /", w)
