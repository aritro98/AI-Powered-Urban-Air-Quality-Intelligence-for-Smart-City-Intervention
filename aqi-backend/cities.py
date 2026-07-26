"""
City & zone registry. Coordinates are real (approximate locality centroids),
used to query real weather / air-quality / land-use data per zone.
"""

CITIES = {
    "delhi": {
        "name": "Delhi NCR",
        "lang": "hi",
        "zones": {
            "Anand Vihar":    (28.6469, 77.3151),
            "RK Puram":       (28.5641, 77.1856),
            "Punjabi Bagh":   (28.6692, 77.1312),
            "Dwarka":         (28.5921, 77.0460),
            "Rohini":         (28.7495, 77.0565),
            "Okhla":          (28.5355, 77.2910),
            "ITO":            (28.6289, 77.2410),
            "Mundka":         (28.6822, 76.9829),
            "Wazirpur":       (28.6996, 77.1650),
            "Narela":         (28.8480, 77.0910),
        },
    },
    "mumbai": {
        "name": "Mumbai",
        "lang": "mr",
        "zones": {
            "Andheri East": (19.1136, 72.8697),
            "Bandra":       (19.0596, 72.8295),
            "Worli":        (19.0176, 72.8168),
            "Chembur":      (19.0522, 72.9005),
            "Borivali":     (19.2307, 72.8567),
            "Powai":        (19.1176, 72.9060),
            "Dadar":        (19.0178, 72.8478),
            "Kurla":        (19.0728, 72.8826),
            "Malad":        (19.1875, 72.8484),
            "Colaba":       (18.9067, 72.8147),
        },
    },
    "kolkata": {
        "name": "Kolkata",
        "lang": "bn",
        "zones": {
            "Salt Lake":   (22.5800, 88.4171),
            "Howrah":      (22.5958, 88.2636),
            "Ballygunge":  (22.5273, 88.3651),
            "Behala":      (22.4997, 88.3117),
            "Jadavpur":    (22.4990, 88.3714),
            "Park Street": (22.5527, 88.3520),
            "Rajarhat":    (22.6238, 88.4680),
            "Garia":       (22.4620, 88.3927),
            "Tollygunge":  (22.4997, 88.3494),
            "Dum Dum":     (22.6420, 88.4197),
        },
    },
    "bengaluru": {
        "name": "Bengaluru",
        "lang": "kn",
        "zones": {
            "Whitefield":       (12.9698, 77.7500),
            "Indiranagar":      (12.9719, 77.6412),
            "Koramangala":      (12.9352, 77.6245),
            "Jayanagar":        (12.9308, 77.5838),
            "Electronic City":  (12.8452, 77.6602),
            "Yeshwanthpur":     (13.0284, 77.5540),
            "Hebbal":           (13.0355, 77.5970),
            "Malleshwaram":     (13.0037, 77.5747),
            "HSR Layout":       (12.9116, 77.6389),
            "Peenya":           (13.0286, 77.5192),
        },
    },
    "chennai": {
        "name": "Chennai",
        "lang": "ta",
        "zones": {
            "Adyar":      (13.0012, 80.2565),
            "T Nagar":    (13.0418, 80.2341),
            "Anna Nagar": (13.0850, 80.2101),
            "Velachery":  (12.9791, 80.2213),
            "Guindy":     (13.0067, 80.2206),
            "Perambur":   (13.1102, 80.2422),
            "Tambaram":   (12.9249, 80.1000),
            "Mylapore":   (13.0339, 80.2685),
            "Porur":      (13.0381, 80.1564),
            "Ambattur":   (13.1143, 80.1548),
        },
    },
}

def zone_coords(city_id: str, zone: str):
    return CITIES[city_id]["zones"][zone]