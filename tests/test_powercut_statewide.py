"""owner 13 Nov: Namakkal's power cuts are often printed only in the daily STATE-WIDE lists (News18 / ABP Live / Samayam).
Only the Namakkal part of such a list is written; a list without one is refused; a notice filed under another district's page is refused."""
import datetime, json, sys, unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research_free"))
import allnews      # noqa: E402
import powercut     # noqa: E402

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
LIST_URL = "https://tamil.abplive.com/news/tamil-nadu/tamilnadu-power-shutdown-12-11-2026-vellore-karur-kovai"
BODY = ("தமிழ்நாட்டில் நாளை காலை 9 மணி முதல் மாலை 5 மணி வரை பராமரிப்புப் பணிகள் காரணமாக மின் விநியோகம் நிறுத்தப்படும். "
        "வேலூர், கரூர், கோவை உள்ளிட்ட மாவட்டங்களில் மின்தடை. "
        "வேலூர் மாவட்டம் காட்பாடி, சத்துவாச்சாரி. நாமக்கல் மாவட்டம் சமயசங்கிலி, ஆலையபட்டி, பருத்திப்பள்ளி. "
        "கரூர் மாவட்டம் பாலம்பாள்புரம், ஐந்து ரோடு. சேலம்: அஸ்தம்பட்டி, சூரமங்கலம்.")


def page(title, body):
    ld = json.dumps({"@type": "NewsArticle", "headline": title, "datePublished": "2026-11-11T19:15:00+05:30", "articleBody": body}, ensure_ascii=False)
    return mock.Mock(text=f'<html><script type="application/ld+json">{ld}</script></html>')


class StateWideList(unittest.TestCase):
    def test_only_our_district_part(self):
        with mock.patch.object(allnews, "_get", return_value=page("Tamilnadu Power Cut: தமிழகத்தில் நாளை (12-11-2026) மின் தடை", BODY)):
            a = allnews.article_any(LIST_URL + allnews.SECTION_MARK)
        self.assertEqual(a["title"], "நாமக்கல் மாவட்டத்தில் நாளை (12-11-2026) மின்தடை: சமயசங்கிலி, ஆலையபட்டி, பருத்திப்பள்ளி")
        self.assertIn("காலை 9 மணி", a["text"])                       # the hours from the intro are kept
        self.assertIn("சமயசங்கிலி, ஆலையபட்டி, பருத்திப்பள்ளி", a["text"])
        for other in ("வேலூர்", "கரூர்", "காட்பாடி", "பாலம்பாள்புரம்", "சேலம்", "அஸ்தம்பட்டி", "கோவை"):
            self.assertNotIn(other, a["text"] + a["title"], other)    # never another district's areas
        self.assertTrue(a["url"].endswith(allnews.SECTION_MARK))

    def test_list_without_namakkal_gives_no_text(self):
        body = BODY.replace("நாமக்கல் மாவட்டம் சமயசங்கிலி, ஆலையபட்டி, பருத்திப்பள்ளி. ", "")
        with mock.patch.object(allnews, "_get", return_value=page("தமிழகத்தில் நாளை மின்தடை", body)):
            a = allnews.article_any(LIST_URL + allnews.SECTION_MARK)
        self.assertEqual(a["text"], "")

    def test_a_road_named_after_a_district_is_not_a_heading(self):
        body = "நாளை காலை 9 மணி முதல் மின்தடை. நாமக்கல்: சேலம் ரோடு, மோகனூர் ரோடு, கொசவம்பட்டி. கரூர்: வெங்கமேடு."
        with mock.patch.object(allnews, "_get", return_value=page("தமிழகத்தில் நாளை மின்தடை", body)):
            a = allnews.article_any(LIST_URL + allnews.SECTION_MARK)
        self.assertIn("சேலம் ரோடு, மோகனூர் ரோடு, கொசவம்பட்டி", a["text"])
        self.assertNotIn("வெங்கமேடு", a["text"])

    def test_normal_links_unchanged(self):
        with mock.patch.object(allnews, "_get", return_value=page("நாமக்கல்லில் மின்தடை", "நாமக்கல் நகரில் நாளை காலை 9 மணி முதல் மின்தடை.")):
            a = allnews.article_any("https://www.dinamani.com/all-editions/edition-dharmapuri/namakkal/2026/Nov/12/x")
        self.assertEqual(a["title"], "நாமக்கல்லில் மின்தடை")


class SearchAndGuard(unittest.TestCase):
    def test_state_lists_are_searched_and_marked(self):
        hit = {"url": LIST_URL, "title": "தமிழகத்தில் நாளை (12-11-2026) மின்தடை அறிவிப்பு", "site": "tamil.abplive.com", "published": ""}
        with mock.patch.object(allnews, "from_dinamalar_list", return_value=[]), mock.patch.object(allnews, "from_listing", return_value=[]), \
                mock.patch.object(allnews, "from_google", side_effect=lambda q: [hit] if "abplive" in q else []), \
                mock.patch.object(allnews, "from_bing", return_value=[]):
            got = [x["url"] for x in powercut.links()]
        self.assertEqual(got, [LIST_URL + allnews.SECTION_MARK])

    def test_other_district_page_refused(self):
        now = datetime.datetime(2026, 11, 10, 19, 0, tzinfo=IST)
        url = "https://www.dinamalar.com/news/tamil-nadu-district-news-coimbatore/power-outage-today-11th/4372345"
        art = {"title": "நாளைய (11ம் தேதி) மின் தடை", "text": "நாமக்கல் சாலை பகுதிகளில் காலை 9 மணி முதல் மின்தடை", "published": "2026-11-10T18:00:00+05:30"}
        with mock.patch.object(allnews, "article_any", return_value=dict(art, url=url)):
            got, why = powercut.check({"url": url, "title": art["title"]}, now.date(), now)
        self.assertIsNone(got)
        self.assertEqual(why, "other district")


if __name__ == "__main__":
    unittest.main()
