"""owner 26 Nov: ONE place that says which pages the daily lanes (history/, jobs/) run for. A page is configuration, not code:
its names, handle, hashtag, logo size, the words that mark a story as belonging to its DISTRICT (taluks, towns), and where its
official job notices are published (jobs/sources/<page>.json, confirmed by the owner before the lane posts anything).
Rasipuram is a page of Namakkal district. Handles are placeholders until the page's token can read the real one (same as goldrate)."""
PAGES = {
    'namakkal': {"town": 'நாமக்கல்', "district_ta": 'நாமக்கல்', "district_en": 'Namakkal', "handle": 'namakkal.360', "tag": '#Namakkal360', "brand_px": 54,
           "official_site": 'namakkal.nic.in', "aliases": ['Kolli Hills', 'Kumarapalayam', 'Mohanur', 'Namakkal', 'Paramathi Velur', 'Rasipuram', 'Sendamangalam', 'Tiruchengode', 'Velur', 'இராசிபுரம்', 'குமாரபாளையம்', 'கொல்லிமலை', 'சேந்தமங்கலம்', 'திருச்செங்கோடு', 'நாமக்கல்', 'மோகனூர்', 'ராசிபுரம்', 'வேலூர்']},
    'rasipuram': {"town": 'இராசிபுரம்', "district_ta": 'நாமக்கல்', "district_en": 'Namakkal', "handle": 'rasipuram360.official', "tag": '#Rasipuram360', "brand_px": 50,
           "official_site": 'namakkal.nic.in', "aliases": ['Kolli Hills', 'Kumarapalayam', 'Mohanur', 'Namakkal', 'Paramathi Velur', 'Rasipuram', 'Sendamangalam', 'Tiruchengode', 'Velur', 'இராசிபுரம்', 'குமாரபாளையம்', 'கொல்லிமலை', 'சேந்தமங்கலம்', 'திருச்செங்கோடு', 'நாமக்கல்', 'மோகனூர்', 'ராசிபுரம்', 'வேலூர்']},
    'coimbatore': {"town": 'கோவை', "district_ta": 'கோயம்புத்தூர்', "district_en": 'Coimbatore', "handle": 'coimbatore360_official', "tag": '#Coimbatore360', "brand_px": 54,
           "official_site": 'coimbatore.nic.in', "aliases": ['Anaimalai', 'Annur', 'Coimbatore', 'Kinathukadavu', 'Madukkarai', 'Mettupalayam', 'Pollachi', 'Sulur', 'Valparai', 'அன்னூர்', 'ஆனைமலை', 'கிணத்துக்கடவு', 'கோயம்புத்தூர்', 'கோவை', 'சூலூர்', 'பொள்ளாச்சி', 'மதுக்கரை', 'மேட்டுப்பாளையம்', 'வால்பாறை']},
    'salem': {"town": 'சேலம்', "district_ta": 'சேலம்', "district_en": 'Salem', "handle": 'salem360.official', "tag": '#Salem360', "brand_px": 54,
           "official_site": 'salem.nic.in', "aliases": ['Attur', 'Edappadi', 'Gangavalli', 'Kadayampatti', 'Mettur', 'Omalur', 'Pethanaickenpalayam', 'Salem', 'Sankagiri', 'Vazhapadi', 'Yercaud', 'ஆத்தூர்', 'எடப்பாடி', 'ஏற்காடு', 'ஓமலூர்', 'காடையாம்பட்டி', 'கெங்கவல்லி', 'சங்ககிரி', 'சேலம்', 'பெத்தநாயக்கன்பாளையம்', 'மேட்டூர்', 'வாழப்பாடி']},
    'erode': {"town": 'ஈரோடு', "district_ta": 'ஈரோடு', "district_en": 'Erode', "handle": 'erode360.official', "tag": '#Erode360', "brand_px": 54,
           "official_site": 'erode.nic.in', "aliases": ['Anthiyur', 'Bhavani', 'Erode', 'Gobichettipalayam', 'Kodumudi', 'Modakurichi', 'Nambiyur', 'Perundurai', 'Sathyamangalam', 'Thalavadi', 'அந்தியூர்', 'ஈரோடு', 'கொடுமுடி', 'கோபிசெட்டிபாளையம்', 'சத்தியமங்கலம்', 'தாளவாடி', 'நம்பியூர்', 'பவானி', 'பெருந்துறை', 'மொடக்குறிச்சி']},
    'tirupur': {"town": 'திருப்பூர்', "district_ta": 'திருப்பூர்', "district_en": 'Tiruppur', "handle": 'tiruppur360.official', "tag": '#Tiruppur360', "brand_px": 52,
           "official_site": 'tiruppur.nic.in', "aliases": ['Avinashi', 'Dharapuram', 'Kangeyam', 'Madathukulam', 'Palladam', 'Tiruppur', 'Tirupur', 'Udumalaipettai', 'Uthukuli', 'அவிநாசி', 'உடுமலைப்பேட்டை', 'ஊத்துக்குளி', 'காங்கேயம்', 'தாராபுரம்', 'திருப்பூர்', 'பல்லடம்', 'மடத்துக்குளம்']},
    'trichy': {"town": 'திருச்சி', "district_ta": 'திருச்சிராப்பள்ளி', "district_en": 'Tiruchirappalli', "handle": 'trichy360.official', "tag": '#Trichy360', "brand_px": 54,
           "official_site": 'tiruchirappalli.nic.in', "aliases": ['Lalgudi', 'Manachanallur', 'Manapparai', 'Marungapuri', 'Musiri', 'Srirangam', 'Thottiyam', 'Thuraiyur', 'Tiruchirappalli', 'Tiruverumbur', 'Trichy', 'திருச்சி', 'திருச்சிராப்பள்ளி', 'திருவெறும்பூர்', 'துறையூர்', 'தொட்டியம்', 'மணப்பாறை', 'மண்ணச்சநல்லூர்', 'மருங்காபுரி', 'முசிறி', 'லால்குடி', 'ஸ்ரீரங்கம்']},
    'karur': {"town": 'கரூர்', "district_ta": 'கரூர்', "district_en": 'Karur', "handle": 'karur360.official', "tag": '#Karur360', "brand_px": 54,
           "official_site": 'karur.nic.in', "aliases": ['Aravakurichi', 'Kadavur', 'Karur', 'Krishnarayapuram', 'Kulithalai', 'Manmangalam', 'அரவக்குறிச்சி', 'கடவூர்', 'கரூர்', 'கிருஷ்ணராயபுரம்', 'குளித்தலை', 'மண்மங்கலம்']},
}


def page(key):
    return dict(PAGES[key], key=key)
