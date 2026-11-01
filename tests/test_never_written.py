"""owner 1 Nov (Namakkal 360 / Rasipuram 360): only Namakkal-district NEWS - no other district's story (RN-251, Salem, filed on the
paper's Namakkal page), no shop offer (RN-255, a Rs.10 saree sale), no suicide story."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research_free"))
import collect      # noqa: E402


class NeverWritten(unittest.TestCase):
    def test_blocked(self):
        for t, x in [("வெள்ளி தொழிலாளி தீக்குளித்து தற்கொலை", "சேலம்: சேலம் கொண்டலாம்பட்டி அல்லேரி முனியப்பன் கோவில் அருகே"),
                     ("அபி சரண் சில்க்ஸில் தீபாவளிக்கு ஒரு சேலை ரூ.10க்கு விற்பனை", ""),
                     ("எஸ்.ஆர்.எம்., ஸ்வீட்ஸ் அண்டு கேக்ஸ் புதிய கிளை திறப்பு விழா", ""),
                     ("பரமத்தி வேலூர் அருகே ஐ.டி. ஊழியர் தூக்கிட்டுத் தற்கொலை", ""),
                     ("ஆத்தூர் அருகே சாலையோரம் காய்ந்த மரம்: விபத்து அபாயம்", "ஆத்தூர்: சேலம் மாவட்டம் ஆத்தூர் அருகே")]:
            self.assertTrue(collect.never_written(t, x), t)

    def test_real_news_goes_on(self):
        for t, x in [("சின்ன வெங்காயம் விலை கிடுகிடு உயர்வு: கிலோ ரூ.100 முதல் ரூ.150 வரை", "நாமக்கல் உழவர் சந்தையில்"),
                     ("நாமக்கல்-சேலம் சாலையில் கோழித்தீவன குடோனில் திடீர் தீ விபத்து", "நாமக்கல்: நாமக்கல் - சேலம் சாலையில்"),
                     ("காளிப்பட்டி மாரியம்மன் கோவிலில் பூச்சாட்டுதலுடன் திருவிழா தொடங்கியது", "சேலம் - நாமக்கல் மாவட்ட எல்லையில் அமைந்துள்ள காளிப்பட்டி"),
                     ("ராசிபுரம் துணை மின் நிலையப் பராமரிப்பு: இன்று மின் தடை", "ராசிபுரம்")]:
            self.assertEqual(collect.never_written(t, x), "", t)


if __name__ == "__main__":
    unittest.main()
